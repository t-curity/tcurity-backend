# app/services/ai_phase_a_client.py
"""
Phase A AI 서버 호출 클라이언트
tcurity-ai 서버의 /phase-a/verify 엔드포인트를 호출
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List


# AI 서버 URL (환경변수에서 가져오거나 기본값 사용)
AI_SERVER_URL = os.getenv("AI_SERVER_URL", "http://10.0.83.48:9000")
# AI_SERVER_URL = "http://10.0.3.151:9000"


# 기준 해상도 (이미지 고정 크기 - fallback용)
W_REF = 1920
H_REF = 1080


def filter_and_restore_points(
    points: List[Any],
    screen_width: int,
    screen_height: int
) -> List[Dict[str, Any]]:
    """
    포인트 필터링 및 픽셀 복원
    - FE 배열 형식 지원: [x, y, t, eventType]
    - FE 객체 형식 지원: {"x": x, "y": y, "t": t, "eventType": eventType}
    - FE 좌표(0~1) × 화면 크기 = 픽셀 좌표
    """
    if not isinstance(points, list) or not points:
        return []
    
    filtered = []
    for p in points:
        try:
            # 배열 형식: [x, y, t, eventType]
            if isinstance(p, (list, tuple)):
                if len(p) < 3:  # 최소 x, y, t 필요
                    continue
                
                x_norm = float(p[0])
                y_norm = float(p[1])
                t = float(p[2])
                event_type = p[3] if len(p) > 3 else "move"
                
            # 객체 형식: {"x": x, "y": y, "t": t, "eventType": eventType}
            elif isinstance(p, dict):
                if not all(k in p for k in ("x", "y", "t")):
                    continue
                
                x_norm = float(p["x"])
                y_norm = float(p["y"])
                t = float(p["t"])
                event_type = p.get("eventType", "move")
            else:
                continue
            
            # 0~1 범위 검증
            if not (0 <= x_norm <= 1 and 0 <= y_norm <= 1):
                continue
            
            # 픽셀 좌표로 복원 (FE 좌표 × 화면 크기)
            filtered.append({
                "x": x_norm * screen_width,
                "y": y_norm * screen_height,
                "t": t,
                "eventType": event_type
            })
        except (ValueError, TypeError, IndexError):
            continue
    
    return filtered


def verify_phase_a_with_ai_sync(
    user_points: List[Dict[str, Any]],
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    AI 서버에 Phase A 드래그 데이터를 전송하여 사람/봇 판별
    
    Args:
        user_points: [{"x": float, "y": float, "t": float, "eventType": str}, ...]
        metadata: {"screenWidth": int, "screenHeight": int, "deviceType": str}
        
    Returns:
        {"pass": bool, "label": str}
    """
    url = f"{AI_SERVER_URL}/phase-a/verify"
    
    # 메타데이터 기본값 설정
    if metadata is None:
        metadata = {}
    
    screen_width = metadata.get("screenWidth", W_REF)
    screen_height = metadata.get("screenHeight", H_REF)
    
    # 포인트 필터링 및 픽셀 복원 (FE 좌표 × 화면 크기)
    filtered_points = filter_and_restore_points(
        user_points,
        screen_width,
        screen_height
    )
    
    # 유효 포인트가 너무 적으면 즉시 봇 처리
    if len(filtered_points) < 3:
        return {
            "pass": False,
            "label": "봇",
            "reason": "insufficient_valid_points"
        }
    
    # GPU 서버로 픽셀 좌표 전송 (GPU는 추론만)
    payload = {
        "points": filtered_points,  # 픽셀 좌표
        "metadata": {
            "deviceType": metadata.get("deviceType", "unknown")
        }
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
        # 연결 실패 시 봇으로 처리
        return {
            "pass": False,
            "label": "봇",
            "reason": "ai_server_connection_failed"
        }
    except urllib.error.HTTPError as e:
        # HTTP 에러 시 봇으로 처리
        return {
            "pass": False,
            "label": "봇",
            "reason": f"ai_server_error_{e.code}"
        }
    except TimeoutError:
        # 타임아웃 시 봇으로 처리
        return {
            "pass": False,
            "label": "봇",
            "reason": "ai_server_timeout"
        }
    except Exception as e:
        # 기타 에러 시 봇으로 처리
        return {
            "pass": False,
            "label": "봇",
            "reason": "ai_server_unknown_error"
        }


# 별칭 (async 버전이 필요한 경우를 위해)
verify_phase_a_with_ai = verify_phase_a_with_ai_sync
