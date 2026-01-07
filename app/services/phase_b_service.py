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
    fixed_numbers: List[int],
    difficulty: str = "NORMAL"
) -> Dict[str, Any]:
    """
    AI 서버에서 받은 문제 데이터를 FE용 payload로 변환
    
    Args:
        fail_count: 실패 횟수
        problem_data: AI 서버 응답
        fixed_numbers: 각 이미지에 할당할 숫자 리스트 [1, 2, 3, 4, 5, 6, 7, 8, 9]
        difficulty: 난이도 ('NORMAL', 'MEDIUM', 'HIGH')
    
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
        
        # 숫자 워터마크 + 난이도별 노이즈 적용
        marked = apply_watermark_and_noise(img, assigned_number, fail_count, difficulty)
        
        processed_grid.append({
            "image_id": img_info["image_id"],
            "image": to_base64(marked),  # FE 타입: "image"
        })
    
    return {
        "question": problem_data["question"],
        "grid": processed_grid,
        "phase": "2/2",  # FE 타입: "phase"
        "time_limit": 300,  # 5분 (Phase A와 동일)
    }




def generate_phase_b_internal(
    problem_data: Dict[str, Any],
    fixed_numbers: List[int]
) -> Dict[str, Any]:
    """
    서버 세션에 저장할 내부 정보 생성
    
    Args:
        problem_data: AI 서버 응답 (answer_uuids 포함)
        fixed_numbers: 각 이미지에 할당된 숫자 리스트 [1, 2, 3, 4, 5, 6, 7, 8, 9]
    
    Returns:
        {
            "correct_uuids": ["uuid-3", "uuid-5", "uuid-7", "uuid-9"],  # 숫자 순서대로 정렬됨
            "issued_at": 1234567890
        }
    """
    # AI 서버가 반환한 정답 UUID 목록 (순서 무작위)
    answer_uuids_set = set(problem_data.get("answer_uuids", []))
    
    if not answer_uuids_set:
        raise RuntimeError("AI 서버 응답에 answer_uuids가 없습니다")
    
    # 이미지의 image_id와 할당된 숫자 매핑
    # images 리스트 순서 = fixed_numbers 순서
    uuid_to_number = {}
    for idx, img_info in enumerate(problem_data.get("images", [])):
        image_id = img_info.get("image_id")
        assigned_number = fixed_numbers[idx]
        uuid_to_number[image_id] = assigned_number
    
    # 정답 UUID들을 숫자 순서대로 정렬
    # 사용자는 숫자가 작은 순서대로 드래그해야 함
    correct_uuids = sorted(
        [uuid for uuid in answer_uuids_set if uuid in uuid_to_number],
        key=lambda uuid: uuid_to_number[uuid]
    )
    
    print(f"[DEBUG] 정답 UUID 정렬: {[(uuid, uuid_to_number.get(uuid)) for uuid in correct_uuids]}")
    
    return {
        "correct_uuids": correct_uuids,
        "issued_at": int(time() * 1000)
    }



def generate_phase_b_both(fail_count: int, difficulty: str = "NORMAL") -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Phase B 문제를 AI 서버에서 생성하고,
    - FE payload
    - Internal payload
    두 값을 한 번에 반환
    
    Args:
        fail_count: 현재 실패 횟수
        difficulty: 난이도 ('NORMAL', 'MEDIUM', 'HIGH')
    
    Returns:
        (fe_payload, internal_payload)
    """
    # 1) AI 서버에서 문제 생성
    problem_data = generate_phase_b_problem_from_ai()
    
    # 2) 고정된 숫자 배치 (1~9 순서대로)
    # 3x3 그리드: [1,2,3 / 4,5,6 / 7,8,9]
    fixed_numbers = list(range(1, 10))  # [1, 2, 3, 4, 5, 6, 7, 8, 9]
    
    # 3) FE payload 생성 (난이도 적용)
    print(f"[DEBUG] Phase B 문제 생성 - fail_count: {fail_count}, difficulty: {difficulty}")
    fe_payload = generate_phase_b_payload(
        fail_count=fail_count,
        problem_data=problem_data,
        fixed_numbers=fixed_numbers,
        difficulty=difficulty
    )
    
    # 4) Internal payload 생성
    internal_payload = generate_phase_b_internal(
        problem_data=problem_data,
        fixed_numbers=fixed_numbers
    )
    
    # ========== 테스트용 콘솔 출력 ==========
    target_class = problem_data.get("target_class", "unknown")
    correct_uuids = internal_payload["correct_uuids"]
    print(f"\n{'='*50}")
    print(f"[PHASE B 문제 정보]")
    print(f"  - 타겟 클래스: {target_class}")
    print(f"  - 정답 개수: {len(correct_uuids)}개")
    print(f"  - 정답 순서: 숫자 작은 순으로 드래그")
    print(f"  - 난이도: {difficulty}")
    print(f"{'='*50}\n")
    
    return fe_payload, internal_payload

