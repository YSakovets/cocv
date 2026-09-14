# Chain of Custody Verification (CoCV)

## Standards Alignment and Contribution Statement

**Method:** Chain of Custody Verification (CoCV)
**Defect class addressed:** Silent protection failures
**Version:** 0.1.1
**Last revised:** 14 September 2026
**Author:** Yevheniia Sakovets
**Permanent identifier:** https://doi.org/10.5281/zenodo.22736556
**Licence:** CC BY 4.0

*Standards are referenced by characteristic name and edition. No text from ISO or IEEE standards is reproduced in this document.*

---

## 1. Scope of this document

CoCV is a cross-layer verification methodology for consumer privacy and security software. It detects *silent protection failures*: cases in which software reports to the user that a protective operation has succeeded while the operation did not complete.

This document maps CoCV to three published standards:

| Standard | What it defines | Why CoCV maps to it |
|---|---|---|
| ISO/IEC 25010:2023 | Software product quality model (9 characteristics) | Names the product qualities a silent protection failure violates |
| ISO/IEC 25012 | Data quality model (15 characteristics) | Names the data qualities CoCV verifies at each handoff |
| ISO/IEC/IEEE 29119 | Software testing processes, documentation, techniques | Locates CoCV within recognised test practice and identifies the gap it fills |

The purpose of the mapping is twofold: to show that CoCV verifies named, standardised quality attributes rather than an ad hoc notion of "quality", and to identify precisely where existing standards define a requirement but provide no technique to verify it.

---

## 2. The verification chain

CoCV treats a protective operation as a chain of custody over user data. Each transfer between independent layers is a link. A silent protection failure is a broken link that the surrounding system does not surface.

Representative links in a consumer privacy or security product:

```
User input  ->  Client/UI  ->  API layer  ->  Backend service  ->  External party  ->  Backend state  ->  API layer  ->  Client/UI  ->  User
```

Each numbered verification point below is checked at one or more of these transitions.

| # | Verification point | What is checked |
|---|---|---|
| V1 | Request capture | Data the user submitted reaches the backend complete and unaltered |
| V2 | Dispatch confirmation | The operation was actually transmitted to its destination, not only queued, logged, or marked as pending |
| V3 | Response interpretation | External or downstream responses are parsed correctly; ambiguous, empty, or error responses are not defaulted to success |
| V4 | State reconciliation | The recorded internal state of the operation matches its actual outcome |
| V5 | User-facing truthfulness | The status presented to the user matches the reconciled internal state |
| V6 | Partial failure handling | When a subset of an operation fails, the system does not report aggregate success |
| V7 | Secure handling in transit and at rest | Data remains protected at each hop and does not appear in cleartext where it should not |
| V8 | Persistence over time | The effect of the operation holds; data does not reappear and suppression is not silently lost |
| V9 | Telemetry fidelity | Events and metrics reported about the operation match what actually occurred |
| V10 | Recovery integrity | After a failed transition, the operation resumes without data loss or duplication |

---

## 3. Mapping to ISO/IEC 25010:2023 (product quality)

ISO/IEC 25010:2023 defines nine product quality characteristics: functional suitability, performance efficiency, compatibility, interaction capability, reliability, security, maintainability, flexibility, and safety.

CoCV addresses four of the nine. It does **not** address the remaining five, and does not claim to.

| Verification point | Characteristic | Sub-characteristic | What the check evidences |
|---|---|---|---|
| V1 | Functional Suitability | Functional completeness | The full set of user-submitted data enters the operation, not a subset |
| V2 | Functional Suitability | Functional correctness | The operation performs the action it reports, not a proxy for it |
| V3 | Functional Suitability | Functional correctness | Outcomes are derived from actual responses, not from default assumptions |
| V4 | Functional Suitability | Functional correctness | Recorded state corresponds to reality |
| V5 | Functional Suitability | Functional correctness | The result presented to the user is accurate |
| V6 | Reliability | Fault tolerance | Degraded operation is reported as degraded, not as success |
| V7 | Security | Confidentiality, Integrity | Data remains protected and unaltered across each transfer |
| V8 | Security | Integrity | The protective effect persists and is not silently reversed |
| V9 | Security | Accountability | Recorded evidence of the operation reflects what occurred |
| V10 | Reliability | Recoverability | Interrupted operations resume without loss or duplication |
| V2, V3 | Compatibility | Interoperability | Exchanges with external systems are correctly completed and interpreted |

**Characteristics CoCV does not address:** performance efficiency, interaction capability, maintainability, flexibility, safety.

---

## 4. Mapping to ISO/IEC 25012 (data quality)

ISO/IEC 25012 defines data quality characteristics across inherent, system-dependent, and combined categories. Because CoCV verifies data in motion rather than a product feature in isolation, this model describes the object of verification more directly than the product model does.

| Verification point | Data quality characteristic | What the check evidences |
|---|---|---|
| V1 | Completeness | No fields are dropped between layers |
| V1, V4, V5 | Accuracy | Values remain correct relative to what the user submitted |
| V4, V5 | Consistency | Representations of the same operation agree across layers |
| V8 | Currentness | State reflects the present reality of the operation, not a stale record |
| V7 | Confidentiality | Data is accessible only where it should be |
| V2, V9 | Traceability | The path of the operation through the system is auditable end to end |
| V3, V4 | Credibility | Recorded outcomes are supported by actual downstream evidence |
| V10 | Recoverability | Data survives interruption of the operation |

**Note.** Traceability is the characteristic most central to CoCV and the one least served by conventional feature-level testing, which verifies the endpoints of an operation but not the path between them.

---

## 5. Mapping to ISO/IEC/IEEE 29119 (testing processes, documentation, techniques)

The mapping to 29119 is structural rather than attribute-based: it locates CoCV within recognised test practice.

### 5.1 Part 2 (test processes)

| 29119 process area | CoCV placement |
|---|---|
| Test design and implementation | CoCV operates here as a design technique: it determines *what* must be verified at each transition, derived from the system architecture |
| Test execution | CoCV checks execute across layers within existing execution processes |
| Test monitoring and control | CoCV outputs (divergence location, defect classification) feed standard defect management and reporting |

### 5.2 Part 3 (test documentation)

CoCV artefacts correspond to documented types in Part 3, demonstrating process conformance rather than parallel practice.

| CoCV artefact | 29119 Part 3 document type |
|---|---|
| Verification chain definition per product | Test design specification |
| Per-transition verification points (V1 to V10) | Test case specification |
| Execution and divergence-analysis procedure | Test procedure specification |
| Coverage matrix of protective operations against verification points | Test design specification (coverage items) |
| Divergence and defect report | Test completion report / incident report |

### 5.3 Part 4 (test design techniques): the gap

Part 4 catalogues established test design techniques, including specification-based techniques such as equivalence partitioning, boundary value analysis, decision table testing, state transition testing, scenario testing, and combinatorial techniques.

These techniques verify behaviour **within a defined system boundary**. Their coverage items are inputs, states, decisions, and paths inside the unit under test. A silent protection failure occurs **between** boundaries: each individual layer satisfies its own specification, and every technique in the catalogue therefore passes.

CoCV is proposed as an additional specification-based technique whose coverage items are **transitions of user data between independent layers**, evaluated against the protective claim the system makes to the user.

Nearest existing relatives, and why they are insufficient:

| Related technique | Why it does not cover this defect class |
|---|---|
| State transition testing | Models states within one system; does not reconcile state across independent systems |
| Scenario / use case testing | Follows a user journey but accepts the interface's own report of success as the oracle |
| Integration testing (general) | Verifies that interfaces exchange data; does not verify that the claimed operation completed |
| Data cycle / CRUD-matrix testing | Verifies data lifecycle within an application's own data model, not across external handoffs |

---

## 6. Contribution statement

ISO/IEC 25010:2023 names functional correctness as a sub-characteristic of functional suitability, and integrity and accountability as sub-characteristics of security. ISO/IEC 25012:2008 names accuracy, consistency and traceability among the required quality characteristics of data. ISO/IEC/IEEE 29119 defines the processes and documentation by which software is tested, and its Part 4 catalogues the techniques available for designing tests.

None of the three supplies a technique for verifying that a protective operation on personal data completed end to end across independent system layers. In consumer privacy and security software, that condition is what the named characteristics rest on: when a handoff between layers fails silently, every layer still satisfies its own specification, and the attributes these standards require are violated without any test reporting it.

Chain of Custody Verification fills that gap. It conforms to the process and documentation model of ISO/IEC/IEEE 29119, verifies characteristics named in ISO/IEC 25010:2023 and ISO/IEC 25012:2008, and supplies the technique those standards assume but do not define: one whose coverage items are the transitions of user data between independent layers, evaluated against the protective claim the product makes to the user.
