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


def generate_phase_b_problem_from_ai(target_class: str = None) -> Dict[str, Any]:
    """
    AI 서버에서 Phase B 문제를 생성
    
    Args:
        target_class: 정답 클래스 (None이면 AI 서버가 랜덤 선택)
        
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
    behavior_data: Any = None
) -> Dict[str, Any]:
    """
    AI 서버에 Phase B 행동 패턴 데이터를 전송하여 검증
    
    Args:
        behavior_data: 행동 패턴 데이터 (points, metadata 등)
        
    Returns:
        {"pass": bool, "label": str}
        - pass: True면 사람, False면 봇
        - label: "사람" 또는 "봇"
    
    Note:
        정답 검증은 백엔드에서 수행하므로, AI 서버는 행동 패턴만 검증
    """
    url = f"{AI_SERVER_URL}/phase-b/verify"
    
    payload = {
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
        # 연결 실패 시 통과 (순서는 이미 백엔드에서 검증됨)
        return {
            "pass": True,
            "label": "사람",
            "reason": "ai_server_connection_failed"
        }
    except urllib.error.HTTPError as e:
        # HTTP 에러 시 통과
        return {
            "pass": True,
            "label": "사람",
            "reason": f"ai_server_error_{e.code}"
        }
    except TimeoutError:
        # 타임아웃 시 통과
        return {
            "pass": True,
            "label": "사람",
            "reason": "ai_server_timeout"
        }
    except Exception as e:
        # 기타 에러 시 통과
        return {
            "pass": True,
            "label": "사람",
            "reason": "ai_server_unknown_error"
        }


# 별칭 (async 버전이 필요한 경우를 위해)
verify_phase_b_with_ai = verify_phase_b_with_ai_sync
