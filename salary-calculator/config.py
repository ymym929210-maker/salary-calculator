# -*- coding: utf-8 -*-
"""
접속번호, 고정수당, 공제 관련 설정값.
"""
import os

# ── 접속 비밀번호 ─────────────────────────────────────
ACCESS_CODE = os.environ.get("ACCESS_CODE", "123456")
SESSION_HOURS = 12

# ── 고정 수당 (월액, 원) ──────────────────────────────
FAMILY_ALLOWANCE_PER_PERSON = 15_000
COMMUTE_ALLOWANCE = 30_000
MEAL_ALLOWANCE = 200_000
HAZARD_ALLOWANCE = 30_000
DUTY_ALLOWANCE = 50_000
FITNESS_ALLOWANCE = 30_000

# ── 정근수당: 1년차 50%, 매년 +5%p, 11년차부터 100% 고정 ─
LONGEVITY_BASE_RATE = 0.50
LONGEVITY_STEP_RATE = 0.05
LONGEVITY_MAX_RATE = 1.00

# ── 매달 상여금 (기본급 대비 %, 4월·10월 제외) ─────────
MONTHLY_BONUS_RATE = 1.00
MONTHLY_BONUS_EXCLUDED_MONTHS = (4, 10)

# ── 월별 고정 지급액 ──────────────────────────────────
HOLIDAY_BONUS_MONTHS = (2, 9)
HOLIDAY_BONUS_AMOUNT = 500_000
SUMMER_VACATION_MONTH = 7
SUMMER_VACATION_AMOUNT = 600_000
SELF_DEV_MONTH = 12
SELF_DEV_AMOUNT = 100_000

# ── 시간외근무수당 ────────────────────────────────────
OVERTIME_MULTIPLIER = 1.5

# ── 공제: 식대공제 계산용 ─────────────────────────────
MEAL_DEDUCTION_PER_MEAL = 4_300   # 전월식수 x 4,300원

# ── 공제: 고정 금액 선택 항목 ─────────────────────────
UNION_FEE_AMOUNT = 30_000     # 노동조합비
PARKING_FEE_AMOUNT = 10_000   # 주차비공제

# ── 소득세 (근사치 — 정확한 값은 명세서 값을 신뢰하세요) ─
INCOME_TAX_BRACKETS = [
    (1_500_000, 0.00),
    (3_000_000, 0.03),
    (5_000_000, 0.06),
    (8_000_000, 0.10),
    (float("inf"), 0.15),
]
LOCAL_TAX_RATE = 0.10  # 지방소득세 = 소득세의 10% (실제 두 달 데이터로 확인됨)

# ── 통상시급: 12호봉 22,697원을 기준으로 기본급 비율에 맞춰 추정 ─
HOURLY_WAGE_REFERENCE_STEP = 12
HOURLY_WAGE_REFERENCE_BASE = 2_211_000
HOURLY_WAGE_REFERENCE_VALUE = 22_697

# ── 직급 표시용 ───────────────────────────────────────
GRADE_LABEL = "8급"

# ── 이번 해(2027) 인상 — 이미 확정된 값 ─────────────────
# 2026년 9월 5.6% 인상이 확정되어 2027년은 연중 이 인상률이
# 그대로 적용된 기본급을 쓴다 (더 이상 퍼센트 입력이 필요 없음).
THIS_YEAR_RAISE_RATE = 5.6

# ── 임금협상 소급 구조 (다음 해=2028 예상용) ────────────
# 다음 해 인상률은 9월에 확정되어, 9월 급여부터 인상된 기본급이 바로 적용됨.
# 3~8월은 이번 해(2027) 확정 기본급으로 매달 지급하고, 9월에 3~8월
# 차액(기본급+상여금+시간외수당 전부 포함, 6개월치)을 "소급인상분"으로 한 번에 지급.
RAISE_EFFECTIVE_MONTH = 9
RETRO_START_MONTH = 3
RETRO_END_MONTH = 8
RETRO_PAY_MONTH = 9
