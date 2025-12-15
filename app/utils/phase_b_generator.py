# app/utils/phase_b_generator.py

import random
from time import time
from typing import Dict, Any, List
from app.utils.image_tools import to_base64, apply_watermark_and_noise
from app.utils.grid_tools import load_random_grid_images


PHASE_B_TIME_LIMIT = 30
PHASE_B_GRID_SIZE = 9
PHASE_B_ANSWER_COUNT = 4


def generate_phase_b_grid(fail_count: int) -> Dict[str, Any]:

    # 랜덤 이미지 grid 로딩
    grid_data = load_random_grid_images(PHASE_B_GRID_SIZE)
    images = grid_data["images"]
    labels = grid_data["labels"]

    # 정답 4개 선택
    correct = random.sample(labels, PHASE_B_ANSWER_COUNT)

    # 이미지 처리
    processed = []
    for idx, (img, label) in enumerate(zip(images, labels)):
        order = correct.index(label) + 1 if label in correct else 0
        processed_img = apply_watermark_and_noise(img, order, fail_count)

        processed.append({
            "slot_index": idx,
            "label": label,
            "image_base64": to_base64(processed_img)
        })

    return {
        "processed_grid": processed,
        "correct_answer": correct
    }
