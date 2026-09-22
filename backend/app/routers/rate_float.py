from fastapi import APIRouter, HTTPException
from app.modules.rate_float import RateFloatError
from app.schemas.rate_float import FloatEventCreate, FloatEventUpdate
from app.services.mortgage_service import MortgageService

router = APIRouter()


@router.get("/loans/{loan_id}/rate-floats")
def list_float_events(loan_id: int):
    with MortgageService() as s:
        if not s.loan(loan_id):
            raise HTTPException(404)
        return {"items": s.list_float_events(loan_id)}


@router.post("/loans/{loan_id}/rate-floats", status_code=201)
def create_float_event(loan_id: int, body: FloatEventCreate):
    with MortgageService() as s:
        if not s.loan(loan_id):
            raise HTTPException(404)
        try:
            return s.create_float_event(loan_id, body.effective_period, body.new_annual_rate, body.note)
        except RateFloatError as e:
            raise HTTPException(422, str(e))


@router.put("/rate-floats/{event_id}")
def update_float_event(event_id: int, body: FloatEventUpdate):
    with MortgageService() as s:
        if not s.float_event(event_id):
            raise HTTPException(404)
        try:
            return s.update_float_event(event_id, body.effective_period, body.new_annual_rate, body.note)
        except RateFloatError as e:
            raise HTTPException(422, str(e))


@router.post("/rate-floats/{event_id}/disable")
def disable_float_event(event_id: int):
    with MortgageService() as s:
        if not s.float_event(event_id):
            raise HTTPException(404)
        try:
            return s.disable_float_event(event_id)
        except RateFloatError as e:
            raise HTTPException(422, str(e))
