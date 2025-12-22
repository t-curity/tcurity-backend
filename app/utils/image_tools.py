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


def apply_watermark_and_noise(img, number, fail_count):
    """
    Phase B 이미지에 숫자 워터마크 적용
    - number: 이미지에 표시할 숫자 (1~9)
    - fail_count: 실패 횟수 (현재 미사용, 추후 노이즈 추가 시 사용)
    """
    from PIL import ImageDraw, ImageFont
    
    # PIL Image로 변환 (없으면 그대로)
    if not hasattr(img, 'mode'):
        # numpy array → PIL Image
        if len(img.shape) == 3:
            img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        else:
            img = Image.fromarray(img)
    
    # RGB로 변환 (RGBA, L 등 다양한 모드 처리)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 숫자 워터마크 추가 (1~9 모두 표시)
    if number > 0:
        draw = ImageDraw.Draw(img)
        text = str(number)
        
        # 폰트 크기 계산 (이미지 크기에 비례)
        w, h = img.size
        font_size = max(20, int(min(w, h) / 10))
        
        try:
            # 시스템 기본 폰트 사용 시도
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            try:
                # macOS 폰트
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                # 기본 폰트 (크기 조절 불가)
                font = ImageFont.load_default()
        
        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        # 우측 상단에 배치
        padding = 10
        x = w - text_w - padding
        y = padding
        
        # 배경 (반투명 검은색 사각형)
        bg_padding = 5
        draw.rectangle(
            [x - bg_padding, y - bg_padding, x + text_w + bg_padding, y + text_h + bg_padding],
            fill=(0, 0, 0, 180)
        )
        
        # 텍스트 (흰색)
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
    
    # PIL Image → numpy array (cv2 형식)
    img_np = np.array(img)
    img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    return img_np


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
    cut_rectangle = [base_x - 10, y_min, 50, y_max - y_min]
    
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
    thickness=32,
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
    img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)  # BGRA 가능

    if img is None:
        raise FileNotFoundError(f"입력 이미지 없음: {img_path}")

    # 혹시 3채널로 들어오면 알파를 붙여줌(안전장치)
    if len(img.shape) == 3 and img.shape[2] == 3:
        alpha = np.full((img.shape[0], img.shape[1], 1), 255, dtype=img.dtype)
        img = np.concatenate([img, alpha], axis=2)  # BGR + A

    canvas = img.copy()

    color = (255, 255, 255, 255)  # 흰색 + 불투명

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
    color = (255, 255, 255, 255) # 흰색 + 불투명

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