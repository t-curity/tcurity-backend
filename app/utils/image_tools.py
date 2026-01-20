import numpy as np
import random
import json
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


# ==========================================================
# 공통 유틸리티 함수
# ==========================================================
def to_base64(img):
    """
    PIL Image 또는 numpy 이미지를 base64 문자열로 변환
    """
    if img is None:
        return ""
    
    # numpy array면 PIL Image로 변환
    if isinstance(img, np.ndarray):
        img = Image.fromarray(img)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def apply_adversarial_noise(img, difficulty: str, fail_count: int):
    """
    Adversarial-like Noise 적용
    
    Args:
        img: PIL Image 또는 numpy array
        difficulty: 'NORMAL', 'MEDIUM', 'HIGH'
        fail_count: 실패 횟수 (추가 노이즈 강도에 영향)
    
    Returns:
        노이즈가 적용된 PIL Image
    
    노이즈 종류:
        - 가우시안 노이즈 (Gaussian Noise)
        - 색상 왜곡 (Color Jitter)
        - 밝기/대비 변화 (Brightness/Contrast)
    """
    if difficulty == "NORMAL":
        # PIL Image로 변환 후 반환
        if isinstance(img, np.ndarray):
            return Image.fromarray(img)
        return img
    
    # PIL Image → numpy array
    if not isinstance(img, np.ndarray):
        img_np = np.array(img)
    else:
        img_np = img
    
    # 난이도별 노이즈 강도 설정
    if difficulty == "MEDIUM":
        base_noise_level = 10  # 약한 노이즈
        color_shift = 5
        brightness_range = 0.1
    else:  # HIGH
        base_noise_level = 25  # 강한 노이즈
        color_shift = 15
        brightness_range = 0.2
    
    # 실패 횟수에 따라 노이즈 강도 추가 (최대 2배)
    multiplier = 1.0 + (fail_count * 0.3)
    multiplier = min(multiplier, 2.0)
    
    noise_level = int(base_noise_level * multiplier)
    color_shift = int(color_shift * multiplier)
    
    img_float = img_np.astype(np.float32)
    
    # 1. 가우시안 노이즈 추가
    noise = np.random.normal(0, noise_level, img_float.shape).astype(np.float32)
    img_float = img_float + noise
    
    # 2. 색상 왜곡 (각 채널별 랜덤 shift)
    for c in range(min(3, img_float.shape[2] if len(img_float.shape) > 2 else 1)):
        shift = random.randint(-color_shift, color_shift)
        if len(img_float.shape) > 2:
            img_float[:, :, c] = img_float[:, :, c] + shift
        else:
            img_float = img_float + shift
    
    # 3. 밝기/대비 변화
    brightness = 1.0 + random.uniform(-brightness_range, brightness_range)
    img_float = img_float * brightness
    
    # 클리핑 (0-255 범위로 제한)
    img_float = np.clip(img_float, 0, 255)
    
    return Image.fromarray(img_float.astype(np.uint8))


def apply_watermark_and_noise(img, number, fail_count, difficulty: str = "NORMAL"):
    """
    Phase B 이미지에 숫자 워터마크 + Adversarial-like Noise 적용
    
    Args:
        img: PIL Image 또는 numpy array
        number: 이미지에 표시할 숫자 (1~9)
        fail_count: 실패 횟수 (노이즈 강도에 영향)
        difficulty: 난이도 ('NORMAL', 'MEDIUM', 'HIGH')
    """
    # PIL Image로 변환
    if isinstance(img, np.ndarray):
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
    
    # Adversarial-like Noise 적용
    img = apply_adversarial_noise(img, difficulty, fail_count)
    
    return img


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
    
    # 절취선 영역 정의 (중심 축 기준)
    CUT_WIDTH = 50  # 절취선 폭
    cut_rectangle = [
        base_x - CUT_WIDTH // 2,  # 중심에서 절반만큼 왼쪽
        y_min,
        CUT_WIDTH,
        y_max - y_min
    ]
    
    # 이미지 크기 (백분율 변환용)
    img_w, img_h = canvas.size

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
    - result_img (PIL Image)
    - metadata (dict)
    두 값을 메모리로만 반환함.
    파일 저장은 전혀 하지 않음.
    """

    # ------------------------
    # 이미지 로드
    # ------------------------
    img = Image.open(img_path)
    
    # RGBA로 변환 (알파 채널 보장)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    canvas = img.copy()
    draw = ImageDraw.Draw(canvas)

    w, h = img.size

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
    # 점선 그리기
    # ------------------------
    segment_length = int(dash_length * segment_ratio)
    color = (255, 255, 255, 255)  # 흰색 + 불투명

    for i in range(0, len(curve_points), dash_length):
        if (i // dash_length) % 2 == 0:
            start = curve_points[i]
            end_idx = min(i + segment_length, len(curve_points) - 1)
            end = curve_points[end_idx]

            x1, y1 = int(start[0]), int(start[1])
            x2, y2 = int(end[0]), int(end[1])
            half = thickness // 2

            draw.rectangle(
                [x1 - half, y1, x1 + half, y2],
                fill=color
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

    # 시각적 확인
    import matplotlib.pyplot as plt
    plt.imshow(img)
    plt.title("Generated Cutline (Preview Only)")
    plt.axis("off")
    plt.show()