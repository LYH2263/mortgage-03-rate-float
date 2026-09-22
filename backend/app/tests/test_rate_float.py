import json
import sqlite3

import pytest

from app.engines.amortization import equal_payment_schedule
from app.modules import rate_float
from app.modules.rate_float import RateFloatError


def mem_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    rate_float.ensure_table(c)
    return c


def test_engine_matches_baseline_without_events():
    base = equal_payment_schedule(1_000_000, 3.5, 360)
    fl = rate_float.rate_float_schedule(1_000_000, 3.5, 360, [])
    assert fl["monthly_payment"] == base["monthly_payment"]
    assert fl["total_interest"] == base["total_interest"]
    assert fl["total_payment"] == base["total_payment"]
    assert fl["rows"] == base["rows"]
    assert fl["switches"] == []


def test_engine_switches_rate_from_effective_period():
    base = equal_payment_schedule(1_000_000, 3.5, 360)
    fl = rate_float.rate_float_schedule(1_000_000, 3.5, 360,
                                        [{"effective_period": 13, "new_annual_rate": 4.5}])
    assert fl["rows"][:12] == base["rows"][:12]
    sw = fl["switches"][0]
    assert sw["period"] == 13
    assert sw["rate_before"] == 3.5
    assert sw["rate_after"] == 4.5
    assert sw["payment_before"] == base["monthly_payment"]
    assert sw["payment_after"] > sw["payment_before"]
    assert fl["rows"][12]["payment"] == sw["payment_after"]
    assert fl["rows"][12]["interest"] == round(fl["rows"][11]["balance"] * 4.5 / 1200, 2)
    assert sw["interest_before"] + sw["interest_after"] == pytest.approx(fl["total_interest"], abs=0.02)
    assert fl["total_interest"] > base["total_interest"]


def test_engine_multiple_switches():
    fl = rate_float.rate_float_schedule(1_000_000, 3.5, 360, [
        {"effective_period": 13, "new_annual_rate": 4.5},
        {"effective_period": 121, "new_annual_rate": 3.0},
    ])
    assert [s["period"] for s in fl["switches"]] == [13, 121]
    assert fl["switches"][1]["rate_before"] == 4.5
    assert fl["switches"][1]["rate_after"] == 3.0
    assert fl["switches"][1]["payment_after"] < fl["switches"][1]["payment_before"]


def test_engine_rejects_bad_period_and_rate():
    with pytest.raises(ValueError):
        rate_float.rate_float_schedule(1000, 3, 12, [{"effective_period": 1, "new_annual_rate": 3}])
    with pytest.raises(ValueError):
        rate_float.rate_float_schedule(1000, 3, 12, [{"effective_period": 13, "new_annual_rate": 3}])
    with pytest.raises(ValueError):
        rate_float.rate_float_schedule(1000, 3, 12, [{"effective_period": 5, "new_annual_rate": -1}])
    with pytest.raises(ValueError):
        rate_float.rate_float_schedule(1000, 3, 12, [
            {"effective_period": 5, "new_annual_rate": 3},
            {"effective_period": 5, "new_annual_rate": 4},
        ])


def test_repo_crud_and_disable():
    c = mem_conn()
    ev = rate_float.create_event(c, 1, 360, 13, 4.5, "LPR调整")
    assert ev["enabled"] == 1
    assert ev["note"] == "LPR调整"
    assert [e["id"] for e in rate_float.list_events(c, 1)] == [ev["id"]]
    up = rate_float.update_event(c, ev["id"], 360, effective_period=25, new_annual_rate=4.2, note="改")
    assert up["effective_period"] == 25 and up["new_annual_rate"] == 4.2 and up["note"] == "改"
    dis = rate_float.disable_event(c, ev["id"])
    assert dis["enabled"] == 0
    assert rate_float.list_events(c, 1, enabled_only=True) == []
    assert len(rate_float.list_events(c, 1)) == 1


def test_repo_validates_period_bounds_and_rate():
    c = mem_conn()
    with pytest.raises(RateFloatError):
        rate_float.create_event(c, 1, 360, 1, 4.5)
    with pytest.raises(RateFloatError):
        rate_float.create_event(c, 1, 360, 361, 4.5)
    with pytest.raises(RateFloatError):
        rate_float.create_event(c, 1, 360, 13, -0.5)


def test_repo_conflict_names_both_ids():
    c = mem_conn()
    a = rate_float.create_event(c, 1, 360, 13, 4.5)
    with pytest.raises(RateFloatError) as ei:
        rate_float.create_event(c, 1, 360, 13, 4.9)
    assert f"#{a['id']}" in str(ei.value)
    b = rate_float.create_event(c, 1, 360, 25, 4.9)
    with pytest.raises(RateFloatError) as ei2:
        rate_float.update_event(c, b["id"], 360, effective_period=13)
    msg = str(ei2.value)
    assert f"#{a['id']}" in msg and f"#{b['id']}" in msg
    rate_float.disable_event(c, a["id"])
    ok = rate_float.create_event(c, 1, 360, 13, 4.1)
    assert ok["enabled"] == 1


def test_service_float_lifecycle(tmp_path, monkeypatch):
    import app.db as db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    from app import seed
    seed.init_db()
    from app.services.mortgage_service import MortgageService
    with MortgageService() as s:
        base = s.schedule(1_000_000, 3.5, 360, 1, persist=False)
        assert "rate_float" not in base
        ev = s.create_float_event(1, 13, 4.5, "加息")
        r1 = s.schedule(1_000_000, 3.5, 360, 1, persist=True)
        sw = r1["rate_float"]["switches"][0]
        assert sw["period"] == 13
        assert sw["rate_before"] == 3.5 and sw["rate_after"] == 4.5
        assert sw["payment_before"] == base["monthly_payment"]
        assert sw["payment_after"] > sw["payment_before"]
        assert r1["total_interest"] > base["total_interest"]
        rid = r1["run_id"]
        assert rid
        s.disable_float_event(ev["id"])
        r2 = s.schedule(1_000_000, 3.5, 360, 1, persist=False)
        assert "rate_float" not in r2
        assert r2["monthly_payment"] == base["monthly_payment"]
        assert r2["total_interest"] == base["total_interest"]
        saved = [h for h in s.history() if h["id"] == rid][0]
        saved_result = json.loads(saved["result_json"])
        saved_sw = saved_result["rate_float"]["switches"][0]
        assert saved_sw["period"] == 13
        assert saved_sw["payment_before"] == sw["payment_before"]
        assert saved_sw["payment_after"] == sw["payment_after"]


def test_service_persist_false_writes_nothing(tmp_path, monkeypatch):
    import app.db as db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    from app import seed
    seed.init_db()
    from app.services.mortgage_service import MortgageService
    with MortgageService() as s:
        before = len(s.history())
        s.create_float_event(1, 13, 4.5)
        r = s.schedule(1_000_000, 3.5, 360, 1, persist=False)
        assert r["run_id"] is None
        assert "rate_float" in r
        assert len(s.history()) == before
