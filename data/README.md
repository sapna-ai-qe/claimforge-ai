# ClaimForge AI — Sample Data

This folder contains the synthetic data ClaimForge AI is built and tested against: a sample auto insurance policy and a set of complete claim packets, each with ground-truth expected outputs.

All data here is **fictional** and created for software testing. The carrier ("Constellation Auto Insurance"), people, vehicles, and incidents do not represent real entities.

---

## Why this data exists

A claims-processing pipeline can't be built or evaluated without realistic inputs and known-correct outputs. This folder provides both:

- **Inputs** — claim packets (FNOL forms, police reports, repair estimates, damage photo descriptions) that resemble what an adjuster actually receives.
- **Ground truth** — for each claim, a `ground_truth.json` describing the structured outputs the pipeline *should* produce at every stage (extraction, coverage, liability, damage, fraud, reserve, letter).

The ground truth files are the interface between the data and the [evaluation harness](../evals/): the harness runs each claim through the pipeline and scores the actual output against the expected output.

---

## Folder structure

```
data/
├── README.md                          ← this file
├── policies/
│   └── constellation_auto_policy_v1.md   ← the master policy all claims reference
└── claims/
    ├── claim_001_covered/
    │   ├── fnol.md
    │   ├── police_report.md
    │   ├── repair_estimate.md
    │   ├── damage_photos.md
    │   └── ground_truth.json
    ├── claim_002_denied/
    │   ├── fnol.md
    │   ├── police_report.md
    │   ├── repair_estimate.md
    │   ├── damage_photos.md
    │   └── ground_truth.json
    └── claim_003_fraud/
        ├── fnol.md
        ├── adjuster_investigation_note.md   ← note: no police report (see scenario)
        ├── repair_estimate.md
        ├── damage_photos.md
        └── ground_truth.json
```

---

## The policy

`policies/constellation_auto_policy_v1.md` is a ~5-page personal auto policy for the fictional Constellation Auto Insurance Company, written in the structure of a real policy: declarations page, insuring agreement, six coverage parts, exclusions, conditions, and general provisions.

Key facts the claims rely on:

- **State**: Connecticut (a comparative-negligence / tort state)
- **Policy period**: 01/15/2026 – 01/15/2027
- **Named insureds**: Maria and Carlos Rodriguez
- **Excluded driver**: Diego Rodriguez (their son) — central to Claim 002
- **Coverages**: BI/PD liability, UM/UIM, MedPay, Collision ($500 deductible), Comprehensive ($250 deductible)
- **Total loss threshold**: 75% of ACV (Part III.C)
- **Late notice provision**: 30 days (Part VII.B)
- **Fraud provision**: policy voidance for material misrepresentation (Part VII.C)

This policy is the document the **Policy RAG** layer indexes and retrieves from when answering coverage questions.

---

## The three scenarios

Each claim exercises a different decision path through the [agent flow](../docs/ARCHITECTURE.md).

### Claim 001 — Covered (happy path)

| | |
|---|---|
| **Scenario** | Insured rear-ended while stopped at a stop sign; clear third-party fault |
| **Expected outcome** | Coverage confirmed (Collision + MedPay) |
| **Decision path** | extract → coverage (covered) → liability → damage → fraud (clean) → reserve → coverage decision letter |
| **What it tests** | The full happy path; clear liability; multiple applicable coverages; clean fraud check (empty signal list); subrogation opportunity |

The baseline correctness check. Every fact is internally consistent across all documents. The fraud signal list should be **empty**.

### Claim 002 — Denied (excluded driver)

| | |
|---|---|
| **Scenario** | The excluded driver (Diego) was operating the insured vehicle and hit a parked car. The FNOL claims the named insured was driving; the police report shows it was Diego. |
| **Expected outcome** | Coverage **denied** (excluded driver) |
| **Decision path** | extract → coverage (NOT covered) → denial letter (short-circuits the rest) |
| **What it tests** | (1) Source-conflict resolution — preferring the police report over the self-reported FNOL on who was driving. (2) Multi-section policy retrieval — the excluded-driver exclusion appears in Parts II, III, IV, and VI, and all should be cited. (3) Fraud detection — the FNOL misstatement is a high-severity signal. |

Demonstrates the denial branch and the agent's ability to reconcile conflicting sources.

### Claim 003 — SIU referral (suspected fraud)

| | |
|---|---|
| **Scenario** | A claimed overnight hit-and-run on a parked BMW, reported 16 days late, with no police report, damage that appears weathered/aged, a prior service record showing pre-existing front-end damage, and a described impact direction that doesn't match the damage pattern. |
| **Expected outcome** | **SIU referral** (pause for investigation — neither approve nor deny) |
| **Decision path** | extract → coverage (facially covered, pending) → damage → fraud (cumulative HIGH) → SIU referral |
| **What it tests** | Multi-signal fraud aggregation. No single signal proves fraud; six moderate signals (2 high, 3 medium, 1 low) collectively exceed the SIU referral threshold. Also tests the "pause, don't deny" logic — the legally correct response to suspicion. |

The most sophisticated scenario, and the best demonstration of agentic multi-document reasoning. Note this claim has an `adjuster_investigation_note.md` instead of a police report — the *absence* of a police report is itself a fraud signal, and the pipeline must handle claims that don't have every document type.

---

## How ground_truth.json maps to the data model

Each `ground_truth.json` mirrors the Pydantic models in [`src/claimforge/models.py`](../src/claimforge/models.py). The top-level keys correspond to the agent node outputs:

| JSON key | Pydantic model | Produced by |
|---|---|---|
| `extracted_claim` | `ExtractedClaim` | extraction layer |
| `coverage_analysis` | `CoverageAnalysis` | coverage node |
| `liability_analysis` | `LiabilityAnalysis` | liability node |
| `damage_analysis` | `DamageAnalysis` | damage node |
| `fraud_signals` | `list[FraudSignal]` | fraud node |
| `reserve_recommendation` | `ReserveRecommendation` | reserve node |
| `expected_letter` | `DraftLetter` (described) | letter node |

### Convention: underscore-prefixed keys are documentation, not data

Keys beginning with `_` (e.g., `_meta`, `_expected_citations`, `_note`) are **annotations for humans and the eval harness**, not fields in the Pydantic models. They explain reasoning, list expected citations, or flag teaching points. When loading ground truth for evaluation, strip or ignore underscore-prefixed keys before comparing against model output.

### Convention: empty list vs. null

`fraud_signals` is always a **list** — an empty list `[]` means "the fraud node ran and found nothing" (Claim 001), while a populated list means signals were found (Claims 002, 003). This matches the data model, where `fraud_signals` is `list[FraudSignal]`, never `None`.

---

## A note on damage photos

Because real images can't be included here, each claim's `damage_photos.md` contains detailed **text descriptions** of what each photo would show. In the production pipeline, the damage node receives actual image bytes and uses a vision LLM. For testing, the vision call can be mocked to return these descriptions. Real placeholder images (or smartphone photos of staged minor damage) can be added later for end-to-end vision testing.

---

## Adding new scenarios

To add a scenario, create a new folder under `claims/` following the same structure, and write a `ground_truth.json` matching the data model. Good candidates for future scenarios:

- A total-loss claim (repair cost exceeds 75% of ACV)
- A multi-vehicle accident (tests the list-of-vehicles handling)
- A claim missing required documents (tests the "request docs" pause branch)
- A comparative-negligence split (e.g., 70/30 fault) rather than clear 100/0 liability
- A claim under no-fault rules (would require a different state and policy variant)
