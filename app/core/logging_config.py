# app/core/logging_config.py
"""
구조화된 로깅 설정

- JSON 포맷 로거
- 민감 데이터 마스킹 (session_id, IP)
- trace_id 지원
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Optional
from contextvars import ContextVar

# 요청별 trace_id 저장
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


# =====================================================
# 마스킹 함수
# =====================================================

def mask_session_id(session_id: Optional[str]) -> str:
    """session_id 앞 6자리만 표시"""
    if not session_id:
        return "***"
    return session_id[:6] + "..." if len(session_id) > 6 else session_id


def mask_ip(ip: Optional[str]) -> str:
    """IP 주소 /24 마스킹 (마지막 옥텟 숨김)"""
    if not ip:
        return "***"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.***"
    return "***"


# =====================================================
# JSON 포맷터
# =====================================================

class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # trace_id 추가
        trace_id = trace_id_var.get()
        if trace_id:
            log_data["trace_id"] = trace_id
        
        # extra 필드 추가 (마스킹된 데이터)
        if hasattr(record, "session_id"):
            log_data["session_id"] = mask_session_id(record.session_id)
        if hasattr(record, "client_ip"):
            log_data["client_ip"] = mask_ip(record.client_ip)
        if hasattr(record, "event"):
            log_data["event"] = record.event
        if hasattr(record, "result"):
            log_data["result"] = record.result
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        return json.dumps(log_data, ensure_ascii=False)


# =====================================================
# 로거 설정
# =====================================================

def setup_logging(level: str = "INFO") -> None:
    """애플리케이션 로깅 설정"""
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # JSON 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # uvicorn 로거 레벨 조정 (너무 verbose 방지)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def generate_trace_id() -> str:
    """새 trace_id 생성"""
    return str(uuid.uuid4())[:8]


def set_trace_id(trace_id: str) -> None:
    """현재 요청의 trace_id 설정"""
    trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """현재 요청의 trace_id 반환"""
    return trace_id_var.get()
