# app/services/logging_service.py
# 추후
# captcha 성공/실패 로그, 이상 행동 로그, 분석용 이벤트 로그

# def log_event(event_type: str, payload: dict):
# pass
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class LogLevel(str, Enum):
    INFO = "info" # 단순 기록
    WARNING = "warning" # 의심
    ERROR = "error" # 장애/위험


logger = logging.getLogger("captcha")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

# CAPTCHA 시스템에서 발생한 "이벤트 하나"를 공통 포맷으로 기록하기 위한 함수
def log_event(
    event_type: str, # 이벤트 ID, 이벤트 코드
    payload: Dict[str, Any], # 이 이벤트에만 해당되는 정보
    level: LogLevel = LogLevel.INFO, # 중요도
    *, # context는 반드시 키워드 인자로만 받겠다는 뜻
    context: Optional[Dict[str, Any]] = None # 모든 로그에 공통적으로 붙는 환경 정보
):
    # 이 이벤트 하나를 기계가 분석하기 좋은 JSON 구조로 만듦
    log_data = {
        "event": event_type, # 모든 로그의 1번 키, 분석/알림 기준점
        "timestamp": datetime.utcnow().isoformat(), # 이벤트 자체의 시간
        "service": "captcha-backend", # 여러 서비스 중 어디서 나온 로그인지
        **(context or {}), # context가 있으면 풀어서 추가, 없으면 빈 dict
        **payload, # 이벤트별 정보 추가
    }

    message = json.dumps(log_data, ensure_ascii=False)

    if level == LogLevel.WARNING:
        logger.warning(message)
    elif level == LogLevel.ERROR:
        logger.error(message)
    else:
        logger.info(message)
