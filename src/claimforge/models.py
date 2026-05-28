"""
ClaimForge AI — Data Model
==========================

Typed contracts between layers of the system. Every layer reads from and
writes to these Pydantic models. If you find yourself passing dicts around,
add a model instead.

Organization:
  1. Common primitives (Money, Citation, AgentStep)
  2. Enums (closed sets)
  3. Domain objects (Person, Vehicle, Driver, Injury, Page, ParsedDocument)
  4. Extraction output (ExtractedClaim)
  5. Agent node outputs (CoverageAnalysis, LiabilityAnalysis, etc.)
  6. Master state (ClaimState)
"""
from __future__ import annotations

#from datetime import date, datetime
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================
# 1. Common primitives
# ============================================================

class Money(BaseModel):
    """Monetary amount with explicit currency. Never use float for money."""
    amount: Decimal = Field(..., description="Amount in major currency units (e.g., dollars, not cents)")
    currency: str = Field(default="USD", description="ISO 4217 currency code")

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:,.2f}"


class BoundingBox(BaseModel):
    """Pixel-coordinate bounding box for citing source material on a page."""
    page: int = Field(..., description="1-indexed page number")
    x: float = Field(..., description="Left edge in page coordinates")
    y: float = Field(..., description="Top edge in page coordinates")
    width: float
    height: float


class Citation(BaseModel):
    """A reference to source material backing a claim made by the agent."""
    document_id: str = Field(..., description="ID of the source document")
    page: int = Field(..., description="1-indexed page number")
    excerpt: str = Field(..., description="The actual text from the source")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Pixel coordinates for UI highlighting")
    section: Optional[str] = Field(default=None, description="Document section (e.g., 'Exclusions IV.B')")


class AgentStep(BaseModel):
    """One step in the agent's execution trace. Powers observability."""
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    node_name: str = Field(..., description="Name of the agent node (e.g., 'coverage_node')")
    started_at: datetime
    completed_at: Optional[datetime] = None
    input_summary: str = Field(..., description="Brief description of what went in")
    output_summary: Optional[str] = Field(default=None, description="Brief description of what came out")
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_usd: Optional[Decimal] = None
    error: Optional[str] = None


# ============================================================
# 2. Enums (closed sets)
# ============================================================

class CoverageType(str, Enum):
    """The six standard US personal auto coverages."""
    BODILY_INJURY_LIABILITY = "bodily_injury_liability"
    PROPERTY_DAMAGE_LIABILITY = "property_damage_liability"
    COLLISION = "collision"
    COMPREHENSIVE = "comprehensive"
    UNINSURED_UNDERINSURED_MOTORIST = "um_uim"
    MEDICAL_PAYMENTS = "medical_payments"
    PERSONAL_INJURY_PROTECTION = "pip"


class ClaimStatus(str, Enum):
    """Lifecycle states for a claim."""
    NEW = "new"
    INVESTIGATING = "investigating"
    AWAITING_DOCS = "awaiting_docs"
    READY_TO_DECIDE = "ready_to_decide"
    DENIED = "denied"
    SETTLED = "settled"
    CLOSED = "closed"
    SIU_REFERRED = "siu_referred"


class DocumentType(str, Enum):
    POLICY = "policy"
    FNOL = "fnol"
    POLICE_REPORT = "police_report"
    ESTIMATE = "estimate"
    PHOTO = "photo"
    MEDICAL_BILL = "medical_bill"
    STATEMENT = "statement"
    UNKNOWN = "unknown"


class FaultBasis(str, Enum):
    """How fault is allocated. Depends on US state."""
    COMPARATIVE = "comparative"      # most states
    CONTRIBUTORY = "contributory"    # AL, MD, NC, VA, DC
    NO_FAULT = "no_fault"            # FL, MI, NY, NJ, PA (choice), etc.


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LetterType(str, Enum):
    COVERAGE_DECISION = "coverage_decision"
    DENIAL = "denial"
    REQUEST_DOCS = "request_docs"
    SIU_REFERRAL = "siu_referral"
    RESERVATION_OF_RIGHTS = "reservation_of_rights"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


# ============================================================
# 3. Domain objects
# ============================================================

class Person(BaseModel):
    """A person referenced in a claim — insured, claimant, witness, driver."""
    person_id: str = Field(default_factory=lambda: str(uuid4()))
    full_name: str
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    drivers_license_number: Optional[str] = None
    drivers_license_state: Optional[str] = None


class Vehicle(BaseModel):
    """A vehicle involved in a claim."""
    vehicle_id: str = Field(default_factory=lambda: str(uuid4()))
    vin: Optional[str] = Field(default=None, description="17-character VIN")
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    license_plate: Optional[str] = None
    license_plate_state: Optional[str] = None
    owner_person_id: Optional[str] = Field(default=None, description="References Person.person_id")

    @field_validator("vin")
    @classmethod
    def validate_vin_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) != 17:
            raise ValueError("VIN must be exactly 17 characters")
        return v


class Driver(BaseModel):
    """A driver involved in the incident — may or may not be the owner."""
    person_id: str = Field(..., description="References Person.person_id")
    vehicle_id: str = Field(..., description="References Vehicle.vehicle_id")
    is_covered_driver: Optional[bool] = Field(
        default=None,
        description="Whether this driver is listed on the policy"
    )


class Injury(BaseModel):
    """An injury claimed in the incident."""
    person_id: str = Field(..., description="References Person.person_id")
    description: str
    severity: Severity
    medical_treatment_received: bool = False


class TextBox(BaseModel):
    """Word-level positional info preserved during ingestion for citations."""
    text: str
    bounding_box: BoundingBox


class Page(BaseModel):
    """One page of a parsed document."""
    page_number: int
    text: str
    text_boxes: list[TextBox] = Field(default_factory=list)
    page_image_path: Optional[str] = Field(default=None, description="Filesystem path to rendered page image")


class ParsedDocument(BaseModel):
    """Output of the ingestion layer. What's in the file, normalized."""
    document_id: str = Field(default_factory=lambda: str(uuid4()))
    source_file: str = Field(..., description="Path to the original uploaded file")
    document_type: DocumentType
    pages: list[Page]
    full_text: str
    sha256: str = Field(..., description="Content hash for deduplication")
    #ingested_at: datetime = Field(default_factory=datetime.utcnow)
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)


# ============================================================
# 4. Extraction output
# ============================================================

class ExtractedClaim(BaseModel):
    """
    Structured claim assembled from parsed documents.
    This is what every agent node reads from.
    """
    claim_number: Optional[str] = Field(default=None, description="Carrier's claim number, if known")
    policy_number: str

    date_of_loss: date
    date_reported: Optional[date] = None
    state_of_loss: str = Field(..., description="2-letter US state code where the loss occurred")

    description: str = Field(..., description="Free-form narrative of what happened")

    insured: Person
    claimant: Person = Field(..., description="May be the same person as insured, or a third party")

    vehicles: list[Vehicle] = Field(default_factory=list)
    drivers: list[Driver] = Field(default_factory=list)
    injuries: list[Injury] = Field(default_factory=list)

    police_report_number: Optional[str] = None
    citations_issued: list[str] = Field(default_factory=list, description="Traffic citations issued at the scene")

    source_documents: list[str] = Field(
        default_factory=list,
        description="document_id values that contributed to this extraction"
    )
    extraction_confidence: dict[str, float] = Field(
        default_factory=dict,
        description="Field-name → confidence (0.0–1.0). Lets the agent know what to trust."
    )


# ============================================================
# 5. Agent node outputs
# ============================================================

class CoverageDetermination(BaseModel):
    """One coverage's verdict within a CoverageAnalysis."""
    coverage_type: CoverageType
    applies: bool
    limit: Optional[Money] = Field(default=None, description="Policy limit for this coverage")
    deductible: Optional[Money] = None
    triggering_conditions_met: bool
    exclusions_invoked: list[str] = Field(
        default_factory=list,
        description="Names of any exclusions that bar this coverage"
    )
    reasoning: str
    citations: list[Citation] = Field(default_factory=list)


class CoverageAnalysis(BaseModel):
    """Output of the Coverage node."""
    is_covered: bool = Field(..., description="True if at least one coverage applies and no blocking exclusions")
    policy_in_force_on_date_of_loss: bool
    driver_is_covered: bool

    applicable_coverages: list[CoverageDetermination] = Field(default_factory=list)
    overall_reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class LiabilityAnalysis(BaseModel):
    """Output of the Liability node."""
    fault_basis: FaultBasis
    party_fault_percentages: dict[str, float] = Field(
        ...,
        description="person_id → fault percentage (0-100). Must sum to 100."
    )
    primary_contributing_factor: str
    reasoning: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def fault_must_sum_to_100(self) -> "LiabilityAnalysis":
        total = sum(self.party_fault_percentages.values())
        if not (99.5 <= total <= 100.5):  # small tolerance for float math
            raise ValueError(f"Fault percentages must sum to 100, got {total}")
        return self


class VehicleDamage(BaseModel):
    """Damage assessment for one vehicle."""
    vehicle_id: str
    damaged_areas: list[str] = Field(default_factory=list, description="e.g., 'front_bumper', 'driver_door'")
    severity: Severity
    repair_estimate_amount: Optional[Money] = None
    acv: Optional[Money] = Field(default=None, description="Actual Cash Value of the vehicle")
    is_total_loss: bool
    photos_analyzed: list[str] = Field(default_factory=list, description="document_ids of photos used")
    reasoning: str


class DamageAnalysis(BaseModel):
    """Output of the Damage node."""
    per_vehicle: list[VehicleDamage]
    overall_reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class FraudSignal(BaseModel):
    """One indicator of potential fraud. Fraud node returns a list."""
    signal_type: str = Field(
        ...,
        description="Short identifier, e.g., 'narrative_photo_mismatch', 'prior_pattern', 'late_reporting'"
    )
    severity: Severity
    description: str = Field(..., description="Human-readable explanation of the inconsistency")
    evidence: list[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class ReserveRecommendation(BaseModel):
    """Output of the Reserve node."""
    indemnity_reserve: Money
    lae_reserve: Money = Field(..., description="Loss Adjustment Expense reserve")
    total_reserve: Money

    breakdown_by_coverage: dict[CoverageType, Money] = Field(default_factory=dict)
    similar_claims_referenced: list[str] = Field(
        default_factory=list,
        description="claim_ids from past-claims RAG that informed this estimate"
    )
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def total_must_equal_components(self) -> "ReserveRecommendation":
        expected = self.indemnity_reserve.amount + self.lae_reserve.amount
        if abs(self.total_reserve.amount - expected) > Decimal("0.01"):
            raise ValueError(
                f"total_reserve ({self.total_reserve.amount}) must equal "
                f"indemnity + LAE ({expected})"
            )
        return self


class DraftLetter(BaseModel):
    """Output of the Letter node."""
    letter_type: LetterType
    recipient: Person
    subject: str
    body: str
    cited_policy_sections: list[Citation] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================
# 6. Master state
# ============================================================

class ClaimState(BaseModel):
    """
    The state object that flows through the LangGraph state machine.
    Every node reads it, every node may write to it.
    """
    claim_id: str = Field(default_factory=lambda: str(uuid4()))
    status: ClaimStatus = ClaimStatus.NEW

    raw_documents: list[ParsedDocument] = Field(default_factory=list)
    extracted_claim: Optional[ExtractedClaim] = None

    coverage_analysis: Optional[CoverageAnalysis] = None
    liability_analysis: Optional[LiabilityAnalysis] = None
    damage_analysis: Optional[DamageAnalysis] = None
    fraud_signals: list[FraudSignal] = Field(default_factory=list)
    reserve_recommendation: Optional[ReserveRecommendation] = None
    draft_letter: Optional[DraftLetter] = None

    human_approvals: dict[str, ApprovalStatus] = Field(
        default_factory=dict,
        description="node_name → approval status from the adjuster"
    )
    trace: list[AgentStep] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def append_step(self, step: AgentStep) -> None:
        """Convenience method for nodes to log their work."""
        self.trace.append(step)
        self.updated_at = datetime.now(timezone.utc)  #datetime.utcnow()


# ============================================================
# Self-test: instantiate a tiny example to verify schemas load
# ============================================================

if __name__ == "__main__":
    # A minimal sanity check — run `python -m claimforge.models` to verify.
    state = ClaimState()
    print(f"Empty ClaimState: {state.claim_id}, status={state.status}")

    insured = Person(full_name="Jane Doe", date_of_birth=date(1985, 4, 12))
    vehicle = Vehicle(vin="1HGBH41JXMN109186", year=2021, make="Honda", model="Civic")
    claim = ExtractedClaim(
        policy_number="POL-12345",
        date_of_loss=date(2026, 3, 15),
        state_of_loss="CT",
        description="Rear-ended at a stop light on Main St.",
        insured=insured,
        claimant=insured,
        vehicles=[vehicle],
    )
    print(f"\nExtractedClaim built: policy={claim.policy_number}, "
          f"vehicles={len(claim.vehicles)}")

    # Pretty-print the JSON schema for the LLM
    print("\nJSON schema for ExtractedClaim (first 200 chars):")
    import json
    schema = ExtractedClaim.model_json_schema()
    print(json.dumps(schema, indent=2)[:200] + "...")
