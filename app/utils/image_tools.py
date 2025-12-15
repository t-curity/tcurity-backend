def generate_phase_a_problem():
    """
    실제 Phase A 문제 생성 로직 대신 서버 실행을 위한 더미 함수.
    """
    return {
        "image_base64": "base64_dummy_image",
        "target_path": [{"x": 10, "y": 20, "t": 0}, {"x": 20, "y": 30, "t": 10}],
        "cut_rectangle": [10, 5, 10, 50]
    }


# def to_base64(img):
#     """
#     placeholder 함수 — 이미지 base64 변환 대신 문자열 반환
#     """
#     return "base64_dummy"


# def apply_watermark_and_noise(img, order, fail_count):
#     """
#     Phase B 이미지 워터마크/노이즈 더미 처리 함수
#     """
#     return img
def load_random_grid_images(n):
    return {"images": [None] * n, "labels": [str(i) for i in range(n)]}

def apply_watermark_and_noise(img, order, fail_count):
    return img

def to_base64(img):
    return "dummy_base64"
