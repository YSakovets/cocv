"""Reconciliation: verify one operation across the whole chain.

For each handoff, the reconciler compares the observation on the source
side with the observation on the target side and applies the declared
verification points. A divergence is recorded at the first handoff where
adjacent layers disagree. That handoff is the localized point of failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .chain import Chain, Handoff, VERIFICATION_POINTS
from .observation import Collectors, Observation


@dataclass
class Divergence:
    point: str
    handoff: str  # "source -> target" or "whole chain"
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def description(self) -> str:
        return VERIFICATION_POINTS[self.point]


@dataclass
class ChainResult:
    chain: str
    claim: str
    operation_id: str
    observations: dict[str, Observation]
    divergences: list[Divergence]

    @property
    def passed(self) -> bool:
        return not self.divergences

    @property
    def first_broken_link(self) -> str | None:
        return self.divergences[0].handoff if self.divergences else None

    @property
    def user_was_told_success(self) -> bool | None:
        last = self.observations.get(self._last_layer())
        return last.reports_success if last else None

    def _last_layer(self) -> str:
        return list(self.observations)[-1]

    @property
    def is_silent_protection_failure(self) -> bool:
        """True when the user was told the operation succeeded and the chain shows it did not."""
        return bool(self.divergences) and self.user_was_told_success is True


def _check_handoff(handoff: Handoff, src: Observation, dst: Observation) -> list[Divergence]:
    label = f"{handoff.source} -> {handoff.target}"
    found: list[Divergence] = []

    if "V1" in handoff.points:
        for s_field, d_field in handoff.carry.items():
            s_val = src.data.get(s_field)
            d_val = dst.data.get(d_field)
            if s_val != d_val:
                found.append(Divergence(
                    "V1", label,
                    f"Field '{s_field}' changed in transit: {s_val!r} became {d_val!r} as '{d_field}'",
                    {"source_value": s_val, "target_value": d_val},
                ))

    if "V2" in handoff.points:
        if src.reports_success and src.dispatched is False:
            found.append(Divergence(
                "V2", label,
                f"{src.layer} records success but has no evidence the operation was dispatched",
                {"reports_success": src.reports_success, "dispatched": src.dispatched},
            ))

    if "V3" in handoff.points:
        empty_or_error = src.raw_response in (None, "", {}, []) or (
            isinstance(src.raw_response, dict) and src.raw_response.get("error")
        )
        if src.reports_success and empty_or_error:
            found.append(Divergence(
                "V3", label,
                f"{src.layer} recorded success from an empty or error response",
                {"raw_response": src.raw_response},
            ))

    if "V4" in handoff.points:
        if src.reports_success is not None and dst.reports_success is not None \
                and src.reports_success != dst.reports_success:
            found.append(Divergence(
                "V4", label,
                f"{src.layer} reports success={src.reports_success} but {dst.layer} reports success={dst.reports_success}",
                {"source": src.reports_success, "target": dst.reports_success},
            ))

    if "V5" in handoff.points:
        # Same comparison as V4, but named for the user-facing edge so reports read correctly.
        if src.reports_success is not None and dst.reports_success is not None \
                and src.reports_success != dst.reports_success:
            found.append(Divergence(
                "V5", label,
                f"User is shown success={dst.reports_success} while reconciled state is success={src.reports_success}",
                {"reconciled": src.reports_success, "shown": dst.reports_success},
            ))

    if "V6" in handoff.points:
        if src.item_outcomes and src.reports_success and not all(src.item_outcomes.values()):
            failed = [k for k, ok in src.item_outcomes.items() if not ok]
            found.append(Divergence(
                "V6", label,
                f"{src.layer} reports aggregate success while {len(failed)} of {len(src.item_outcomes)} items failed",
                {"failed_items": failed},
            ))

    if "V7" in handoff.points:
        for obs in (src, dst):
            if obs.cleartext_exposures:
                found.append(Divergence(
                    "V7", label,
                    f"{obs.layer} exposed the payload in cleartext: {', '.join(obs.cleartext_exposures)}",
                    {"exposures": list(obs.cleartext_exposures)},
                ))

    return found


def _check_whole_chain(chain: Chain, obs: dict[str, Observation]) -> list[Divergence]:
    found: list[Divergence] = []
    label = "whole chain"
    layers = list(obs.values())

    if "V8" in chain.whole_chain_points:
        # The ground-truth layer re-checks whether the effect still holds. If it does not,
        # every layer that told anyone the operation succeeded is now wrong.
        truth_layer = next((o for o in layers if o.evidence.get("is_ground_truth")), None)
        if truth_layer is not None and truth_layer.evidence.get("effect_holds_on_recheck") is False:
            reporters = [o.layer for o in layers if o.reports_success]
            if reporters:
                found.append(Divergence(
                    "V8", label,
                    f"Effect did not hold on re-check at {truth_layer.layer}; still reported as success by {', '.join(reporters)}",
                    {"ground_truth": truth_layer.layer, "evidence": truth_layer.evidence},
                ))

    if "V9" in chain.whole_chain_points:
        truth = _ground_truth_success(layers)
        for o in layers:
            reported = o.telemetry.get("operation_succeeded")
            if reported is not None and truth is not None and reported != truth:
                found.append(Divergence(
                    "V9", label,
                    f"{o.layer} telemetry reports success={reported} but ground truth is success={truth}",
                    {"telemetry": o.telemetry},
                ))

    if "V10" in chain.whole_chain_points:
        for o in layers:
            dup = o.evidence.get("duplicate_effects")
            lost = o.evidence.get("lost_on_retry")
            if dup:
                found.append(Divergence("V10", label, f"{o.layer} applied the operation more than once after retry", {"duplicates": dup}))
            if lost:
                found.append(Divergence("V10", label, f"{o.layer} lost the operation on retry", {"lost": lost}))
    return found


def _ground_truth_success(layers: list[Observation]) -> bool | None:
    """The most downstream layer with a definite success value is treated as ground truth."""
    for o in layers:
        if o.evidence.get("is_ground_truth") and o.reports_success is not None:
            return o.reports_success
    return None


def reconcile(chain: Chain, collectors: Collectors, operation_id: str) -> ChainResult:
    observations: dict[str, Observation] = {}
    for layer in chain.layer_names():
        if layer not in collectors:
            raise KeyError(f"No collector registered for layer '{layer}'")
        observations[layer] = collectors[layer](operation_id)

    divergences: list[Divergence] = []
    for handoff in chain.handoffs:
        divergences.extend(_check_handoff(handoff, observations[handoff.source], observations[handoff.target]))
    divergences.extend(_check_whole_chain(chain, observations))

    return ChainResult(
        chain=chain.name,
        claim=chain.claim,
        operation_id=operation_id,
        observations=observations,
        divergences=divergences,
    )
