# core/state_machine.py

from enum import Enum
from typing import List

class SessionStatus(str, Enum):
    """API 명세와 Session Store에 사용되는 세션 상태."""
    INIT = "INIT"               # 세션 생성 직후
    PHASE_A = "PHASE_A"         # Phase A 문제 요청됨, 검증 대기/재시도 상태
    PHASE_B = "PHASE_B"         # Phase B 문제 요청됨, 검증 대기/재시도 상태
    COMPLETED = "COMPLETED"     # 모든 검증 완료 (최종 성공)
    
# --- 상태별 허용/차단 API 규칙 정의 (참고용) ---

# { 현재 상태: [허용되는 다음 상태 목록] }
STATE_TRANSITION_RULES = {
    SessionStatus.INIT: [SessionStatus.PHASE_A],
    SessionStatus.PHASE_A: [SessionStatus.PHASE_A, SessionStatus.PHASE_B], # 재시도 또는 성공
    SessionStatus.PHASE_B: [SessionStatus.PHASE_B, SessionStatus.COMPLETED], # 재시도 또는 성공
    SessionStatus.COMPLETED: [SessionStatus.COMPLETED] # 최종 상태, 변경 불가
}

def is_valid_transition(current_status: SessionStatus, next_status: SessionStatus) -> bool:
    """주어진 상태 전이가 유효한지 확인합니다."""
    allowed_next_states = STATE_TRANSITION_RULES.get(current_status, [])
    return next_status in allowed_next_states

# --- 상태별 허용 API 규칙 정의 (참고용) ---

# { API 엔드포인트: [호출이 허용되는 현재 상태 목록] }
API_ACCESS_RULES = {
    "/session/init": [None], # INIT 이전 상태
    "/captcha/request": [SessionStatus.INIT, SessionStatus.PHASE_A], # 문제 요청은 INIT 또는 재시도(PHASE_A)일 때만 가능
    "/captcha/submit": [SessionStatus.PHASE_A, SessionStatus.PHASE_B], # 제출은 해당 단계에서만 가능
    "/captcha/verify": [SessionStatus.COMPLETED] # S2S 최종 검증
}

def can_access_api(current_status: SessionStatus, api_path: str) -> bool:
    """현재 상태에서 특정 API 경로 접근이 허용되는지 확인합니다."""
    allowed_statuses = API_ACCESS_RULES.get(api_path)
    if allowed_statuses is None:
        return False # 정의되지 않은 API 경로
    
    # SessionStatus.INIT은 None 상태로 간주
    if current_status is None:
        current_status = SessionStatus.INIT
        
    return current_status in allowed_statuses