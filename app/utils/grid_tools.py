# app/utils/grid_tools.py

def load_random_grid_images(grid_size: int):
    """
    Phase B grid 문제 제공을 위한 더미 이미지 로더
    """
    # grid_size = 9 이면 9개의 이미지 + 라벨 생성
    dummy_images = [f"img_{i}" for i in range(grid_size)]
    dummy_labels = [f"label_{i}" for i in range(grid_size)]

    return {
        "images": dummy_images,
        "labels": dummy_labels
    }
