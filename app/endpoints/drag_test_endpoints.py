# app/endpoints/drag_test_endpoints.py
"""
드래그 테스트 데이터 수집용 API
- GET  /api/drag-test/        : 테스트 페이지
- POST /api/drag-test/log     : 드래그 데이터 저장
- GET  /api/drag-test/data    : 저장된 데이터 조회
- GET  /api/drag-test/stats   : 통계 요약
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from pathlib import Path
import json
from datetime import datetime

router = APIRouter(prefix="/api/drag-test", tags=["drag-test"])

# 데이터 저장 경로
DATA_DIR = Path("./data/drag_test")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 테스트 페이지 경로
STATIC_DIR = Path(__file__).parent.parent / "static"


class DragTestLog(BaseModel):
    session_id: str
    test_number: int
    logged_at: str
    device_type: str
    user_agent: str
    screen_width: int
    screen_height: int
    guide_line: Dict[str, Any]
    start_point: Optional[Dict[str, float]]
    end_point: Optional[Dict[str, float]]
    progress: Optional[float] = None
    duration_ms: int
    point_count: int
    points: List[Dict[str, Any]]


def _get_today_file() -> Path:
    """일자별 파일"""
    today = datetime.now().strftime("%Y-%m-%d")
    return DATA_DIR / f"drag_data_{today}.jsonl"


@router.get("/", response_class=HTMLResponse)
async def serve_test_page():
    """테스트 페이지 서빙"""
    test_page = STATIC_DIR / "drag_test.html"
    if test_page.exists():
        return FileResponse(test_page, media_type="text/html")
    return HTMLResponse(
        "<h1>drag_test.html not found</h1>"
        "<p>Put it in app/static/drag_test.html</p>",
        status_code=404
    )


@router.post("/log")
async def log_drag_test(data: DragTestLog):
    """드래그 테스트 데이터 저장"""
    try:
        with open(_get_today_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(data.model_dump(), ensure_ascii=False) + "\n")
        
        return {"success": True, "message": "Data logged"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/data")
async def get_drag_test_data(date: Optional[str] = None):
    """
    저장된 데이터 조회
    - date: YYYY-MM-DD 형식 (선택, 없으면 전체)
    """
    records = []
    
    if date:
        # 특정 날짜 데이터
        file = DATA_DIR / f"drag_data_{date}.jsonl"
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
    else:
        # 전체 데이터
        for file in sorted(DATA_DIR.glob("drag_data_*.jsonl")):
            with open(file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
    
    return {
        "count": len(records),
        "data": records
    }


@router.get("/stats")
async def get_drag_test_stats():
    """
    통계 요약
    - 디바이스별 통과율
    - 시작/끝 좌표 평균
    """
    records = []
    for file in sorted(DATA_DIR.glob("drag_data_*.jsonl")):
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    
    if not records:
        return {"message": "No data yet", "total": None, "pc": None, "mobile": None}
    
    # 디바이스별 분류
    pc_records = [r for r in records if r.get("device_type") == "pc"]
    mobile_records = [r for r in records if r.get("device_type") == "mobile"]
    
    def calc_stats(recs):
        if not recs:
            return None
        
        pass_count = sum(1 for r in recs if r.get("result") == "pass")
        start_ys = [r["start_point"]["y"] for r in recs if r.get("start_point")]
        end_ys = [r["end_point"]["y"] for r in recs if r.get("end_point")]
        durations = [r["duration_ms"] for r in recs if r.get("duration_ms")]
        
        return {
            "count": len(recs),
            "pass_count": pass_count,
            "pass_rate": round(pass_count / len(recs) * 100, 1),
            "start_y": {
                "avg": round(sum(start_ys) / len(start_ys), 4) if start_ys else None,
                "min": round(min(start_ys), 4) if start_ys else None,
                "max": round(max(start_ys), 4) if start_ys else None,
            },
            "end_y": {
                "avg": round(sum(end_ys) / len(end_ys), 4) if end_ys else None,
                "min": round(min(end_ys), 4) if end_ys else None,
                "max": round(max(end_ys), 4) if end_ys else None,
            },
            "duration_ms": {
                "avg": round(sum(durations) / len(durations), 1) if durations else None,
                "min": min(durations) if durations else None,
                "max": max(durations) if durations else None,
            },
        }
    
    return {
        "total": calc_stats(records),
        "pc": calc_stats(pc_records),
        "mobile": calc_stats(mobile_records),
    }


@router.delete("/data")
async def clear_drag_test_data():
    """데이터 초기화 (개발용)"""
    count = 0
    for file in DATA_DIR.glob("drag_data_*.jsonl"):
        file.unlink()
        count += 1
    
    return {"success": True, "deleted_files": count}