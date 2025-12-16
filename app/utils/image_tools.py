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
    """
    if img is None:
        return img

    result = img.copy()

    if fail_count > 0:
        noise_intensity = min(fail_count * 5, 30)
        noise = np.random.randint(
            -noise_intensity, noise_intensity, result.shape, dtype=np.int16
        )
        result = np.clip(
            result.astype(np.int16) + noise, 0, 255
        ).astype(np.uint8)

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

    image_base64 = to_base64(canvas)

    curve_points = metadata["curve_points"]
    target_path = [
        {"x": pt[0], "y": pt[1], "t": i * 10}
        for i, pt in enumerate(curve_points)
    ]

    base_x = metadata["base_x"]
    y_min, y_max = metadata["ticket_y_range"]
    cut_rectangle = [base_x - 10, y_min, 20, y_max - y_min]

    return {
        "image_base64": image_base64,
        "target_path": target_path,
        "cut_rectangle": cut_rectangle
    }


# ==========================================================
# 1) Bézier 곡선 생성
# ==========================================================
def bezier_curve(P0, P1, P2, P3, num_points=250):
    t = np.linspace(0, 1, num_points).reshape(num_points, 1)

    P0 = P0.reshape(1, 2)
    P1 = P1.reshape(1, 2)
    P2 = P2.reshape(1, 2)
    P3 = P3.reshape(1, 2)

    curve = (
        (1 - t)**3 * P0
        + 3 * (1 - t)**2 * t * P1
        + 3 * (1 - t) * t**2 * P2
        + t**3 * P3
    )

    return curve.astype(int)


# ==========================================================
# 2) 절취선 생성 (메모리 리턴, 파일 저장 없음)
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
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"입력 이미지 없음: {img_path}")

    h, w = img.shape[:2]

    ticket_y_min = int(h * ticket_y_ratio[0])
    ticket_y_max = int(h * ticket_y_ratio[1])

    x_min = int(w * x_center_ratio[0])
    x_max = int(w * x_center_ratio[1])
    base_x = random.randint(x_min, x_max)

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

    curve_points = bezier_curve(P0, P1, P2, P3)

    canvas = img.copy()
    segment_length = int(dash_length * segment_ratio)
    color = (255, 255, 255)

    for i in range(0, len(curve_points), dash_length):
        if (i // dash_length) % 2 == 0:
            x, y = curve_points[i]
            half = thickness // 2
            cv2.rectangle(
                canvas,
                (x - half, y),
                (x + half, y + segment_length),
                color,
                -1
            )

    metadata = {
        "curve_points": curve_points.tolist(),
        "base_x": base_x,
        "ticket_y_range": [ticket_y_min, ticket_y_max]
    }

    return canvas, metadata


# ==========================================================
# 로컬 테스트용 실행부
# ==========================================================
if __name__ == "__main__":
    img, meta = generate_cutline("tcurity_ticket.png")

    with open("cutline_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)

    print("절취선 생성 완료")

    import matplotlib.pyplot as plt
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    plt.show()
