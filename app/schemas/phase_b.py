# app/schemas/phase_b.py

from pydantic import BaseModel
from typing import List, Optional

class PhaseBVerifyRequest(BaseModel):
    user_answer: List[str]
    behavior_pattern_data: Optional[List[List[float]]] = None


class PhaseBVerifyResponse(BaseModel):
    status: str
    problem: Optional[dict] = None
    message: Optional[str] = None
    error: Optional[str] = None
