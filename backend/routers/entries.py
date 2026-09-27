from datetime import date as date_type
from datetime import datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select, delete, Select
from sqlalchemy.orm import Session, joinedload

from config import settings
from database import DBSession
from models import Food, FoodEntry, MealType
from schemas import (
    CopyDayIn, 
    CopyDayOut, 
    DailySummaryOut,
    DayPoint,
    FoodEntryCreate,
    FoodEntryOut,
    FoodEntryUpdate,
    FoodEntrywithMacros,
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