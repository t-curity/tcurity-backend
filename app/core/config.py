# app/core/config.py

# 서비스 정책 / 시간 / 임계값 / 전역 상수
SESSION_TTL_SECONDS = 15 * 60  # 15분

# # Phase A
# PHASE_A_TIME_LIMIT = 20          # FE 제한 시간
# PHASE_A_MAX_ATTEMPTS = 3         # 최대 재시도

# # Phase B
# PHASE_B_TIME_LIMIT = 30
# PHASE_B_MAX_FAIL_COUNT = 2

# # Behavior Model
# PHASE_A_ANOMALY_THRESHOLD = 0.5  # 정책으로 확정되면