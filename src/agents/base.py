from __future__ import annotations
from typing import Protocol, Dict
from src.core.config import AppConfig

class Agent(Protocol):
    name: str
    def call(self, payload: Dict, *, cfg: AppConfig) -> Dict: ...
