from pydantic import BaseModel, Field
from typing import List, Optional
#

class CaptchaSubmitRequest(BaseModel):
    """
    Phase A/B 공통 제출 스키마
    """
    behavior_pattern_data: Optional[List[List[float]]] = Field(
        default=None, 
        description="사용자의 드래그 행동 데이터 [[x, y, t], ...]"
    )
    user_answer: Optional[List[str]] = Field(
        default=None, 
        description="Phase B 정답 배열"
    )
