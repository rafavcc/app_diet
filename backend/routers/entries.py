from datetime import date as date_type
from datetime import datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select, delete, Select
from sqlalchemy.orm import Session, joinedload

from config import settings
from database import DbSession
from models import Food, FoodEntry, MealType
from schemas import (
    CopyDayIn, 
    CopyDayOut,
    DailySummaryOut,
    DayPoint,
    FoodEntryCreate,
    FoodEntryOut,
    FoodEntryUpdate,
    FoodEntryWithMacros,
    MacroSummary,
    RangeSummaryOut
)

from services.macros import ZERO, add_macros, divide_macros, macros_for

router = APIRouter(prefix="/entries", tags=["entries"])

def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise

def _day_bounds(day: date_type) -> tuple[datetime, datetime]:
    """Half-open range so the index on FoodEntry.datetime is usable"""
    start = datetime.combine(day, time.min)
    return start, datetime.combine(day, time.max)

def _to_out(entry: FoodEntry) -> FoodEntryOut:
    return FoodEntryOut(
        id = entry.id, 
        meal_type= entry.meal_type or MealType.Other,
        grams = entry.grams,
        food_id = entry.food_id,
        datetime = entry.datetime,
        food_name = entry.food.name if entry.food else None
    )
def _with_macros(entry:FoodEntry) -> FoodEntryWithMacros:
    return FoodEntryWithMacros(
        **_to_out(entry).model_dump(),
        macros=MacroSummary(**macros_for(entry.food, entry.grams))
    )
def _entries_select() -> Select[tuple[FoodEntry]]:
    return select(FoodEntry).options(joinedload(FoodEntry.food)).order_by(FoodEntry.datetime.desc())

def _get_or_404(db:Session, entry_id:int) -> FoodEntry:
    entry = db.scalars(_entries_select().where(FoodEntry.id == entry_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="FoodEntry not found")
    return entry

@router.post("", response_model=FoodEntryOut, status_code=201)
def create_entry(db: DbSession, body: FoodEntryCreate):
    """Create a new food entry"""
    if db.get(Food, body.food_id) is None:
        raise HTTPException(status_code=404, detail="Food not found")

    data = body.model_dump()
    if data["datetime" ] is None:
        data["datetime"] = datetime.now()
    entry = FoodEntry(**data)
    db.add(entry)
    _commit(db)
    db.refresh(entry)
    return _to_out(entry)

@router.get("", response_model=list[FoodEntryOut] | list[FoodEntryWithMacros])
def list_entries(
    db: DbSession,
    date: date_type | None = None,
    meal_type: MealType | None = None,
    include_macros: bool = False,
    limit: Annotated[int, Query(gt=0, le=settings.max_page_size)] = settings.default_page_size,
    offset: Annotated[int, Query(ge=0)] = 0
):
    stmt = _entries_select()
    if date is not None:
        start, end = _day_bounds(date)
        stmt = stmt.where(FoodEntry.datetime.between(start, end))
    if meal_type is not None:
        stmt = stmt.where(FoodEntry.meal_type == meal_type)

    entries = db.scalars(stmt.order_by(FoodEntry.datetime).offset(offset).limit(limit)).all()
    if not include_macros:
        return [_to_out(entry) for entry in entries]
    return [_with_macros(entry) for entry in entries]

@router.get("/daily-summary", response_model=DailySummaryOut)
def daily_summary(db: DbSession, date: date_type):
    start, end = _day_bounds(date)
    entries = db.scalars(_entries_select().where(FoodEntry.datetime.between(start, end))).all()

    by_meal_type: dict[str, dict] = {}
    totals = dict(ZERO)
    for entry in entries:
        macros = macros_for(entry.food, entry.grams)
        key = (entry.meal_type or MealType.Other).value
        by_meal_type[key] = add_macros(by_meal_type.get(key, ZERO), macros)
        totals = add_macros(totals, macros)

    return DailySummaryOut(
        date=date,
        by_meal_type = {key:MacroSummary(**value) for key, value in by_meal_type.items()},
        totals=MacroSummary(**totals),
        entry_count = len(entries)
    )

@router.get("/range-summary", response_model=RangeSummaryOut)
def range_summary(db: DbSession, start: date_type, end: date_type):
    if start > end:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    span_days = (end - start).days + 1
    if span_days > settings.max_range_days:
        raise HTTPException(status_code=400, detail=f"Date range must be {settings.max_range_days} days or less")

    range_start, _ = _day_bounds(start)
    _, range_end = _day_bounds(end)
    entries = db.scalars(_entries_select().where(FoodEntry.datetime.between(range_start, range_end))).all()

    per_day: dict[date_type, dict] = {}
    counts: dict[date_type, int] = {}
    totals = dict(ZERO)

    for entry in entries:
        day = entry.datetime.date()
        macros = macros_for(entry.food, entry.grams)
        per_day[day] = add_macros(per_day.get(day, ZERO), macros)
        counts[day] = counts.get(day, 0) + 1
        totals = add_macros(totals, macros)

    days = []
    for offset in range(span_days):
        day = start + timedelta(days=offset)
        days.append(DayPoint(
            date=day,
            macros=MacroSummary(**per_day.get(day, ZERO)),
            entry_count=counts.get(day, 0)
        ))
    logget_days = len(per_day)

    return RangeSummaryOut(
        start=start,
        end=end,
        days=days,
        totals = MacroSummary(**totals),
        averages = MacroSummary(**divide_macros(totals, logget_days or 1)),
        logged_days=logget_days
    )

@router.post("/copy", response_model=CopyDayOut, status_code=201)
def copy_day(db: DbSession, body: CopyDayIn):
    source_start, source_end = _day_bounds(body.source_date)
    stmt = select(FoodEntry).where(FoodEntry.datetime.between(source_start, source_end))
    if body.meal_types:
        stmt = stmt.where(FoodEntry.meal_type.in_(body.meal_types))
    source_entries = db.scalars(stmt).all()

    if not source_entries:
        raise HTTPException(status_code=404, detail="Nothing logged on source date")
    replaced = 0
    if body.replace:
        target_start, target_end = _day_bounds(body.target_date)
        delete_stmt = delete(FoodEntry).where(FoodEntry.datetime.between(target_start, target_end))
        if body.meal_types:
            delete_stmt = delete_stmt.where(FoodEntry.meal_type._in(body.meal_types))
        replaced = db.execute(
            delete_stmt.execute_options(synchronize_session=False)
        ).rowcount

        for entry in source_entries:
            db.add(
                FoodEntry(
                    meal_type=entry.meal_type,
                    grams = entry.grams,
                    food_id = entry.food_id,
                    datetime=datetime.combine(body.target_date, entry.datetime.time())
                )
            )
        _commit(db)
        return CopyDayOut(
            copied=len(source_entries),
            replaced=replaced,
            source_date = body.source_date,
            target_date = body.target_date
        )

@router.get("/{entry_id}", response_model = FoodEntryOut)
def get_entry(db: DbSession, entry_id : int):
    return _to_out(_get_or_404(db, entry_id))

@router.get("/{entry_id}/macros", response_model = FoodEntryWithMacros)
def get_entry_macros(db: DbSession, entry_id : int):
    return _with_macros(_get_or_404(db, entry_id))

@router.put("/{entry_id}", response_model=FoodEntryOut)
def update_entry(db: DbSession, entry_id: int, body: FoodEntryUpdate):
    entry = _get_or_404(db, entry_id)

    changes = body.model_dump(exclude_unset=True)
    if "food_id" in changes and db.get(Food, changes["food_id"]) is None:
        raise HTTPException(status_code=404, datail="Food not found")
    
    for field, value in changes.items():
        setattr(entry, field, value)
    _commit(db)
    db.refresh(entry)
    return _to_out(entry)
                   
@router.delete("/{entry_id}", status_code = 204)
def delele_entry(db: DbSession, entry_id = int):
    entry = _get_or_404(db, entry_id)
    db.delete(entry)
    _commit(db)
    return Response(status_code=204)