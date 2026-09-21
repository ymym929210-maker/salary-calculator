"""
salary_table.csv (8급 전용 호봉표)를 생성하는 스크립트.

확인된 값: 12호봉 2,211,000원 / 11->12호봉 상승분 59,000원 /
           12->13호봉 상승분 60,000원 / 13->14호봉 상승분 61,000원
위 패턴(호봉이 하나 오를 때마다 상승분이 1,000원씩 커짐)을 그대로 연장해서
1~30호봉 전체를 추정했습니다. 12~14호봉 구간은 실제 값이고,
그 외 구간은 같은 규칙으로 추정한 값이니 실제 호봉표와 다르면 salary_table.csv를
직접 수정하세요.
"""
import csv

ANCHOR_STEP = 12
ANCHOR_BASE = 2_211_000
MAX_STEP = 30


def inc_to(n: int) -> int:
    # n호봉으로 올라갈 때의 상승분 (11->12=59000, 12->13=60000, 13->14=61000 규칙)
    return 47_000 + n * 1000


base = {ANCHOR_STEP: ANCHOR_BASE}
for n in range(ANCHOR_STEP + 1, MAX_STEP + 1):
    base[n] = base[n - 1] + inc_to(n)
for n in range(ANCHOR_STEP - 1, 0, -1):
    base[n] = base[n + 1] - inc_to(n + 1)

with open("salary_table.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["호봉", "기본급"])
    for step in sorted(base):
        writer.writerow([step, base[step]])

print("salary_table.csv 생성 완료 (8급, 12~14호봉만 확인된 값)")
