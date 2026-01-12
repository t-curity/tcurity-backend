from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any


class PointData(BaseModel):
    """
    개별 포인트 스키마
    - x, y: 좌표 (0~2000 범위)
    - t: timestamp (필수, 밀리초)
    """
    x: float = Field(..., ge=0, le=2000)
    y: float = Field(..., ge=0, le=2000)
    t: int = Field(..., ge=0)  # timestamp 필수


class CaptchaSubmitRequest(BaseModel):
    """
    Phase A/B 공통 제출 스키마
    
    검증 규칙:
    - points: 최대 2000개, timestamp 단조 증가
    - user_answer: 최대 20개
    """
    behavior_pattern_data: Optional[Dict[str, Any]] = None
    user_answer: Optional[List[str]] = Field(None, max_length=20)
    points: Optional[List[Any]] = Field(None, max_length=2000)
    metadata: Optional[Dict[str, Any]] = None

    @field_validator('points')
    @classmethod
    def validate_points(cls, v):
        """points 검증: 개수 제한 + timestamp 단조 증가"""
        if v is None:
            return v
        
        if len(v) > 2000:
            raise ValueError('points 개수가 2000개를 초과했습니다.')
        
        # timestamp 단조 증가 검증
        prev_ts = None
        for i, point in enumerate(v):
            # dict 형태일 경우 t 값 추출
            if isinstance(point, dict):
                ts = point.get('t')
                if ts is None:
                    # t가 없으면 검증 스킵 (Phase B 등에서 다른 형식 사용 가능)
                    continue
                if not isinstance(ts, (int, float)):
                    raise ValueError(f'points[{i}].t는 숫자여야 합니다.')
                if prev_ts is not None and ts < prev_ts:
                    raise ValueError(f'points[{i}].t가 이전 값보다 작습니다. (timestamp 순서 오류)')
                prev_ts = ts
        
        return v

    @field_validator('user_answer')
    @classmethod
    def validate_user_answer(cls, v):
        """user_answer 검증: 최대 20개"""
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError('user_answer 개수가 20개를 초과했습니다.')
        return v
