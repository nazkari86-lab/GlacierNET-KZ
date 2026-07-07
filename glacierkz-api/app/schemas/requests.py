from typing import Optional

from pydantic import BaseModel, Field


class TrendRequest(BaseModel):
    file_ids: list[str] = Field(..., min_length=2, description="List of result IDs for different years")
    years: list[int] = Field(..., min_length=2)
    forecast_until: int = 2050


class LLMAnalyzeRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Free-form analysis prompt")
    provider: str = Field("", description="LLM provider: openai, anthropic, groq, google, ollama, openrouter")
    model: str = Field("", description="Model name within provider")
    mode: str = Field("describe", description="Analysis mode: describe, trend, compare")
    context: Optional[str] = Field(None, description="Optional context JSON")
    api_key: Optional[str] = Field(None, description="User-provided API key for the selected provider")


class FetchModelsRequest(BaseModel):
    provider: str = Field(..., description="LLM provider: openai, anthropic, groq, google, openrouter")
    api_key: str = Field(..., min_length=1, description="User-provided API key for the provider")
