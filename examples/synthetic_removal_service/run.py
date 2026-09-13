"""Run the reference implementation against the synthetic service.

    python -m examples.synthetic_removal_service.run
    python -m examples.synthetic_removal_service.run --fault empty_response_ok
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cocv import Chain, reconcile, to_text
from cocv.ai import RuleBasedClassifier

from .service import Faults, RemovalService

HERE = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser(description="CoCV demo against a synthetic removal service")
    parser.add_argument("--fault", action="append", default=[], choices=list(Faults.__dataclass_fields__),
                        help="inject a fault (repeatable)")
    args = parser.parse_args()

    faults = Faults(**{f: True for f in args.fault})
    service = RemovalService(faults=faults)
    service.submit_removal("op-1", name="Ada Example", email="ada@example.org",
                           address="1 Long Street Name That Exceeds Twenty Characters, Springfield")

    chain = Chain.load(HERE / "chain.yaml")
    result = reconcile(chain, service.collectors(), "op-1")

    print(f"Conventional feature-level check: user sees '{service.status_shown_to_user('op-1')}'")
    print()
    print(to_text(result))

    if result.divergences:
        print()
        print("Classified defects:")
        for defect in RuleBasedClassifier().classify(result):
            print(f"  {defect.severity.upper():<9} {defect.title}")
            print(f"            hypothesis: {defect.root_cause_hypothesis}")


if __name__ == "__main__":
    main()
