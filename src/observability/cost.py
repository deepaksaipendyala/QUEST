from __future__ import annotations

MODEL_COST_PER_INPUT: dict[str, float] = {
    "gpt-3.5-turbo-0125": 0.0000005,
    "gpt-4-turbo-2024-04-09": 0.00001,
    "gpt-4o-2024-05-13": 0.000005,
    "gpt-4o-mini": 0.15 / 1_000_000,  # $0.15 per 1M tokens = $1.5e-7 per token
    "gpt-4o": 2.5 / 1_000_000,  # $2.50 per 1M tokens = $2.5e-6 per token
    "gpt-4-0613": 0.00001,
    "gpt-4": 0.00001,
    "Meta-Llama-3.1-405B-Instruct": 0.0,
}

MODEL_COST_PER_OUTPUT: dict[str, float] = {
    "gpt-3.5-turbo-0125": 0.0000015,
    "gpt-4-turbo-2024-04-09": 0.00003,
    "gpt-4o-2024-05-13": 0.000015,
    "gpt-4o-mini": 0.6 / 1_000_000,  # $0.60 per 1M tokens = $6e-7 per token
    "gpt-4o": 10.0 / 1_000_000,  # $10.00 per 1M tokens = $1e-5 per token
    "gpt-4-0613": 0.00003,
    "gpt-4": 0.00003,
    "Meta-Llama-3.1-405B-Instruct": 0.0,
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_cost = MODEL_COST_PER_INPUT.get(model, 0.0) * input_tokens
    output_cost = MODEL_COST_PER_OUTPUT.get(model, 0.0) * output_tokens
    return input_cost + output_cost


def get_model_pricing(model: str) -> tuple[float, float]:
    return (
        MODEL_COST_PER_INPUT.get(model, 0.0),
        MODEL_COST_PER_OUTPUT.get(model, 0.0),
    )

