"""Human-readable and machine-readable reports for a ChainResult."""

from __future__ import annotations

import json
from dataclasses import asdict

from .reconcile import ChainResult


def to_text(result: ChainResult) -> str:
    lines = [
        f"Chain:      {result.chain}",
        f"Claim:      {result.claim}",
        f"Operation:  {result.operation_id}",
        f"User told:  {'success' if result.user_was_told_success else 'failure' if result.user_was_told_success is False else 'unknown'}",
        f"Verdict:    {'PASS' if result.passed else 'FAIL'}",
    ]
    if result.is_silent_protection_failure:
        lines.append("Class:      SILENT PROTECTION FAILURE (user was told success; chain shows it did not complete)")
    if result.divergences:
        lines.append(f"First broken link: {result.first_broken_link}")
        lines.append("")
        lines.append("Divergences:")
        for d in result.divergences:
            lines.append(f"  [{d.point}] {d.handoff}")
            lines.append(f"      {d.summary}")
            if d.evidence:
                lines.append(f"      evidence: {json.dumps(d.evidence, default=str)}")
    lines.append("")
    lines.append("Trace:")
    for name, obs in result.observations.items():
        status = "success" if obs.reports_success else "failure" if obs.reports_success is False else "n/a"
        lines.append(f"  {name:<16} reports={status:<8} data={json.dumps(obs.data, default=str)}")
    return "\n".join(lines)


def to_dict(result: ChainResult) -> dict:
    return {
        "chain": result.chain,
        "claim": result.claim,
        "operation_id": result.operation_id,
        "passed": result.passed,
        "silent_protection_failure": result.is_silent_protection_failure,
        "first_broken_link": result.first_broken_link,
        "divergences": [asdict(d) | {"description": d.description} for d in result.divergences],
        "trace": {name: asdict(obs) for name, obs in result.observations.items()},
    }


def to_json(result: ChainResult) -> str:
    return json.dumps(to_dict(result), indent=2, default=str)
