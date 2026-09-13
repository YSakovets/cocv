# Chain of Custody Verification (CoCV)

A cross-layer verification methodology for consumer privacy and security software, with a reference implementation.

CoCV detects **silent protection failures**: cases where software reports to the user that a protective operation succeeded ("your data was removed", "your files were erased", "your password is encrypted") while the operation did not, in fact, complete.

Methodology specification: **https://yevheniiasakovets.com/cocv/**
Standards alignment: [docs/standards-mapping.md](docs/standards-mapping.md)

## The problem in one paragraph

A deletion request crosses at least six handoffs: interface, API, backend, external party, stored state, interface again. Feature-level tests check each layer against its own specification and take the system's own status as the oracle. When a failure happens *between* layers, every layer passes its own test, every test is green, and the user sees "Removed" while nothing was removed. CoCV follows one piece of user data across all handoffs and compares adjacent layers against each other and against downstream reality. The interface is the last thing checked and the first thing distrusted.

## What is in this repository

| Path | What it is |
|---|---|
| `cocv/chain.py` | Chain definitions: layers, handoffs, and which verification points apply. Loaded from YAML. |
| `cocv/observation.py` | The `Observation` a collector returns for one layer: the data as that layer holds it, whether it reports success, whether it dispatched, raw responses, exposures, telemetry. |
| `cocv/reconcile.py` | The reconciler. Applies verification points V1 to V10 across adjacent layers and localizes the first broken link. Deterministic. |
| `cocv/report.py` | Text and JSON reports, including the full trace. |
| `cocv/ai/classify.py` | Classification of divergences into actionable defects. A rule-based classifier is always available; an LLM classifier accepts any caller-supplied completion function. AI is applied to the reconciler's result, never asked to decide what to check. |
| `examples/synthetic_removal_service/` | A six-layer in-memory removal service with seven injectable faults, its chain definition, and a runner. |
| `tests/` | For each fault: the feature-level check passes, CoCV fails and localizes the break. |
| `docs/` | Methodology summary, chain definition format, standards mapping. |

## Quickstart

```bash
pip install -e .
python -m examples.synthetic_removal_service.run
python -m examples.synthetic_removal_service.run --fault empty_response_ok
python -m examples.synthetic_removal_service.run --fault trim_address --fault partial_as_complete
pytest
```

The healthy run passes. Each `--fault` reproduces a silent protection failure pattern seen in real systems: an empty external response mapped to success, an address trimmed by the API layer, one broker failing while aggregate status reads Complete, a request queued and recorded as sent, the payload logged in cleartext, a record reappearing after deletion, telemetry emitted from the same status field the interface reads.

Example output for `--fault empty_response_ok`:

```
Conventional feature-level check: user sees 'Complete'

Verdict:    FAIL
Class:      SILENT PROTECTION FAILURE (user was told success; chain shows it did not complete)
First broken link: backend -> brokers

Divergences:
  [V3] backend -> brokers
      backend recorded success from an empty or error response
  [V4] backend -> brokers
      backend reports success=True but brokers reports success=False
```

## Applying CoCV to your own product

1. **Pick one protective claim** your product makes to the user. Not a feature; a claim that something happened.
2. **Draw the chain.** List every layer the user's data crosses between the user's action and the user's confirmation, including external parties.
3. **Write the chain definition** in YAML (see `docs/chain-definition.md`). Declare which verification points apply to each handoff and which fields must survive each handoff unchanged.
4. **Write a collector per layer.** A collector reads that layer's real state for one operation id and returns an `Observation`. It must not read a status another layer derived.
5. **Run `reconcile`** and read the trace. For the first claim, do this by hand before automating anything.
6. **Only then** wire it into CI and, if useful, attach a classifier.

## Verification points

| Point | Check |
|---|---|
| V1 | Request capture: data reaches the next layer complete and unaltered |
| V2 | Dispatch confirmation: the operation was actually transmitted, not only queued or logged |
| V3 | Response interpretation: empty, ambiguous, or error responses are not defaulted to success |
| V4 | State reconciliation: recorded status matches the real outcome |
| V5 | User-facing truthfulness: the status shown to the user matches the reconciled state |
| V6 | Partial failure handling: a partial failure is not reported as aggregate success |
| V7 | Secure handling: data is not exposed in cleartext where it should not be |
| V8 | Persistence over time: the effect of the operation holds on re-check |
| V9 | Telemetry fidelity: reported events match what actually occurred |
| V10 | Recovery integrity: interrupted operations resume without loss or duplication |

## Where AI fits

The reconciler decides whether and where the chain broke. That is deterministic. The classifier explains the divergence: likely root cause, user impact, what to check first. `RuleBasedClassifier` does this with no external calls. `LLMClassifier` does it with a language model you supply through a single `complete(prompt) -> str` function; no provider is hard-coded and no credentials are read by this library. The order is deliberate: the architecture determines what is verified, and AI is applied to the result.

## Status

Version 0.1, working draft. The verification points and the reference implementation are open for review. Corrections, counterexamples, and reports of use on real systems are welcome as issues or pull requests. Teams that have applied the method and are willing to be listed can open an issue titled "Adoption".

## Independence

This methodology and implementation were developed independently by the author, using no code, data, or internal materials of any employer. The synthetic service in `examples/` is invented for demonstration and does not model any specific product.

## Citation

```
Sakovets, Y. (2026). Chain of Custody Verification (CoCV): a methodology for
detecting silent protection failures in consumer privacy and security software,
v0.1. https://github.com/GITHUB_USERNAME/cocv
```

See `CITATION.cff`.

## License

Code: MIT (see `LICENSE`). Methodology text in `docs/`: Creative Commons Attribution 4.0.
