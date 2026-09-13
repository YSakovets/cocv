"""Observations: what a layer actually holds about one operation.

A collector is any callable that, given an operation id, returns an
Observation for one layer. Collectors read real state: a database row,
an outbound request log, an external party's record, the rendered UI.
They never read the status field another layer derived.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


@dataclass
class Observation:
    layer: str
    operation_id: str
    # The data as this layer holds it (field name -> value).
    data: dict[str, Any] = field(default_factory=dict)
    # Whether this layer records the operation as having succeeded.
    reports_success: bool | None = None
    # Whether this layer has evidence the operation was actually transmitted onward.
    dispatched: bool | None = None
    # Raw response received from the next party, if this layer received one.
    raw_response: Any = None
    # Per-item outcomes for operations that fan out (e.g. one request per broker).
    item_outcomes: dict[str, bool] = field(default_factory=dict)
    # Places where the sensitive payload was found in cleartext (log names, queue names).
    cleartext_exposures: tuple[str, ...] = ()
    # Emitted telemetry events, if this layer emits any.
    telemetry: dict[str, Any] = field(default_factory=dict)
    # Free-form notes a collector wants to attach as evidence.
    evidence: dict[str, Any] = field(default_factory=dict)


class Collector(Protocol):
    def __call__(self, operation_id: str) -> Observation: ...


Collectors = dict[str, Callable[[str], Observation]]
