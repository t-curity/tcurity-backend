# app/services/phase_b_service.py

import random
from time import time
from typing import Dict, Any, List, Tuple
from PIL import Image

from app.services.ai_phase_b_client import generate_phase_b_problem_from_ai
from app.utils.image_tools import to_base64, apply_watermark_and_noise

PHASE_B_TIME_LIMIT = 30


def generate_phase_b_payload(
    fail_count: int,
    problem_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    AI 서버에서 받은 문제 데이터를 FE용 payload로 변환
    
    Args:
        fail_count: 실패 횟수
        problem_data: AI 서버 응답
            {
                "question": "Animals 이미지를 모두 고르시오",
                "target_class": "Animals",
                "images": [
                    {
                        "path": "/path/to/image.jpg",
                        "label": "Animals",
                        "is_target": True
                    },
                    ...
                ]
            }
    
    Returns:
        FE용 payload (absolute answer 제외)
    """
    processed_grid = []
    
    # 정답 순서 매핑 (워터마크용)
    target_images = [img for img in problem_data["images"] if img["is_target"]]
    
    for idx, img_info in enumerate(problem_data["images"]):
        # 이미지 파일 로드
        img_path = img_info["path"]
        try:
            img = Image.open(img_path)
        except Exception as e:
            raise RuntimeError(f"이미지 로드 실패: {img_path}, Error: {e}")
        
        # 워터마크 순서 결정 (정답이면 1~4, 오답이면 0)
        if img_info["is_target"]:
            order = next(
                i + 1 for i, t in enumerate(target_images) 
                if t["path"] == img_path
            )
        else:
            order = 0
        
        # 워터마크 및 노이즈 적용
        marked = apply_watermark_and_noise(img, order, fail_count)
        
        processed_grid.append({
            "slot_index": idx,
            "label": img_info["label"],
            "image_base64": to_base64(marked)
        })
    
    return {
        "type": "PHASE_B",
        "grid": processed_grid,
        "time_limit": PHASE_B_TIME_LIMIT,
        "question": problem_data["question"]
    }


def generate_phase_b_internal(problem_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    서버 세션에 저장할 내부 정보 생성
    
    Args:
        problem_data: AI 서버 응답
    
    Returns:
        {
            "correct_answer": ["0", "3", "5", "7"],  # 정답 이미지의 인덱스
            "issued_at": 1234567890
        }
    """
    # 정답 이미지의 인덱스를 문자열 리스트로 변환
    correct_indices = [
        str(idx) 
        for idx, img in enumerate(problem_data["images"]) 
        if img["is_target"]
    ]
    
    return {
        "correct_answer": correct_indices,
        "issued_at": int(time() * 1000)
    }


def generate_phase_b_both(fail_count: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Phase B 문제를 AI 서버에서 생성하고,
    - FE payload
    - Internal payload
    두 값을 한 번에 반환
    
    Args:
        fail_count: 현재 실패 횟수
    
    Returns:
        (fe_payload, internal_payload)
    """
    # 1) AI 서버에서 문제 생성
    problem_data = generate_phase_b_problem_from_ai()
    
    # 디버깅 로그
    correct_indices = [
        str(idx) 
        for idx, img in enumerate(problem_data["images"]) 
        if img["is_target"]
    ]
    print(f"[PHASE B] CORRECT ANSWER = {correct_indices}")
    print(f"[PHASE B] TARGET CLASS = {problem_data['target_class']}")
    
    # 2) FE payload 생성
    fe_payload = generate_phase_b_payload(
        fail_count=fail_count,
        problem_data=problem_data
    )
    
    # 3) Internal payload 생성
    internal_payload = generate_phase_b_internal(problem_data)
    
    return fe_payload, internal_payload

