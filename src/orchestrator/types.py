from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Budget:
    max_iterations: int
