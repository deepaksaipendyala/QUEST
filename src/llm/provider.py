from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List, Optional
import math

from src.observability.cost import calculate_cost


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    temperature: float
    top_p: float
    collect_logprobs: bool = False


@dataclass
class LLMResult:
    text: str
    token_logprobs: Optional[List[float]]
    entropy: Optional[float]
    avg_logprob: Optional[float]
    token_count: int
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0


def llm_enabled() -> bool:
    api_key = os.getenv("OPENAI_API_KEY")
    dry_flag = os.getenv("DRY_LLM", "0")
    return bool(api_key) and dry_flag != "1"


def _extract_code_from_markdown(text: str) -> str:
    """Extract Python code from markdown-formatted text."""
    import re
    
    # Try various markdown code block patterns
    patterns = [
        r'```python\s*\n(.*?)```',  # ```python\n...\n```
        r'```py\s*\n(.*?)```',      # ```py\n...\n```
        r'```\s*python\s*\n(.*?)```',  # ``` python\n...\n```
        r'```\s*\n(.*?)```',        # ```\n...\n```
    ]
    
    for pattern in patterns:
        code_blocks = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if code_blocks:
            # Return the largest code block (likely the main code)
            return max(code_blocks, key=len).strip()
    
    # If no code blocks found, check if text starts with common Python patterns
    # (might be plain code without markdown)
    text_stripped = text.strip()
    if text_stripped.startswith(('import ', 'from ', 'def ', 'class ', '#')):
        return text_stripped
    
    # Last resort: return original text
    return text_stripped


def _compute_entropy(token_logprobs: List[float]) -> Optional[float]:
    if not token_logprobs:
        return None
    entropies: List[float] = []
    for lp in token_logprobs:
        try:
            prob = math.exp(lp)
        except OverflowError:
            continue
        if prob <= 0.0:
            continue
        entropies.append(-math.log(prob, 2))
    if not entropies:
        return None
    return sum(entropies) / len(entropies)


def run_completion(prompt: str, cfg: LLMConfig) -> LLMResult:
    if not llm_enabled():
        return LLMResult("", None, None, None, 0, 0, 0, 0.0)
    if cfg.provider.lower() != "openai":
        return LLMResult("", None, None, None, 0, 0, 0, 0.0)

    import openai  # type: ignore

    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        timeout=60.0  # prevent hanging
    )

    extra_args = {}
    if cfg.collect_logprobs:
        extra_args["logprobs"] = True
        extra_args["top_logprobs"] = 0

    resp = client.chat.completions.create(
        model=cfg.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=cfg.temperature,
        top_p=cfg.top_p,
        **extra_args,
    )
    content = resp.choices[0].message.content or ""
    
    input_tokens = 0
    output_tokens = 0
    if hasattr(resp, "usage") and resp.usage:
        input_tokens = getattr(resp.usage, "prompt_tokens", 0)
        output_tokens = getattr(resp.usage, "completion_tokens", 0)
    
    estimated_cost = calculate_cost(cfg.model, input_tokens, output_tokens)
    
    token_logprobs: Optional[List[float]] = None
    avg_logprob: Optional[float] = None
    entropy: Optional[float] = None
    token_count = output_tokens if output_tokens > 0 else 0

    if cfg.collect_logprobs:
        logprob_container = getattr(resp.choices[0], "logprobs", None)
        if logprob_container and getattr(logprob_container, "content", None):
            token_logprobs = []
            for item in logprob_container.content:
                lp = getattr(item, "logprob", None)
                if lp is not None:
                    token_logprobs.append(float(lp))
            if token_logprobs:
                token_count = len(token_logprobs)
                avg_logprob = sum(token_logprobs) / token_count
                entropy = _compute_entropy(token_logprobs)
        else:
            if token_count == 0:
                token_count = len(content.split())

    if token_count == 0:
        token_count = output_tokens if output_tokens > 0 else len(content.split())

    cleaned_content = _extract_code_from_markdown(content)
    return LLMResult(
        text=cleaned_content,
        token_logprobs=token_logprobs,
        entropy=entropy,
        avg_logprob=avg_logprob,
        token_count=token_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=estimated_cost,
    )
