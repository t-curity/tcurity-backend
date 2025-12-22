# app/services/ai_phase_b_client.py
"""
Phase B AI 서버 호출 클라이언트
- /phase-b/generate: 문제 생성
- /phase-b/verify: 답안 검증
"""

import os
import json
import random
import urllib.request
import urllib.error
from typing import Dict, Any, List


# AI 서버 URL (Phase A와 동일한 서버 사용)
AI_SERVER_URL = os.getenv("AI_SERVER_URL", "http://10.0.83.48:9000")


# 로컬 fallback용 규칙 (AI 서버 참고)
PHASE_B_RULES: Dict[str, List[str]] = {
    "Animals": ["Building", "Devices", "Fashion", "Vehicle"],
    "Birds": ["Building", "Devices", "Fashion", "Food"],
    "Building": ["Nature", "Devices", "Fashion", "Sports"],
    "Devices": ["Instrument", "Building", "Fashion", "Food"],
    "Fashion": ["Devices", "Instrument", "Building", "Food"],
    "Food": ["Instrument", "Devices", "Fashion", "Nature"],
    "Instrument": ["Building", "Devices", "Fashion", "Nature"],
    "Nature": ["Building", "Devices", "Instrument", "Vehicle"],
    "Sports": ["Fashion", "Building", "Devices", "Food"],
    "Vehicle": ["Building", "Nature", "Devices", "Instrument"],
}


def generate_phase_b_problem_from_ai(target_class: str = None) -> Dict[str, Any]:
    """
    AI 서버에서 Phase B 문제를 생성
    
    Args:
        target_class: 정답 클래스 (None이면 랜덤 선택)
        
    Returns:
        {
            "question": "Animals 이미지를 모두 고르시오",
            "target_class": "Animals",
            "images": [
                {
                    "path": "...",
                    "label": "Animals",
                    "is_target": True
                },
                ...
            ]
        }
    """
    # target_class가 없으면 랜덤 선택
    if target_class is None:
        target_class = random.choice(list(PHASE_B_RULES.keys()))
    
    url = f"{AI_SERVER_URL}/phase-b/generate"
    
    payload = {
        "target_class": target_class
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result
            
    except Exception as e:
        # AI 서버 실패 시 에러 발생 (fallback 없음)
        raise RuntimeError(
            f"AI 서버 문제 생성 실패: {str(e)}\n"
            f"AI_SERVER_URL={AI_SERVER_URL}"
        )


def verify_phase_b_with_ai_sync(
    user_answer: List[str],
    correct_answer: List[str],
    behavior_data: Any = None
) -> Dict[str, Any]:
    """
    AI 서버에 Phase B 데이터를 전송하여 검증
    
    Args:
        user_answer: 사용자가 선택한 답 (예: ["0", "3", "7"])
        correct_answer: 정답 (예: ["0", "3", "7"])
        behavior_data: 선택적 행동 패턴 데이터
        
    Returns:
        {"pass": bool, "label": str}
        - pass: True면 정답, False면 오답/봇
        - label: "정답" 또는 "오답" 또는 "봇"
    """
    url = f"{AI_SERVER_URL}/phase-b/verify"
    
    payload = {
        "user_answer": user_answer,
        "correct_answer": correct_answer,
        "behavior_data": behavior_data
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result
            
    except urllib.error.URLError as e:
        # 연결 실패 시 기본 정답 체크로 fallback
        return {
            "pass": user_answer == correct_answer,
            "label": "정답" if user_answer == correct_answer else "오답",
            "reason": "ai_server_connection_failed"
        }
    except urllib.error.HTTPError as e:
        # HTTP 에러 시 기본 정답 체크로 fallback
        return {
            "pass": user_answer == correct_answer,
            "label": "정답" if user_answer == correct_answer else "오답",
            "reason": f"ai_server_error_{e.code}"
        }
    except TimeoutError:
        # 타임아웃 시 기본 정답 체크로 fallback
        return {
            "pass": user_answer == correct_answer,
            "label": "정답" if user_answer == correct_answer else "오답",
            "reason": "ai_server_timeout"
        }
    except Exception as e:
        # 기타 에러 시 기본 정답 체크로 fallback
        return {
            "pass": user_answer == correct_answer,
            "label": "정답" if user_answer == correct_answer else "오답",
            "reason": "ai_server_unknown_error"
        }


# 별칭 (async 버전이 필요한 경우를 위해)
verify_phase_b_with_ai = verify_phase_b_with_ai_sync
