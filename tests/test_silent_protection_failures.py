"""Each test injects one fault into the synthetic service and shows two things:

1. The conventional feature-level check passes (the user sees 'Complete').
2. CoCV fails, and localizes the divergence to the expected verification point.

That pairing is the whole argument of the methodology.
"""

from pathlib import Path

import pytest

from cocv import Chain, reconcile
from examples.synthetic_removal_service.service import Faults, RemovalService

CHAIN = Chain.load(Path(__file__).parent.parent / "examples/synthetic_removal_service/chain.yaml")
ADDRESS = "1 Long Street Name That Exceeds Twenty Characters, Springfield"


def run(faults: Faults):
    service = RemovalService(faults=faults)
    service.submit_removal("op-1", "Ada Example", "ada@example.org", ADDRESS)
    return service, reconcile(CHAIN, service.collectors(), "op-1")


def test_healthy_chain_passes():
    service, result = run(Faults())
    assert service.status_shown_to_user("op-1") == "Complete"
    assert result.passed
    assert not result.is_silent_protection_failure


@pytest.mark.parametrize(
    "fault, expected_point, expected_link",
    [
        ("trim_address", "V1", "interface -> api"),
        ("queue_without_send", "V2", "backend -> brokers"),
        ("empty_response_ok", "V3", "backend -> brokers"),
        ("partial_as_complete", "V6", "backend -> brokers"),
        ("log_cleartext", "V7", "api -> backend"),
    ],
)
def test_feature_level_passes_but_cocv_localizes_the_break(fault, expected_point, expected_link):
    service, result = run(Faults(**{fault: True}))

    # The conventional check: the interface says the job is done.
    assert service.status_shown_to_user("op-1") == "Complete"

    # CoCV: the chain is broken, and we know which link.
    assert not result.passed
    points = {d.point for d in result.divergences}
    assert expected_point in points
    assert any(d.handoff == expected_link and d.point == expected_point for d in result.divergences)


@pytest.mark.parametrize("fault", ["queue_without_send", "empty_response_ok", "partial_as_complete"])
def test_faults_that_leave_data_in_place_are_silent_protection_failures(fault):
    _, result = run(Faults(**{fault: True}))
    assert result.is_silent_protection_failure
    # Ground truth disagrees with what the user was shown.
    assert result.observations["brokers"].reports_success is False
    assert result.observations["interface_result"].reports_success is True


def test_reappearance_is_caught_by_persistence_check():
    _, result = run(Faults(reappears_later=True))
    assert any(d.point == "V8" for d in result.divergences)
    assert result.is_silent_protection_failure


def test_telemetry_inherits_the_status_error():
    _, result = run(Faults(empty_response_ok=True, telemetry_from_status=True))
    assert any(d.point == "V9" for d in result.divergences)


def test_first_broken_link_is_the_earliest_handoff():
    _, result = run(Faults(trim_address=True, empty_response_ok=True))
    assert result.first_broken_link == "interface -> api"


def test_chain_definition_rejects_unknown_points():
    with pytest.raises(ValueError):
        Chain.from_dict({
            "name": "x", "claim": "y",
            "layers": ["a", "b"],
            "handoffs": [{"from": "a", "to": "b", "points": ["V99"]}],
        })
