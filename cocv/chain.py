"""Chain definitions.

A chain describes the layers a protective operation crosses and the
handoffs between them. Each handoff declares which verification points
apply and how fields are named on either side.

Chains are declared in YAML so that they can be reviewed by people who
do not read the implementation. See docs/chain-definition.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VERIFICATION_POINTS: dict[str, str] = {
    "V1": "Request capture: data reaches the next layer complete and unaltered",
    "V2": "Dispatch confirmation: the operation was actually transmitted, not only queued or logged",
    "V3": "Response interpretation: empty, ambiguous, or error responses are not defaulted to success",
    "V4": "State reconciliation: recorded status matches the real outcome",
    "V5": "User-facing truthfulness: the status shown to the user matches the reconciled state",
    "V6": "Partial failure handling: a partial failure is not reported as aggregate success",
    "V7": "Secure handling: data is not exposed in cleartext where it should not be",
    "V8": "Persistence over time: the effect of the operation holds",
    "V9": "Telemetry fidelity: reported events match what actually occurred",
    "V10": "Recovery integrity: interrupted operations resume without loss or duplication",
}


@dataclass(frozen=True)
class Layer:
    name: str
    description: str = ""


@dataclass(frozen=True)
class Handoff:
    """A transfer of the operation's data from one layer to the next."""

    source: str
    target: str
    points: tuple[str, ...]
    # Field names on the source side mapped to field names on the target side.
    # Fields listed here are expected to survive the handoff unchanged.
    carry: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = [p for p in self.points if p not in VERIFICATION_POINTS]
        if unknown:
            raise ValueError(f"Unknown verification point(s) {unknown} on {self.source} -> {self.target}")


@dataclass(frozen=True)
class Chain:
    name: str
    claim: str
    layers: tuple[Layer, ...]
    handoffs: tuple[Handoff, ...]
    # Checks that apply to the operation as a whole rather than to one handoff.
    whole_chain_points: tuple[str, ...] = ()

    def layer_names(self) -> list[str]:
        return [layer.name for layer in self.layers]

    def validate(self) -> None:
        names = set(self.layer_names())
        for h in self.handoffs:
            for side in (h.source, h.target):
                if side not in names:
                    raise ValueError(f"Handoff references unknown layer '{side}'")
        unknown = [p for p in self.whole_chain_points if p not in VERIFICATION_POINTS]
        if unknown:
            raise ValueError(f"Unknown whole-chain verification point(s) {unknown}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chain":
        layers = tuple(Layer(**item) if isinstance(item, dict) else Layer(name=item) for item in data["layers"])
        handoffs = tuple(
            Handoff(
                source=item["from"],
                target=item["to"],
                points=tuple(item.get("points", ())),
                carry=dict(item.get("carry", {})),
            )
            for item in data.get("handoffs", ())
        )
        chain = cls(
            name=data["name"],
            claim=data["claim"],
            layers=layers,
            handoffs=handoffs,
            whole_chain_points=tuple(data.get("whole_chain_points", ())),
        )
        chain.validate()
        return chain

    @classmethod
    def load(cls, path: str | Path) -> "Chain":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh))
