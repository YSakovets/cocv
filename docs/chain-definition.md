# Chain definition format

A chain is declared in YAML so that it can be reviewed by people who do not read the implementation. One chain describes one protective claim.

```yaml
name: personal-data-removal
claim: "Your personal information has been removed from data broker sites."

layers:
  - name: interface
    description: Form where the user submits name, email, and address
  - name: api
  - name: backend
  - name: brokers          # external parties; ground truth
  - name: state
  - name: interface_result

handoffs:
  - from: interface
    to: api
    points: [V1]
    carry: { name: name, email: email, address: address }

  - from: backend
    to: brokers
    points: [V2, V3, V4, V6]

  - from: state
    to: interface_result
    points: [V5]

whole_chain_points: [V8, V9, V10]
```

## Fields

- `name`: identifier for the chain.
- `claim`: the exact promise made to the user, in the user's words. Everything downstream is verified against this sentence.
- `layers`: ordered list of the layers the data crosses. Order matters: it is the order of the trace and the order in which the first broken link is determined.
- `handoffs`: each transfer between two layers, with the verification points that apply and, for V1, a `carry` map of field names on the source side to field names on the target side. Fields listed in `carry` must survive the handoff unchanged.
- `whole_chain_points`: checks that apply to the operation as a whole rather than to one handoff (V8, V9, V10).

## Ground truth

Exactly one layer should be the ground truth for the claim: the place where you can observe whether the protective operation actually happened, independent of anything the system recorded about itself. For a removal claim that is the external party. For an erasure claim it is the storage medium. For an encryption claim it is the stored bytes. The collector for that layer sets `evidence["is_ground_truth"] = True` and, where the claim has a duration, `evidence["effect_holds_on_recheck"]`.

## Collectors

A collector is a function `(operation_id) -> Observation` for one layer. It reads that layer's real state. It never reads a status field another layer derived, because that would make the layer agree with the error it is supposed to detect.
