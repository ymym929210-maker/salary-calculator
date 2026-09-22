# -*- coding: utf-8 -*-
import csv
import os
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, session

import config

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.permanent_session_lifetime = timedelta(hours=config.SESSION_HOURS)


def load_salary_table():
    table = {}
    with open(os.path.join(os.path.dirname(__file__), "salary_table.csv"),
              encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            table[int(row["호봉"])] = int(row["기본급"])
    return table


SALARY_TABLE = load_salary_table()
STEPS = sorted(SALARY_TABLE.keys())

MONTH_NAMES = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월",
               "9월", "10월", "11월", "12월"]


def longevity_rate_for(years: float) -> float:
    if years < 1:
        years = 1
    rate = config.LONGEVITY_BASE_RATE + (years - 1) * config.LONGEVITY_STEP_RATE
    return min(rate, config.LONGEVITY_MAX_RATE)


def apply_raise(amount: float, rate: float) -> int:
    """금액에 인상률(%)을 적용하고 1,000원 단위로 반올림 (실제 관행)."""
    return round(amount * (1 + rate / 100) / 1000) * 1000


def base_2027_for_step(step: int) -> int:
    """2026년 9월 5.6% 인상이 이미 확정된, 2027년에 쓰는 고정 기본급."""
    step = min(max(step, min(STEPS)), max(STEPS))
    return apply_raise(SALARY_TABLE[step], config.THIS_YEAR_RAISE_RATE)


def hourly_wage_for(base: int) -> int:
    ratio = base / config.HOURLY_WAGE_REFERENCE_BASE
    return round(config.HOURLY_WAGE_REFERENCE_VALUE * ratio)


def step_for_month(start_step: int, promo_month: int, m: int) -> int:
    return start_step if m < promo_month else start_step + 1


def years_for_month(start_years: float, promo_month: int, m: int) -> float:
    # 호봉 오르는 달에 연차도 함께 한 살 올라간다고 가정 (정근수당 %에 반영)
    return start_years if m < promo_month else start_years + 1


def calc_month(base, hourly_wage, years, family_count, overtime_hours, month, step,
                retro_base=0, retro_bonus=0, retro_overtime=0):
    family = family_count * config.FAMILY_ALLOWANCE_PER_PERSON
    overtime = round(overtime_hours * hourly_wage * config.OVERTIME_MULTIPLIER)

    longevity = 0
    longevity_rate_pct = 0
    monthly_bonus = 0
    if month in config.MONTHLY_BONUS_EXCLUDED_MONTHS:
        rate = longevity_rate_for(years)
        longevity = round(base * rate)
        longevity_rate_pct = round(rate * 100)
    else:
        monthly_bonus = round(base * config.MONTHLY_BONUS_RATE)

    holiday_bonus = config.HOLIDAY_BONUS_AMOUNT if month in config.HOLIDAY_BONUS_MONTHS else 0
    summer_vacation = config.SUMMER_VACATION_AMOUNT if month == config.SUMMER_VACATION_MONTH else 0
    self_dev = config.SELF_DEV_AMOUNT if month == config.SELF_DEV_MONTH else 0

    # (이름, 금액, 비과세여부, 특별항목여부)
    items = [
        ("기본급", base, False, False),
        ("교통보조비", config.COMMUTE_ALLOWANCE, False, False),
        ("급량비", config.MEAL_ALLOWANCE, True, False),
        ("위험수당", config.HAZARD_ALLOWANCE, False, False),
        ("직무수당", config.DUTY_ALLOWANCE, False, False),
        ("체력단련비", config.FITNESS_ALLOWANCE, False, False),
        ("가족수당", family, False, False),
    ]
    if overtime:
        items.append(("시간외근무수당", overtime, False, False))
    if monthly_bonus:
        items.append(("상여금", monthly_bonus, False, False))
    if longevity:
        items.append((f"정근수당 ({longevity_rate_pct}%)", longevity, False, True))
    if holiday_bonus:
        items.append(("명절수당", holiday_bonus, False, True))
    if summer_vacation:
        items.append(("여름휴가비", summer_vacation, False, True))
    if self_dev:
        items.append(("자기계발비", self_dev, False, True))
    if retro_base:
        items.append((f"기본급소급 ({config.RETRO_START_MONTH}~{config.RETRO_END_MONTH}월)",
                       retro_base, False, True))
    if retro_bonus:
        items.append((f"상여소급 ({config.RETRO_START_MONTH}~{config.RETRO_END_MONTH}월)",
                       retro_bonus, False, True))
    if retro_overtime:
        items.append((f"시간외소급 ({config.RETRO_START_MONTH}~{config.RETRO_END_MONTH}월)",
                       retro_overtime, False, True))

    gross = sum(v for _, v, _, _ in items)
    return {
        "month_name": MONTH_NAMES[month - 1], "step": step,
        "grade_label": f"{config.GRADE_LABEL} {step}호봉",
        "lines": items, "gross": gross,
    }


def calc_2027(step, promo_month, years, family_count, overtime_hours_annual):
    """2027년: 5.6% 인상이 이미 확정된 고정 기본급으로 연중 계산."""
    monthly_overtime = overtime_hours_annual / 12
    months = []
    for m in range(1, 13):
        current_step = step_for_month(step, promo_month, m)
        current_years = years_for_month(years, promo_month, m)
        base = base_2027_for_step(current_step)
        hourly_wage = hourly_wage_for(base)
        months.append(calc_month(base, hourly_wage, current_years, family_count,
                                  monthly_overtime, m, current_step))
    year_total = sum(mo["gross"] for mo in months)
    return {"months": months, "year_total": year_total}


def calc_2028(step, promo_month, years, family_count, overtime_hours_annual, raise_rate):
    """2028년: 9월에 raise_rate% 인상 확정, 9월부터 적용 + 3~8월 소급
    (기본급소급/상여소급/시간외소급 3개 항목으로 분리, 실제 명세서 방식과 동일)."""
    monthly_overtime = overtime_hours_annual / 12

    retro_base = 0
    retro_bonus = 0
    retro_overtime = 0
    for rm in range(config.RETRO_START_MONTH, config.RETRO_END_MONTH + 1):
        rm_step = step_for_month(step, promo_month, rm)
        old_base = base_2027_for_step(rm_step)
        new_base = apply_raise(old_base, raise_rate)
        base_diff = new_base - old_base
        retro_base += base_diff
        if rm not in config.MONTHLY_BONUS_EXCLUDED_MONTHS:
            retro_bonus += round(base_diff * config.MONTHLY_BONUS_RATE)
        old_hourly = hourly_wage_for(old_base)
        new_hourly = hourly_wage_for(new_base)
        retro_overtime += round((new_hourly - old_hourly) * monthly_overtime * config.OVERTIME_MULTIPLIER)

    months = []
    for m in range(1, 13):
        current_step = step_for_month(step, promo_month, m)
        current_years = years_for_month(years, promo_month, m)
        base_2027 = base_2027_for_step(current_step)
        base = base_2027 if m < config.RAISE_EFFECTIVE_MONTH else apply_raise(base_2027, raise_rate)
        hourly_wage = hourly_wage_for(base)
        if m == config.RETRO_PAY_MONTH:
            months.append(calc_month(base, hourly_wage, current_years, family_count, monthly_overtime,
                                      m, current_step, retro_base, retro_bonus, retro_overtime))
        else:
            months.append(calc_month(base, hourly_wage, current_years, family_count, monthly_overtime,
                                      m, current_step))

    year_total = sum(mo["gross"] for mo in months)
    return {"months": months, "year_total": year_total}


def is_authed() -> bool:
    return bool(session.get("authed"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if code == config.ACCESS_CODE:
            session.permanent = True
            session["authed"] = True
            return redirect(url_for("index"))
        error = "접속번호가 올바르지 않습니다."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _num(form, name, default=0, cast=float):
    val = form.get(name, "")
    if val in (None, ""):
        return default
    try:
        return cast(val)
    except ValueError:
        return default


@app.route("/", methods=["GET", "POST"])
def index():
    if not is_authed():
        return redirect(url_for("login"))

    this_year = None
    next_year = None
    current_year_label = datetime.now().year + 1  # 2027
    next_year_label = current_year_label + 1        # 2028

    form_values = {
        "step": 12, "promo_month": 2, "years": 1, "family_count": 3,
        "overtime_hours_annual": 0, "next_raise_rate": 0,
    }

    if request.method == "POST":
        f = request.form
        form_values.update(
            step=_num(f, "step", 12, int),
            promo_month=_num(f, "promo_month", 2, int),
            years=_num(f, "years", 1, float),
            family_count=_num(f, "family_count", 0, int),
            overtime_hours_annual=_num(f, "overtime_hours_annual", 0, float),
            next_raise_rate=_num(f, "next_raise_rate", 0, float),
        )
        this_year = calc_2027(
            form_values["step"], form_values["promo_month"], form_values["years"],
            form_values["family_count"], form_values["overtime_hours_annual"],
        )
        next_year = calc_2028(
            form_values["step"] + 1, form_values["promo_month"], form_values["years"],
            form_values["family_count"], form_values["overtime_hours_annual"],
            form_values["next_raise_rate"],
        )

    return render_template(
        "index.html", steps=STEPS, form=form_values,
        this_year=this_year, next_year=next_year,
        current_year_label=current_year_label, next_year_label=next_year_label,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
