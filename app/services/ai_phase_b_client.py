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


def filter_and_normalize_points_phase_b(
    points: List[Any],
) -> List[Dict[str, Any]]:
    """
    Phase B 포인트 필터링 (정규화 좌표 0~1 그대로 유지)
    - Phase A와 동일한 구조
    - FE 배열 형식 지원: [x, y, t, eventType]
    - FE 객체 형식 지원: {"x": x, "y": y, "t": t, "eventType": eventType}
    - 좌표는 0~1 정규화 상태 그대로 전송
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
                event_type = p[3] if len(p) > 3 else "click"
                
            # 객체 형식: {"x": x, "y": y, "t": t, "eventType": eventType}
            elif isinstance(p, dict):
                if not all(k in p for k in ("x", "y", "t")):
                    continue
                
                x_norm = float(p["x"])
                y_norm = float(p["y"])
                t = float(p["t"])
                event_type = p.get("eventType", p.get("event_type", "click"))
            else:
                continue
            
            # 0~1 범위 검증
            if not (0 <= x_norm <= 1 and 0 <= y_norm <= 1):
                continue
            
            # 정규화 좌표 그대로 전송 (픽셀 변환 없음)
            filtered.append({
                "x": x_norm,
                "y": y_norm,
                "t": t,
                "eventType": event_type
            })
        except (ValueError, TypeError, IndexError):
            continue
    
    return filtered


def verify_phase_b_with_ai_sync(
    user_points: List[Any],
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    AI 서버에 Phase B 행동 패턴 데이터를 전송하여 사람/봇 판별
    
    Args:
        user_points: [[x, y, t, eventType], ...] 또는 [{"x": x, "y": y, "t": t}, ...]
                     x, y는 0~1 정규화 좌표
        metadata: {"screenWidth": int, "screenHeight": int, "deviceType": str}
        
    Returns:
        {"pass": bool, "label": str}
        - pass: True면 사람, False면 봇
        - label: "사람" 또는 "봇"
    
    Note:
        정답 검증은 백엔드에서 수행하므로, AI 서버는 행동 패턴만 검증
    """
    url = f"{AI_SERVER_URL}/phase-b/verify"
    
    # 메타데이터 기본값 설정
    if metadata is None:
        metadata = {}
    
    # 포인트 필터링 (정규화 좌표 그대로)
    filtered_points = filter_and_normalize_points_phase_b(user_points)
    
    print(f"[DEBUG] Phase B AI 호출 - 원본 포인트: {len(user_points)}개, 필터링 후: {len(filtered_points)}개")
    
    # 유효 포인트가 너무 적으면 즉시 통과 처리
    if len(filtered_points) < 2:  # Phase B는 클릭이므로 2개로 완화
        print(f"[DEBUG] 포인트 부족으로 AI 서버 호출 스킵 (최소 2개 필요)")
        return {
            "pass": True,
            "label": "사람",
            "reason": "insufficient_valid_points"
        }

    
    # GPU 서버로 정규화 좌표 전송
    payload = {
        "points": filtered_points,  # 정규화 좌표 (0~1)
        "metadata": {
            "deviceType": metadata.get("deviceType", "unknown"),
            "screenWidth": metadata.get("screenWidth"),
            "screenHeight": metadata.get("screenHeight"),
        }
    }
    
    print(f"[DEBUG] AI 서버 호출: {url}")
    print(f"[DEBUG] Payload: points={len(filtered_points)}개, metadata={metadata.get('deviceType')}")
    
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
            print(f"[DEBUG] AI 서버 응답: {result}")
            return result
            
    except urllib.error.URLError as e:
        # 연결 실패 시 통과 (AI 모델 준비 전)
        print(f"[DEBUG] AI 서버 연결 실패: {e}")
        return {
            "pass": True,
            "label": "사람",
            "reason": "ai_server_connection_failed"
        }
    except urllib.error.HTTPError as e:
        # HTTP 에러 시 통과
        print(f"[DEBUG] AI 서버 HTTP 에러: {e.code}")
        return {
            "pass": True,
            "label": "사람",
            "reason": f"ai_server_error_{e.code}"
        }
    except TimeoutError:
        # 타임아웃 시 통과
        print(f"[DEBUG] AI 서버 타임아웃")
        return {
            "pass": True,
            "label": "사람",
            "reason": "ai_server_timeout"
        }
    except Exception as e:
        # 기타 에러 시 통과
        print(f"[DEBUG] AI 서버 알 수 없는 에러: {e}")
        return {
            "pass": True,
            "label": "사람",
            "reason": "ai_server_unknown_error"
        }



# 별칭 (async 버전이 필요한 경우를 위해)
verify_phase_b_with_ai = verify_phase_b_with_ai_sync
