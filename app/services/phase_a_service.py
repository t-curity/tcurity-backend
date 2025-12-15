# app/services/phase_a_service.py

from typing import Dict, Any, List, Tuple
from app.utils.image_tools import generate_phase_a_problem

GUIDE_TEXT = "절취선을 따라 드래그하세요."
TIME_LIMIT = 300  # 5분


def generate_phase_a_payload() -> Dict[str, Any]:
    """
    Client(FE)에게 내려보낼 Phase A 문제 payload만 생성한다.
    - 절대 target_path 등 내부 검증 정보는 포함하지 않음.
    """
    fe_payload, _ = generate_phase_a_both()
    return fe_payload


def generate_phase_a_internal() -> Dict[str, Any]:
    """
    서버가 세션에 저장해야 하는 Phase A 내부 정보만 반환한다.
    - target_path 등 검증에 필요한 데이터만 포함.
    """
    _, internal_payload = generate_phase_a_both()
    return internal_payload


def generate_phase_a_both() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    단일 문제 생성 함수.
    FE payload + Internal payload를 한 번에 생성하여 반환한다.

    반환:
        fe_payload: FE에게 내려보낼 UI/문제 데이터
        internal_payload: 서버에만 저장할 정답 경로/메타데이터
    """
    problem = generate_phase_a_problem()

    # ---------------------------
    # FE(클라이언트) 전달용 데이터
    # ---------------------------
    fe_payload = {
        "phase": "1/2",
        "image": problem["image_base64"],
        "cut_rectangle": problem["cut_rectangle"],
        "guide_text": GUIDE_TEXT,
        "time_limit": TIME_LIMIT,
    }

    # ---------------------------
    # Internal(서버) 저장 데이터
    # ---------------------------
    internal_payload = {
        "target_path": problem["target_path"]
    }

    return fe_payload, internal_payload
