# app/services/phase_b_service.py

import io
import base64
import random
from time import time
from typing import Dict, Any, List, Tuple
from PIL import Image

from app.services.ai_phase_b_client import generate_phase_b_problem_from_ai
from app.utils.image_tools import to_base64, apply_watermark_and_noise

PHASE_B_TIME_LIMIT = 30


def generate_phase_b_payload(
    fail_count: int,
    problem_data: Dict[str, Any],
    fixed_numbers: List[int]
) -> Dict[str, Any]:
    """
    AI 서버에서 받은 문제 데이터를 FE용 payload로 변환
    
    Args:
        fail_count: 실패 횟수
        problem_data: AI 서버 응답
        fixed_numbers: 각 이미지에 할당할 숫자 리스트 [1, 2, 3, 4, 5, 6, 7, 8, 9]
    
    Returns:
        FE용 payload (absolute answer 제외)
    """
    processed_grid = []
    
    for idx, img_info in enumerate(problem_data["images"]):
        # 이미지 Base64 디코딩
        img_base64 = img_info.get("image_base64")
        if not img_base64:
            raise RuntimeError(f"이미지 Base64 데이터 없음: index {idx}")
        
        try:
            # Base64 → PIL Image
            img_data = base64.b64decode(img_base64)
            img = Image.open(io.BytesIO(img_data))
        except Exception as e:
            raise RuntimeError(f"이미지 디코딩 실패: index {idx}, Error: {e}")
        
        # 이 이미지에 할당된 숫자 (고정: 1~9)
        assigned_number = fixed_numbers[idx]
        
        # 숫자 워터마크 적용
        marked = apply_watermark_and_noise(img, assigned_number, fail_count)
        
        processed_grid.append({
            "image_id": img_info["image_id"],  # AI 서버에서 받은 UUID
            "image_base64": to_base64(marked),
        })
    
    return {
        "type": "PHASE_B",
        "grid": processed_grid,
        "question": problem_data["question"],
    }


def generate_phase_b_internal(
    problem_data: Dict[str, Any],
    fixed_numbers: List[int]
) -> Dict[str, Any]:
    """
    서버 세션에 저장할 내부 정보 생성
    
    Args:
        problem_data: AI 서버 응답
        fixed_numbers: 각 이미지에 할당된 숫자 리스트 [1, 2, 3, 4, 5, 6, 7, 8, 9]
    
    Returns:
        {
            "number_to_index": {"1": "0", "2": "1", ...},
            "number_to_uuid": {"1": "uuid-1", "2": "uuid-2", ...},
            "correct_numbers": [3, 5, 7, 9],
            "correct_uuids": ["uuid-3", "uuid-5", "uuid-7", "uuid-9"],
            "issued_at": 1234567890
        }
    """
    # ============================================================
    # [주석] 순서 관련 데이터 - 추후 활성화 예정
    # ============================================================
    # # 숫자 → 인덱스 매핑
    # number_to_index = {
    #     str(num): str(idx) 
    #     for idx, num in enumerate(fixed_numbers)
    # }
    # 
    # # 숫자 → UUID 매핑
    # number_to_uuid = {
    #     str(fixed_numbers[idx]): problem_data["images"][idx]["image_id"]
    #     for idx in range(len(problem_data["images"]))
    # }
    # 
    # # 정답 이미지 인덱스 찾기
    # target_indices = [i for i, img in enumerate(problem_data["images"]) if img["is_target"]]
    # 
    # # 정답 숫자들 (순서대로 정렬)
    # correct_numbers = sorted([fixed_numbers[i] for i in target_indices])
    # 
    # # 정답 UUID들 (숫자 순서대로)
    # correct_uuids = [number_to_uuid[str(num)] for num in correct_numbers]
    # ============================================================
    
    # 정답 UUID만 추출 (순서 무관)
    correct_uuids = [
        img["image_id"] 
        for img in problem_data["images"] 
        if img["is_target"]
    ]
    
    return {
        # "number_to_index": number_to_index,
        # "number_to_uuid": number_to_uuid,
        # "correct_numbers": correct_numbers,
        "correct_uuids": correct_uuids,
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
    
    # 2) 고정된 숫자 배치 (1~9 순서대로)
    # 3x3 그리드: [1,2,3 / 4,5,6 / 7,8,9]
    fixed_numbers = list(range(1, 10))  # [1, 2, 3, 4, 5, 6, 7, 8, 9]
    
    # 3) FE payload 생성
    fe_payload = generate_phase_b_payload(
        fail_count=fail_count,
        problem_data=problem_data,
        fixed_numbers=fixed_numbers
    )
    
    # 4) Internal payload 생성
    internal_payload = generate_phase_b_internal(
        problem_data=problem_data,
        fixed_numbers=fixed_numbers
    )
    
    # 디버깅 로그
    print(f"[PHASE B] CORRECT NUMBERS = {internal_payload['correct_numbers']}")
    print(f"[PHASE B] TARGET CLASS = {problem_data['target_class']}")
    
    return fe_payload, internal_payload

