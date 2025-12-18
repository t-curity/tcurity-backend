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
    # cut_rectangle을 guide_line 백분율로 변환
    cut_rect = problem["cut_rectangle"]  # [x, y, width, height]
    img_w = problem["image_width"]
    img_h = problem["image_height"]
    
    # 절취선 중앙 x 좌표 (백분율)
    center_x = (cut_rect[0] + cut_rect[2] / 2) / img_w
    # y 시작/끝 (백분율)
    y_start = cut_rect[1] / img_h
    y_end = (cut_rect[1] + cut_rect[3]) / img_h
    # 너비 (백분율)
    line_width = cut_rect[2] / img_w
    
    fe_payload = {
        "guide_line": {
            "start": [round(center_x, 4), round(y_start, 4)],
            "end": [round(center_x, 4), round(y_end, 4)],
            "width": round(line_width, 4),
        },
        "guide_text": GUIDE_TEXT,
        "image": problem["image_base64"],
        "phase": "1/2",
        "time_limit": TIME_LIMIT,
    }

    # ---------------------------
    # Internal(서버) 저장 데이터
    # ---------------------------
    internal_payload = {
        "target_path": problem["target_path"]
    }

    return fe_payload, internal_payload


# # ===========================
# # Phase A 검증 (AI 연동)
# # ===========================
# from app.services.ai_phase_a_client import verify_phase_a_with_ai


# def verify_phase_a_by_ai(
#     user_points: List[Dict[str, Any]],
# ) -> Dict[str, Any]:
#     """
#     Phase A 사용자 입력을 AI 서버에 위임하여 검증한다.

#     반환 예:
#     {
#         "success": True
#     }
#     or
#     {
#         "success": False,
#         "reason": "BOT_DETECTED"
#     }
#     """
#     ai_result = verify_phase_a_with_ai(user_points)

#     if not ai_result.get("pass"):
#         return {
#             "success": False,
#             "reason": "BOT_DETECTED"
#         }

#     return {
#         "success": True
#     }
