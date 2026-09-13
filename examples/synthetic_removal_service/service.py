"""A synthetic personal-data removal service.

Six layers, in memory, with faults you can switch on. It exists so that the
methodology can be demonstrated and tested without any real product. Every
fault here is a pattern seen in real systems; none is taken from any
specific product.

Layers: interface -> api -> backend -> brokers (external) -> state -> interface_result

Faults:
  trim_address          V1  the API trims the address to 20 characters
  queue_without_send    V2  backend marks "sent" but never dispatches
  empty_response_ok     V3  an empty broker response is recorded as success
  partial_as_complete   V6  one broker fails, aggregate status still Complete
  log_cleartext         V7  backend logs the full payload before encrypting
  reappears_later       V8  a broker re-lists the record after "deletion"
  telemetry_from_status V9  telemetry emits success from the status field
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cocv.observation import Observation


@dataclass
class Faults:
    trim_address: bool = False
    queue_without_send: bool = False
    empty_response_ok: bool = False
    partial_as_complete: bool = False
    log_cleartext: bool = False
    reappears_later: bool = False
    telemetry_from_status: bool = False


@dataclass
class RemovalService:
    faults: Faults = field(default_factory=Faults)
    brokers: tuple[str, ...] = ("broker-a", "broker-b", "broker-c")

    def __post_init__(self) -> None:
        self._interface: dict[str, dict] = {}
        self._api: dict[str, dict] = {}
        self._backend: dict[str, dict] = {}
        self._broker_records: dict[str, dict[str, bool]] = {b: {} for b in self.brokers}
        self._broker_responses: dict[str, dict[str, object]] = {}
        self._state: dict[str, dict] = {}
        self._removed_at_operation: dict[str, bool] = {}
        self._logs: list[str] = []

    # ---- the operation ----------------------------------------------------

    def submit_removal(self, op_id: str, name: str, email: str, address: str) -> None:
        # Interface collects the data.
        self._interface[op_id] = {"name": name, "email": email, "address": address}

        # API accepts the payload (fault: trims address).
        payload = dict(self._interface[op_id])
        if self.faults.trim_address:
            payload["address"] = payload["address"][:20]
        self._api[op_id] = payload

        # Backend builds requests to each broker.
        if self.faults.log_cleartext:
            self._logs.append(f"removal payload {op_id}: {payload}")
        backend = {"data": dict(payload), "dispatched": {}, "responses": {}}

        for broker in self.brokers:
            # Seed: the broker holds the record before removal.
            self._broker_records[broker][op_id] = True

            if self.faults.queue_without_send:
                backend["dispatched"][broker] = False
                backend["responses"][broker] = {"status": "queued"}
                continue

            backend["dispatched"][broker] = True
            # Broker processes the request.
            if self.faults.partial_as_complete and broker == "broker-c":
                response = {"error": "record locked"}
                self._broker_records[broker][op_id] = True  # still there
            elif self.faults.empty_response_ok:
                response = ""  # broker returned nothing
                self._broker_records[broker][op_id] = True  # nothing happened
            else:
                response = {"status": "deleted"}
                self._broker_records[broker][op_id] = False
            backend["responses"][broker] = response

        self._backend[op_id] = backend

        # Backend records aggregate state.
        per_broker_ok = {}
        for broker, response in backend["responses"].items():
            if self.faults.queue_without_send:
                ok = True  # fault: queued counts as done
            elif self.faults.empty_response_ok and response == "":
                ok = True  # fault: empty mapped to success
            elif isinstance(response, dict) and response.get("error"):
                ok = False
            else:
                ok = isinstance(response, dict) and response.get("status") == "deleted"
            per_broker_ok[broker] = ok

        if self.faults.partial_as_complete:
            aggregate = any(per_broker_ok.values())
        else:
            aggregate = all(per_broker_ok.values())

        self._state[op_id] = {"status": "Complete" if aggregate else "Failed", "per_broker": per_broker_ok}

        # Snapshot the real outcome at the moment the operation completed.
        self._removed_at_operation[op_id] = not any(recs.get(op_id, False) for recs in self._broker_records.values())

        # Later: a broker re-lists the record (fault).
        if self.faults.reappears_later:
            self._broker_records["broker-a"][op_id] = True

    # ---- collectors: what each layer really holds -------------------------

    def collect_interface(self, op_id: str) -> Observation:
        return Observation(layer="interface", operation_id=op_id, data=dict(self._interface[op_id]))

    def collect_api(self, op_id: str) -> Observation:
        return Observation(layer="api", operation_id=op_id, data=dict(self._api[op_id]))

    def collect_backend(self, op_id: str) -> Observation:
        b = self._backend[op_id]
        state = self._state[op_id]
        exposures = tuple("application.log" for line in self._logs if op_id in line)[:1]
        responses = b["responses"]
        # Represent the fan-out as a single raw response for V3: use the first empty/error if any.
        raw = next((r for r in responses.values() if r in ("", None) or (isinstance(r, dict) and r.get("error"))),
                   next(iter(responses.values()), None))
        return Observation(
            layer="backend",
            operation_id=op_id,
            data=dict(b["data"]),
            reports_success=state["status"] == "Complete",
            dispatched=all(b["dispatched"].values()),
            raw_response=raw,
            item_outcomes=dict(state["per_broker"]),
            cleartext_exposures=exposures,
            telemetry={"operation_succeeded": state["status"] == "Complete"} if self.faults.telemetry_from_status else {},
        )

    def collect_brokers(self, op_id: str) -> Observation:
        # Ground truth: does any broker still hold the record?
        still_held = {b: recs.get(op_id, False) for b, recs in self._broker_records.items()}
        holds_now = not any(still_held.values())
        return Observation(
            layer="brokers",
            operation_id=op_id,
            data={},
            # Outcome at the time of the operation: did the removal actually happen?
            reports_success=self._removed_at_operation[op_id],
            # Re-check now: does the effect still hold?
            evidence={"is_ground_truth": True, "still_held_by": [b for b, h in still_held.items() if h],
                      "effect_holds_on_recheck": holds_now},
        )

    def collect_state(self, op_id: str) -> Observation:
        return Observation(layer="state", operation_id=op_id,
                           reports_success=self._state[op_id]["status"] == "Complete")

    def collect_interface_result(self, op_id: str) -> Observation:
        # The interface renders whatever the state says. It is not an oracle.
        shown = self._state[op_id]["status"]
        return Observation(layer="interface_result", operation_id=op_id,
                           data={"shown": shown}, reports_success=shown == "Complete")

    def collectors(self) -> dict:
        return {
            "interface": self.collect_interface,
            "api": self.collect_api,
            "backend": self.collect_backend,
            "brokers": self.collect_brokers,
            "state": self.collect_state,
            "interface_result": self.collect_interface_result,
        }

    # ---- the conventional feature-level test would call this -------------

    def status_shown_to_user(self, op_id: str) -> str:
        return self._state[op_id]["status"]
