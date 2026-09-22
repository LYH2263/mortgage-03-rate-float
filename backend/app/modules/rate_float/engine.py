"""rate_float engine: equal-payment schedule with mid-loan annual-rate switches.

Each enabled event switches the annual rate from its effective period on:
periods before the switch keep the previous rate/payment, and from the
effective period the remaining monthly payment is recomputed from the
outstanding balance at the new rate over the remaining periods.
"""


def _payment(balance: float, monthly_rate: float, periods: int) -> float:
    if periods <= 0:
        return balance
    if monthly_rate == 0:
        return balance / periods
    f = (1 + monthly_rate) ** periods
    return balance * monthly_rate * f / (f - 1)


def rate_float_schedule(principal: float, annual_rate: float, months: int, events) -> dict:
    P = float(principal)
    n = int(months)
    if n <= 0:
        raise ValueError("months")
    by_period = {}
    for e in events:
        p = int(e["effective_period"])
        if p <= 1 or p > n:
            raise ValueError("effective_period")
        if float(e["new_annual_rate"]) < 0:
            raise ValueError("new_annual_rate")
        if p in by_period:
            raise ValueError("duplicate effective_period")
        by_period[p] = e

    rows = []
    switches = []
    bal = P
    rate = float(annual_rate)
    pay = _payment(bal, rate / 12.0 / 100.0, n)
    initial_pay = pay
    interest_sum = 0.0
    for i in range(1, n + 1):
        ev = by_period.get(i)
        if ev is not None:
            new_rate = float(ev["new_annual_rate"])
            new_pay = _payment(bal, new_rate / 12.0 / 100.0, n - i + 1)
            switches.append({
                "event_id": ev.get("id"),
                "period": i,
                "rate_before": round(rate, 6),
                "rate_after": round(new_rate, 6),
                "payment_before": round(pay, 2),
                "payment_after": round(new_pay, 2),
                "interest_before": round(interest_sum, 2),
            })
            rate = new_rate
            pay = new_pay
        interest = bal * rate / 12.0 / 100.0
        principal_part = pay - interest
        if i == n:
            principal_part = bal
            pay_i = principal_part + interest
        else:
            pay_i = pay
        bal = max(0.0, bal - principal_part)
        interest_sum += interest
        rows.append({
            "period": i,
            "payment": round(pay_i, 2),
            "principal": round(principal_part, 2),
            "interest": round(interest, 2),
            "balance": round(bal, 2),
        })
    for sw in switches:
        sw["interest_after"] = round(interest_sum - sw["interest_before"], 2)
    return {
        "monthly_payment": round(initial_pay, 2),
        "total_interest": round(interest_sum, 2),
        "total_payment": round(sum(x["payment"] for x in rows), 2),
        "rows": rows,
        "switches": switches,
    }
