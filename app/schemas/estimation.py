from enum import Enum
from pydantic import BaseModel, field_validator


class PreprocessingMode(str, Enum):
    none = "none"
    inline_cleaning = "inline_cleaning"
    two_phase = "two_phase"


class ExampleFormat(str, Enum):
    markdown = "markdown"
    json = "json"
    narrative = "narrative"


class EstimationRequest(BaseModel):
    transcription: str
    preprocessing: PreprocessingMode = PreprocessingMode.none
    example_format: ExampleFormat = ExampleFormat.markdown
    num_examples: int = 3
    model: str | None = None
    max_tokens: int = 4000
    thinking_budget: int | None = None
    evaluate: bool = True

    @field_validator("transcription")
    @classmethod
    def min_length(cls, v: str) -> str:
        if len(v.strip()) < 50:
            raise ValueError("transcription must be at least 50 characters")
        return v

    @field_validator("num_examples")
    @classmethod
    def valid_range(cls, v: int) -> int:
        if not 0 <= v <= 5:
            raise ValueError("num_examples must be between 0 and 5")
        return v


class GenerationOptions(BaseModel):
    transcription: str
    preprocessing: PreprocessingMode
    example_format: ExampleFormat
    num_examples: int
    model: str
    max_tokens: int
    thinking_budget: int | None
    evaluate: bool


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    preprocessing_input_tokens: int = 0
    preprocessing_output_tokens: int = 0


class StructureCheck(BaseModel):
    score: float
    issues: list[str]
    has_title: bool
    has_breakdown_table: bool
    has_totals_section: bool
    has_team_section: bool
    has_duration_section: bool
    hours_match: bool
    cost_match: bool
    finish_reason_ok: bool


class EstimationResponse(BaseModel):
    estimation: str
    model: str
    provider: str
    finish_reason: str
    preprocessing: str
    extracted_requirements: str | None
    latency_ms: int
    usage: TokenUsage
    validation: StructureCheck | None
