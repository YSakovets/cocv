# Chain of Custody Verification: methodology summary

This is a summary. The full specification is published at https://yevheniiasakovets.com/cocv/.

## The defect class

A silent protection failure is a defect in which software reports to the user that a protective operation succeeded while the operation did not complete. It is invisible to the user, who has been told she is protected, and invisible to feature-level testing, which takes the system's own status as the oracle.

## Three principles

1. The data is the unit of test, not the feature. A test case is one protective operation on one piece of user data, traced end to end.
2. The oracle is downstream reality, never the system's own report. Each verification point compares a layer against independent evidence from the next layer or the external party.
3. Every handoff is a verification point. A failure is localized to the first transition where two adjacent layers disagree.

## Where AI fits

The chain definition (the architecture) determines what must be verified and where. The reconciler applies it deterministically. AI is applied on top, to classify and explain divergences at scale. It is not asked to decide what to check, because a model handed a codebase produces tests that check each layer against itself, which is the original failure mode automated.

## Relationship to standards

See `standards-mapping.md`. In short: ISO/IEC 25010 and ISO/IEC 25012 define the qualities CoCV verifies (functional correctness, integrity, accuracy, consistency, traceability); ISO/IEC/IEEE 29119 defines the process and documentation CoCV conforms to and catalogues techniques that verify behaviour within a system boundary. CoCV is proposed as an additional technique whose coverage items are transitions of user data between independent layers.
