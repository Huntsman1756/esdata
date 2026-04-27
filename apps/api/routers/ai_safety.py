"""Adversarial testing router for AI Act compliance (Fase 24.7).

Endpoints for running adversarial tests and checking AI safety.
"""

from fastapi import APIRouter, Query

from pydantic import BaseModel, Field

from services.adversarial import (
    detect_prompt_injection,
    is_out_of_domain,
    run_adversarial_test,
    sanitize_input,
)


router = APIRouter(prefix="/v1/ai/safety", tags=["ai_safety"])


class InjectionCheckRequest(BaseModel):
    """Request for prompt injection detection."""

    text: str = Field(description="Text to check for injection")


class InjectionCheckResponse(BaseModel):
    """Response for injection detection."""

    injection: bool = Field(description="Whether injection was detected")
    types: list[str] = Field(default_factory=list, description="Injection types found")
    score: float = Field(ge=0, le=1, description="Injection confidence score")
    matched_patterns: list[str] = Field(default_factory=list, description="Matched pattern types")


class SanitizeRequest(BaseModel):
    """Request for input sanitization."""

    text: str = Field(description="Text to sanitize")
    max_length: int = Field(default=4000, description="Maximum allowed length")


class SanitizeResponse(BaseModel):
    """Response for sanitization."""

    cleaned: str = Field(description="Sanitized text")
    blocked: bool = Field(description="Whether the input was blocked")
    reason: str | None = Field(default=None, description="Reason for blocking")
    length_truncated: bool = Field(description="Whether input was truncated")
    warnings: list[str] = Field(default_factory=list, description="Sanitization warnings")


class DomainCheckRequest(BaseModel):
    """Request for domain validation."""

    query: str = Field(description="Query to check against domain")


class DomainCheckResponse(BaseModel):
    """Response for domain check."""

    out_of_domain: bool = Field(description="Whether the query is out of domain")
    domain_score: float = Field(ge=0, le=1, description="Domain relevance score")
    matched_keywords: list[str] = Field(default_factory=list, description="Matched domain keywords")
    reason: str = Field(description="Explanation of the result")


class AdversarialTestRequest(BaseModel):
    """Request for a single adversarial test."""

    test_name: str = Field(description="Name of the test")
    input_text: str = Field(description="Adversarial input to test")


class AdversarialTestResponse(BaseModel):
    """Response for adversarial test."""

    test_name: str = Field(description="Test name")
    injection_detected: bool = Field(description="Whether injection was detected")
    injection_types: list[str] = Field(default_factory=list)
    injection_score: float = Field(ge=0, le=1, default=0.0)
    blocked: bool = Field(description="Whether the input was blocked")
    out_of_domain: bool = Field(description="Whether out of domain")
    domain_score: float = Field(ge=0, le=1, default=0.0)
    passed: bool = Field(description="Whether the test passed")


@router.post(
    "/injection/check",
    response_model=InjectionCheckResponse,
    summary="Check for prompt injection",
    description="Detect prompt injection attempts in the given text.",
)
async def check_injection(req: InjectionCheckRequest):
    """Check text for prompt injection."""
    result = detect_prompt_injection(req.text)
    return InjectionCheckResponse(**result)


@router.post(
    "/sanitize",
    response_model=SanitizeResponse,
    summary="Sanitize AI input",
    description="Sanitize and validate input for AI components.",
)
async def sanitize(req: SanitizeRequest):
    """Sanitize input text."""
    result = sanitize_input(req.text, max_length=req.max_length)
    return SanitizeResponse(**result)


@router.post(
    "/domain/check",
    response_model=DomainCheckResponse,
    summary="Check domain relevance",
    description="Verify if a query is within the fiscal-regulatory domain.",
)
async def check_domain(req: DomainCheckRequest):
    """Check if query is in domain."""
    result = is_out_of_domain(req.query)
    return DomainCheckResponse(**result)


@router.post(
    "/test",
    response_model=AdversarialTestResponse,
    summary="Run adversarial test",
    description="Run a single adversarial test against the input.",
)
async def run_test(req: AdversarialTestRequest):
    """Run adversarial test."""
    result = run_adversarial_test(req.test_name, req.input_text)
    return AdversarialTestResponse(
        test_name=result.test_name,
        injection_detected=result.injection_detected,
        injection_types=result.injection_types,
        injection_score=result.injection_score,
        blocked=result.blocked,
        out_of_domain=result.out_of_domain,
        domain_score=result.domain_score,
        passed=result.passed,
    )
