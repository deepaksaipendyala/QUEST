from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    temperature: float
    top_p: float


def llm_enabled() -> bool:
    api_key = os.getenv("OPENAI_API_KEY")
    dry_flag = os.getenv("DRY_LLM", "0")
    return bool(api_key) and dry_flag != "1"


def run_completion(prompt: str, cfg: LLMConfig) -> str:
    if not llm_enabled():
        return ""
    if cfg.provider.lower() != "openai":
        return ""

    import openai  # type: ignore

    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=cfg.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=cfg.temperature,
        top_p=cfg.top_p,
    )
    return resp.choices[0].message.content or ""
