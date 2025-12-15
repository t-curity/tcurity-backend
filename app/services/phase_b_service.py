# app/services/phase_b_service.py

import random
from time import time
from typing import Dict, Any, List, Tuple

from app.utils.grid_tools import load_random_grid_images
from app.utils.image_tools import to_base64, apply_watermark_and_noise

PHASE_B_TIME_LIMIT = 30
PHASE_B_SIZE = 9
PHASE_B_ANSWER_COUNT = 4


def generate_phase_b_payload(fail_count: int, correct_answer: List[str], images: List[Any], labels: List[str]) -> Dict[str, Any]:
    """
    FE에게 내려보낼 Phase B 문제 payload만 구성.
    - absolute answer 절대 포함 X
    """

    processed_grid = []
    for idx, (img, label) in enumerate(zip(images, labels)):
        order = correct_answer.index(label) + 1 if label in correct_answer else 0
        marked = apply_watermark_and_noise(img, order, fail_count)

        processed_grid.append({
            "slot_index": idx,
            "label": label,
            "image_base64": to_base64(marked)
        })

    return {
        "type": "PHASE_B",
        "grid": processed_grid,
        "time_limit": PHASE_B_TIME_LIMIT
    }


def generate_phase_b_internal(correct_answer: List[str]) -> Dict[str, Any]:
    """
    서버 세션에 저장해야 하는 내부 정보만 포함.
    - 정답 배열
    - 문제 생성 시각
    - fail_count는 verify_service에서 증가시킴
    """

    return {
        "correct_answer": correct_answer,
        "issued_at": int(time() * 1000)
    }


def generate_phase_b_both(fail_count: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Phase B 문제를 생성하고,
    - FE payload
    - Internal payload
    두 값을 한 번에 반환한다.
    """

    grid_data = load_random_grid_images(PHASE_B_SIZE)
    images = grid_data["images"]
    labels = grid_data["labels"]

    if len(images) != PHASE_B_SIZE:
        raise ValueError("[ERROR] Phase B grid image count mismatch")

    # 1) 정답 4개 선택
    correct_answer = random.sample(labels, PHASE_B_ANSWER_COUNT)

    #디버깅 로그
    print("[PHASE B] CORRECT ANSWER =", correct_answer)
    
    # 2) FE payload 생성
    fe_payload = generate_phase_b_payload(
        fail_count=fail_count,
        correct_answer=correct_answer,
        images=images,
        labels=labels,
    )

    # 3) Internal payload 생성
    internal_payload = generate_phase_b_internal(correct_answer)

    return fe_payload, internal_payload
