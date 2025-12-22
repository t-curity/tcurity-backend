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
    
    # 정답 이미지 인덱스 찾기
    target_indices = [i for i, img in enumerate(problem_data["images"]) if img["is_target"]]
    
    # 정답 이미지에 할당된 숫자들 (순서대로 정렬)
    target_numbers = sorted([fixed_numbers[i] for i in target_indices])
    
    for idx, img_info in enumerate(problem_data["images"]):
        # 이미지 파일 로드
        img_path = img_info["path"]
        try:
            img = Image.open(img_path)
        except Exception as e:
            raise RuntimeError(f"이미지 로드 실패: {img_path}, Error: {e}")
        
        # 이 이미지에 할당된 숫자 (고정: 1~9)
        assigned_number = fixed_numbers[idx]
        
        # 숫자 워터마크 적용
        marked = apply_watermark_and_noise(img, assigned_number, fail_count)
        
        processed_grid.append({
            "slot_index": idx,
            "label": img_info["label"],
            "image_base64": to_base64(marked),
            "number": assigned_number  # FE에 숫자 정보 전달 (디버깅용, 선택적)
        })
    
    return {
        "type": "PHASE_B",
        "grid": processed_grid,
        "time_limit": PHASE_B_TIME_LIMIT,
        "question": problem_data["question"],
        "target_numbers": target_numbers  # 정답 숫자들 (순서대로)
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
            "number_to_index": {
                "1": "0",  # 숫자 1은 인덱스 0
                "2": "1",  # 숫자 2는 인덱스 1
                ...
            },
            "correct_numbers": [3, 5, 7, 9],  # 정답 숫자들 (순서대로)
            "issued_at": 1234567890
        }
    """
    # 숫자 → 인덱스 매핑
    number_to_index = {
        str(num): str(idx) 
        for idx, num in enumerate(fixed_numbers)
    }
    
    # 정답 이미지 인덱스 찾기
    target_indices = [i for i, img in enumerate(problem_data["images"]) if img["is_target"]]
    
    # 정답 숫자들 (순서대로 정렬)
    correct_numbers = sorted([fixed_numbers[i] for i in target_indices])
    
    return {
        "number_to_index": number_to_index,
        "correct_numbers": correct_numbers,
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

