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


def hourly_wage_for(base: int) -> int:
    # 12호봉 22,697원을 기준으로 기본급 비율만큼 같이 오른다고 추정
    ratio = base / config.HOURLY_WAGE_REFERENCE_BASE
    return round(config.HOURLY_WAGE_REFERENCE_VALUE * ratio)


def calc_month(base, hourly_wage, years, family_count, overtime_hours, month, step):
    family = family_count * config.FAMILY_ALLOWANCE_PER_PERSON
    overtime = round(overtime_hours * hourly_wage * config.OVERTIME_MULTIPLIER)

    longevity = 0
    monthly_bonus = 0
    if month in config.MONTHLY_BONUS_EXCLUDED_MONTHS:
        longevity = round(base * longevity_rate_for(years))
    else:
        monthly_bonus = round(base * config.MONTHLY_BONUS_RATE)

    holiday_bonus = config.HOLIDAY_BONUS_AMOUNT if month in config.HOLIDAY_BONUS_MONTHS else 0
    summer_vacation = config.SUMMER_VACATION_AMOUNT if month == config.SUMMER_VACATION_MONTH else 0
    self_dev = config.SELF_DEV_AMOUNT if month == config.SELF_DEV_MONTH else 0

    items = [
        ("기본급", base),
        ("교통보조비", config.COMMUTE_ALLOWANCE),
        ("급량비", config.MEAL_ALLOWANCE),
        ("위험수당", config.HAZARD_ALLOWANCE),
        ("직무수당", config.DUTY_ALLOWANCE),
        ("체력단련비", config.FITNESS_ALLOWANCE),
        ("가족수당", family),
    ]
    if overtime:
        items.append(("시간외근무수당", overtime))
    if monthly_bonus:
        items.append(("상여금", monthly_bonus))
    if longevity:
        items.append(("정근수당", longevity))
    if holiday_bonus:
        items.append(("명절수당", holiday_bonus))
    if summer_vacation:
        items.append(("여름휴가비", summer_vacation))
    if self_dev:
        items.append(("자기계발비", self_dev))

    gross = sum(v for _, v in items)
    return {"month_name": MONTH_NAMES[month - 1], "step": step, "lines": items, "gross": gross}


def base_for_step(step: int, raise_rate: float = 0) -> int:
    step = min(max(step, min(STEPS)), max(STEPS))
    return round(SALARY_TABLE[step] * (1 + raise_rate / 100))


def calc_year(step, promo_month, years, family_count, overtime_hours, raise_rate):
    months = []
    for m in range(1, 13):
        current_step = step if m < promo_month else step + 1
        current_years = years if m < promo_month else years + 1
        base = base_for_step(current_step, raise_rate)
        hourly_wage = hourly_wage_for(base)
        months.append(calc_month(base, hourly_wage, current_years, family_count, overtime_hours, m, current_step))
    year_total = sum(mo["gross"] for mo in months)
    hourly_wage_start = hourly_wage_for(base_for_step(step, raise_rate))
    hourly_wage_after = hourly_wage_for(base_for_step(step + 1, raise_rate))
    return {
        "months": months, "year_total": year_total,
        "hourly_wage_start": hourly_wage_start, "hourly_wage_after": hourly_wage_after,
    }


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
    combined_months = None
    current_year_label = datetime.now().year
    next_year_label = current_year_label + 1

    form_values = {
        "step": 12, "promo_month": 2, "years": 1, "family_count": 3,
        "overtime_hours": 0, "raise_rate": 5.6,
    }

    if request.method == "POST":
        f = request.form
        form_values.update(
            step=_num(f, "step", 12, int),
            promo_month=_num(f, "promo_month", 2, int),
            years=_num(f, "years", 1, float),
            family_count=_num(f, "family_count", 0, int),
            overtime_hours=_num(f, "overtime_hours", 0, float),
            raise_rate=_num(f, "raise_rate", 0, float),
        )
        this_year = calc_year(
            form_values["step"], form_values["promo_month"], form_values["years"],
            form_values["family_count"], form_values["overtime_hours"], 0,
        )
        next_year = calc_year(
            form_values["step"] + 1, form_values["promo_month"], form_values["years"],
            form_values["family_count"], form_values["overtime_hours"], form_values["raise_rate"],
        )
        combined_months = [
            {
                "month_name": ty["month_name"],
                "grade_label": f"{config.GRADE_LABEL} {ty['step']}호봉",
                "lines": ty["lines"],
                "gross": ty["gross"],
                "next_gross": ny["gross"],
                "next_grade_label": f"{config.GRADE_LABEL} {ny['step']}호봉",
            }
            for ty, ny in zip(this_year["months"], next_year["months"])
        ]

    return render_template(
        "index.html", steps=STEPS, form=form_values,
        this_year=this_year, next_year=next_year, combined_months=combined_months,
        current_year_label=current_year_label, next_year_label=next_year_label,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
