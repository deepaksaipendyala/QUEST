from __future__ import annotations
from typing import Dict
from src.agents.base import Agent
from src.core.config import AppConfig

def send(agent: Agent, message: Dict, cfg: AppConfig) -> Dict:
    return agent.call(message, cfg=cfg)
