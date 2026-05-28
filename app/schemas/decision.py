from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .invoice import InvoiceExtraction


class WorkflowType(str, Enum):
    AP = "accounts_payable"
    AR = "accounts_receivable"


class ApprovalRecommendation(str, Enum):
    APPROVE = "approve"
    REVIEW = "review"
    REJECT = "reject"
    MISSING_INFO = "missing_info"


class EscalationLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_id: str = Field(..., min_length=1, description="Stable identifier for the retrieved knowledge source.")
    source_title: str = Field(..., min_length=1, description="Human-readable title for the cited source.")
    excerpt: str = Field(..., min_length=20, description="Relevant supporting excerpt from the source.")
    relevance_reason: str = Field(..., min_length=10, description="Why this source matters for the current decision.")


class AnomalyFlag(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(..., min_length=1, description="Machine-readable anomaly identifier.")
    message: str = Field(..., min_length=10, description="Human-readable explanation of the issue.")
    severity: EscalationLevel = Field(..., description="Operational severity of the anomaly.")


class APDecision(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=True)

    recommendation: ApprovalRecommendation = Field(..., description="Recommended AP action.")
    missing_fields: list[str] = Field(default_factory=list, description="Required AP fields missing from the extracted invoice.")
    reviewer_summary: str = Field(..., min_length=20, description="Short summary for a finance reviewer.")
    evidence: list[EvidenceItem] = Field(..., min_length=1, description="Grounding evidence supporting the decision.")
    policy_evidence: list[EvidenceItem] = Field(default_factory=list, description="Policy evidence used for AP validation and review.")
    anomalies: list[AnomalyFlag] = Field(default_factory=list, description="Detected workflow anomalies.")
    human_review_required: bool = Field(..., description="Whether the AP result requires a finance reviewer before action.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Estimated model confidence from 0 to 1.")


class ARDecision(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=True)

    escalation_level: EscalationLevel = Field(..., description="Recommended AR escalation level.")
    subject: str = Field(..., min_length=5, description="Readable follow-up subject line.")
    follow_up_email: str = Field(..., min_length=40, description="Grounded follow-up email body.")
    tts_safe_subject: str = Field(..., min_length=5, description="Voice-safe subject line for call or TTS workflows.")
    tts_safe_follow_up: str = Field(..., min_length=40, description="Voice-safe follow-up body with readable dates, amounts, and identifiers.")
    followup_subject: str = Field(..., min_length=5, description="Suggested email subject line.")
    followup_draft: str = Field(..., min_length=40, description="Grounded follow-up email body.")
    followup_subject_tts: str = Field(..., min_length=5, description="Voice-safe subject line for TTS or calling workflows.")
    followup_draft_tts: str = Field(..., min_length=40, description="Voice-safe follow-up body with readable dates, amounts, and identifiers.")
    evidence: list[EvidenceItem] = Field(..., min_length=1, description="Grounding evidence supporting the draft.")
    trigger_codes: list[str] = Field(default_factory=list, description="Workflow reasons that drove the AR escalation.")
    customer_tone: str | None = Field(default=None, description="Detected tone or reminder style for the customer.")
    human_review_required: bool = Field(..., description="Whether the AR result requires a finance reviewer before sending.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Estimated model confidence from 0 to 1.")


class WorkflowResult(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    workflow_type: WorkflowType = Field(..., description="Resolved workflow path for the case.")
    extraction: InvoiceExtraction = Field(..., description="Structured extraction output for the incoming document.")
    ap_decision: APDecision | None = Field(default=None, description="Decision payload for AP cases.")
    ar_decision: ARDecision | None = Field(default=None, description="Decision payload for AR cases.")

    @field_validator("ap_decision", "ar_decision")
    @classmethod
    def keep_optional_payloads_as_is(cls, value):
        return value

    @model_validator(mode="after")
    def validate_workflow_payloads(self) -> "WorkflowResult":
        if self.workflow_type == WorkflowType.AP:
            if self.ap_decision is None:
                raise ValueError("AP workflow results must include an ap_decision payload.")
            if self.ar_decision is not None:
                raise ValueError("AP workflow results cannot include an ar_decision payload.")
        if self.workflow_type == WorkflowType.AR:
            if self.ar_decision is None:
                raise ValueError("AR workflow results must include an ar_decision payload.")
            if self.ap_decision is not None:
                raise ValueError("AR workflow results cannot include an ap_decision payload.")
        return self
