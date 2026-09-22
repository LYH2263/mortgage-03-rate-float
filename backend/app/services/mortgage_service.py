from app.db import connect
from app.engines.amortization import equal_payment_schedule
from app.modules import rate_float
from app.modules.rate_float import RateFloatError
from app.repositories import loans, runs, settings

class MortgageService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_loans(self): return loans.list_all(self._c)
    def loan(self, lid): return loans.get(self._c, lid)
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50): return runs.list_recent(self._c, limit)
    def schedule(self, principal, annual_rate, months, loan_id, persist, preview_rows=12):
        events = rate_float.list_events(self._c, loan_id, enabled_only=True) if loan_id else []
        if events:
            full = rate_float.rate_float_schedule(principal, annual_rate, months, events)
        else:
            full = equal_payment_schedule(principal, annual_rate, months)
        out = {k: full[k] for k in ("monthly_payment", "total_interest", "total_payment")}
        out["preview"] = full["rows"][:preview_rows]
        out["row_count"] = len(full["rows"])
        if events:
            out["rate_float"] = {"applied": True, "switches": full["switches"]}
        rid = None
        if persist:
            rid = runs.insert(self._c, "schedule", {"principal": principal, "annual_rate": annual_rate, "months": months}, out, loan_id)
        return {"run_id": rid, **out}
    def list_float_events(self, loan_id): return rate_float.list_events(self._c, loan_id)
    def float_event(self, event_id): return rate_float.get_event(self._c, event_id)
    def create_float_event(self, loan_id, effective_period, new_annual_rate, note=""):
        loan = loans.get(self._c, loan_id)
        if not loan: raise RateFloatError(f"贷款 #{loan_id} 不存在")
        return rate_float.create_event(self._c, loan_id, loan["months"], effective_period, new_annual_rate, note)
    def update_float_event(self, event_id, effective_period=None, new_annual_rate=None, note=None):
        ev = rate_float.get_event(self._c, event_id)
        if not ev: raise RateFloatError(f"事件 #{event_id} 不存在")
        loan = loans.get(self._c, ev["loan_id"])
        return rate_float.update_event(self._c, event_id, loan["months"], effective_period, new_annual_rate, note)
    def disable_float_event(self, event_id): return rate_float.disable_event(self._c, event_id)
    def dashboard(self):
        items = loans.list_all(self._c)
        return {"loan_count": len(items), "clean": len([x for x in items if "种子" not in x["name"]]), "dirty": len([x for x in items if "种子" in x["name"]])}
