# app/schemas/session.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.core.state_machine import SessionStatus


# -------------------------
# Phase A 스키마
# -------------------------

class TargetPoint(BaseModel):
    x: float
    y: float
    t: float  # timestamp or step index


class PhaseAData(BaseModel):
    target_path: List[TargetPoint] = Field(
        description="서버에 저장된 정답 궤적 좌표"
    )
    attempts: int = Field(
        description="Phase A 시도 횟수"
    )


# -------------------------
# Phase B 스키마
# -------------------------

class PhaseBData(BaseModel):
    correct_answer: List[str] = Field(
        description="정답 이미지 레이블 배열"
    )
    fail_count: int = Field(
        description="Phase B 실패 횟수 (난이도 조절 기준)"
    )
    issued_at: int = Field(
        description="문제 발급 시점 (ms)"
    )


# -------------------------
# /session/init 응답 스키마
# -------------------------

class SessionCreateResponse(BaseModel):
    status: str = Field(..., example="INIT")
    session_id: str = Field(
        ..., 
        example="a8f41c8d-773d-4cce-9bac-f8f8c42ca999"
    )
    expires_in: int = Field(..., example=600)


# -------------------------
# 전체 세션 디버그용 스키마
# -------------------------

class SessionInfo(BaseModel):
    """
    디버깅/테스트용 전체 세션 내부 구조
    ※ FE/고객사에는 절대 노출 금지
    """
    session_id: str
    client_id: str
    status: SessionStatus
    created_at: int
    expires_at: int

    phase_a: PhaseAData
    phase_b: PhaseBData
