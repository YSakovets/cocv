"""AI-assisted classification of divergences.

The reconciler decides *whether* and *where* the chain broke. That is
deterministic and does not depend on a model. This module sits on top of
the reconciler and helps with the part that benefits from AI: turning a
divergence plus its evidence into a classified, well-described defect
that an engineer can act on.

Two classifiers are provided:

- RuleBasedClassifier: deterministic, no external calls. Always available.
- LLMClassifier: sends the divergence and evidence to a language model
  through a caller-supplied function. No provider is hard-coded and no
  keys are read here.

The order of operations is deliberate. The architecture (the chain
definition) determines what is verified. AI is applied to the result,
never asked to decide what to check.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..reconcile import ChainResult, Divergence

SEVERITY_BY_POINT = {
    "V5": "critical",   # user told success, it was not
    "V3": "critical",   # empty/error response mapped to success
    "V6": "critical",   # partial failure reported as success
    "V2": "high",       # recorded as sent, was not
    "V4": "high",
    "V8": "high",
    "V7": "high",
    "V1": "medium",
    "V9": "medium",
    "V10": "medium",
}


@dataclass
class ClassifiedDefect:
    title: str
    severity: str
    point: str
    handoff: str
    root_cause_hypothesis: str
    user_impact: str
    evidence: dict


class RuleBasedClassifier:
    def classify(self, result: ChainResult) -> list[ClassifiedDefect]:
        defects: list[ClassifiedDefect] = []
        for d in result.divergences:
            defects.append(ClassifiedDefect(
                title=f"[{d.point}] {d.summary}",
                severity=SEVERITY_BY_POINT.get(d.point, "medium"),
                point=d.point,
                handoff=d.handoff,
                root_cause_hypothesis=_hypothesis(d),
                user_impact=_impact(d, result),
                evidence=d.evidence,
            ))
        return defects


def _hypothesis(d: Divergence) -> str:
    return {
        "V1": "A field is trimmed, truncated, renamed, or dropped by serialization or validation between layers.",
        "V2": "Status is written before, or independently of, the outbound call; the call may be queued and never sent.",
        "V3": "Response handling has a default branch that maps unexpected, empty, or error responses to success.",
        "V4": "Two layers derive status from different sources and are never reconciled.",
        "V5": "The interface reads a status field that is not derived from the real outcome.",
        "V6": "Aggregate status is computed as 'any succeeded' or 'request accepted' rather than 'all succeeded'.",
        "V7": "Payload is logged, cached, or queued before encryption, or decrypted for processing and not cleared.",
        "V8": "The effect is applied once and not re-verified; upstream re-ingestion or suppression expiry reverses it.",
        "V9": "Telemetry is emitted from the same status field the interface uses, so it inherits the same error.",
        "V10": "Retry logic lacks idempotency keys or replays from a stale checkpoint.",
    }.get(d.point, "Unknown.")


def _impact(d: Divergence, result: ChainResult) -> str:
    if result.user_was_told_success:
        return ("The user was told the protective operation succeeded. It did not complete. "
                "The user is exposed while believing they are protected and has no reason to check.")
    return "The user was not told the operation succeeded; impact is limited to the failed operation itself."


class LLMClassifier:
    """Classify with a language model supplied by the caller.

    `complete` receives a prompt string and returns the model's text.
    The prompt contains only the divergence and its evidence, never the
    whole codebase; the model is asked to explain, not to decide.
    """

    def __init__(self, complete: Callable[[str], str]) -> None:
        self._complete = complete
        self._fallback = RuleBasedClassifier()

    def classify(self, result: ChainResult) -> list[ClassifiedDefect]:
        base = self._fallback.classify(result)
        for defect in base:
            prompt = (
                "You are assisting a quality engineer. A cross-layer verification found a divergence.\n"
                f"Claim to the user: {result.claim}\n"
                f"Verification point: {defect.point} ({defect.title})\n"
                f"Handoff: {defect.handoff}\n"
                f"Evidence: {defect.evidence}\n"
                "In three sentences: (1) the most likely root cause, (2) what the user experiences, "
                "(3) what an engineer should check first. Do not speculate beyond the evidence."
            )
            try:
                defect.root_cause_hypothesis = self._complete(prompt).strip()
            except Exception:  # keep the deterministic hypothesis if the model call fails
                pass
        return base
