from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CaptchaSubmitRequest(BaseModel):
    """
    Phase A/B 공통 제출 스키마
    """
    behavior_pattern_data: Optional[Dict[str, Any]] = None
    user_answer: Optional[List[str]] = None

    points: Optional[List[Any]] = None
    metadata: Optional[Dict[str, Any]] = None
