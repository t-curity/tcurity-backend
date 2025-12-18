import cv2
import numpy as np
import random
import json
import base64


# ==========================================================
# 공통 유틸리티 함수
# ==========================================================
def to_base64(img):
    """
    numpy 이미지(BGR)를 base64 문자열로 변환
    """
    if img is None:
        return ""
    _, buffer = cv2.imencode('.png', img)
    return base64.b64encode(buffer).decode('utf-8')


def apply_watermark_and_noise(img, order, fail_count):
    """
    Phase B 이미지에 워터마크/노이즈 적용
    - order: 정답 순서 (0이면 정답 아님)
    - fail_count: 실패 횟수에 따라 노이즈 강도 조절 가능
    """
    if img is None:
        return img
    
    result = img.copy()
    
    # 실패 횟수에 따른 노이즈 추가 (선택적)
    if fail_count > 0:
        noise_intensity = min(fail_count * 5, 30)
        noise = np.random.randint(-noise_intensity, noise_intensity, result.shape, dtype=np.int16)
        result = np.clip(result.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return result


# ==========================================================
# Phase A 문제 생성
# ==========================================================
def generate_phase_a_problem():
    """
    Phase A 문제 생성 - 절취선 이미지를 생성하고 FE에 전달할 데이터 반환
    """
    img_path = "app/static/tcurity_ticket.png"  
    
    canvas, metadata = generate_cutline(img_path)
    
    _, buffer = cv2.imencode('.png', canvas)
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    
    curve_points = metadata["curve_points"]
    target_path = [
        {"x": pt[0], "y": pt[1], "t": i * 10}
        for i, pt in enumerate(curve_points)
    ]
    
    base_x = metadata["base_x"]
    y_min, y_max = metadata["ticket_y_range"]
    cut_rectangle = [base_x - 10, y_min, 20, y_max - y_min]
    
    # 이미지 크기 (백분율 변환용)
    img_h, img_w = canvas.shape[:2]
    
    return {
        "image_base64": image_base64,
        "target_path": target_path,
        "cut_rectangle": cut_rectangle,
        "image_width": img_w,
        "image_height": img_h
    }

# ==========================================================
# 1) Bézier 곡선 생성 함수
# ==========================================================
def bezier_curve(P0, P1, P2, P3, num_points=250):
    t = np.linspace(0, 1, num_points).reshape(num_points, 1)

    P0 = P0.reshape(1, 2)
    P1 = P1.reshape(1, 2)
    P2 = P2.reshape(1, 2)
    P3 = P3.reshape(1, 2)

    curve = (1 - t)**3 * P0 \
            + 3 * (1 - t)**2 * t * P1 \
            + 3 * (1 - t) * t**2 * P2 \
            + t**3 * P3

    return curve.astype(int)



# ==========================================================
# 2) 절취선 생성 (메모리 리턴 + 저장 없음)
# ==========================================================
def generate_cutline(
    img_path,
    x_center_ratio=(0.30, 0.55),
    x_jitter=2,
    ticket_y_ratio=(0.10, 0.89),
    dash_length=13,
    thickness=20,
    segment_ratio=1.3
):
    """
    절취선을 생성하고:
    - result_img (numpy image)
    - metadata (dict)
    두 값을 메모리로만 반환함.
    파일 저장은 전혀 하지 않음.
    """

    # ------------------------
    # 이미지 로드
    # ------------------------
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"입력 이미지 없음: {img_path}")

    h, w = img.shape[:2]

    # ------------------------
    # 티켓 y 범위
    # ------------------------
    ticket_y_min = int(h * ticket_y_ratio[0])
    ticket_y_max = int(h * ticket_y_ratio[1])

    # ------------------------
    # 랜덤 x 위치
    # ------------------------
    x_min = int(w * x_center_ratio[0])
    x_max = int(w * x_center_ratio[1])
    base_x = random.randint(x_min, x_max)

    # ------------------------
    # Bézier Control Points
    # ------------------------
    P0 = np.array([base_x, ticket_y_min])
    P3 = np.array([base_x, ticket_y_max])

    P1 = np.array([
        base_x + random.randint(-x_jitter, x_jitter),
        ticket_y_min + int((ticket_y_max - ticket_y_min) * 0.3)
    ])

    P2 = np.array([
        base_x + random.randint(-x_jitter, x_jitter),
        ticket_y_min + int((ticket_y_max - ticket_y_min) * 0.7)
    ])

    # 곡선 생성
    curve_points = bezier_curve(P0, P1, P2, P3)

    # ------------------------
    # 점선 그리기 (결과는 메모리에서만 유지)
    # ------------------------
    canvas = img.copy()
    segment_length = int(dash_length * segment_ratio)
    color = (255, 255, 255)

    for i in range(0, len(curve_points), dash_length):

        if (i // dash_length) % 2 == 0:
            start = tuple(curve_points[i])
            end_idx = min(i + segment_length, len(curve_points) - 1)
            end = tuple(curve_points[end_idx])

            x1, y1 = start
            x2, y2 = end
            half = thickness // 2

            cv2.rectangle(
                canvas,
                (x1 - half, y1),
                (x1 + half, y2),
                color,
                -1
            )

    # ------------------------
    # 메타데이터 구성
    # ------------------------
    metadata = {
        "curve_points": curve_points.tolist(),
        "base_x": base_x,
        "ticket_y_range": [ticket_y_min, ticket_y_max]
    }

    return canvas, metadata



# ==========================================================
# 3) 실행부 (원하면 주석 처리하면 됨)
# ==========================================================
if __name__ == "__main__":
    img, meta = generate_cutline("tcurity_ticket.png")

    # ✅ JSON 파일 저장
    with open("cutline_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)

    print("=== 절취선 생성 완료 ===")
    print("JSON 저장 완료: cutline_meta.json")

    # 시각적 확인 (저장은 아님)
    import matplotlib.pyplot as plt
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.title("Generated Cutline (Preview Only)")
    plt.axis("off")
    plt.show()