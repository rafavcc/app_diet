from __future__ import annotations

import datetime as dt
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator, StringConstraints

from models import MealType
from services.macros import KCAL_PER_G_CARB, KCAL_PER_G_PROT, KCAL_PER_G_FATS

MAX_MACRO_SUM = 100.0

# Reusable field types: each validation rule is written once and shared by create/update schemas

FoodName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Macro_per_100g = Annotated[float, Field(ge=0, le=100, description="Macro value per 100g of food")]
Grams = Annotated[float, Field(ge=0, description="Weight in grams")]
PositiveId = Annotated[int, Field(gt=0, description="Positive integer ID")]

def validate_macro_sum(carb: float | None, prot : float | None, fats: float | None) -> None:
    total = (carb or 0) + (prot or 0) + (fats or 0)
    if total > MAX_MACRO_SUM:
        raise ValueError(f"Sum of macros must be less than or equal to {MAX_MACRO_SUM}.")


class FoodBase(BaseModel):
    name : FoodName
    carb_per_100g : Macro_per_100g = 0.0
    prot_per_100g : Macro_per_100g = 0.0
    fats_per_100g : Macro_per_100g = 0.0

class FoodCreate(FoodBase):
    is_favourite : bool = False

    @model_validator(mode="after")
    def check_macro_sum(self) -> Self:
        validate_macro_sum(self.carb_per_100g, self.prot_per_100g, self.fats_per_100g)
        return self

class FoodUpdate(FoodBase):
    name : FoodName | None = None
    carb_per_100g : Macro_per_100g | None = None
    prot_per_100g : Macro_per_100g | None = None
    fats_per_100g : Macro_per_100g | None = None
    is_favourite : bool | None = None

class FavouriteUpdate(BaseModel):
    is_favourite : bool

class FoodOut(FoodBase):
    id : int
    is_favourite : bool = False
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def calories_per_100g(self) -> float:
        return round(
                self.carb_per_100g * KCAL_PER_G_CARB +
                self.prot_per_100g * KCAL_PER_G_PROT +
                self.fats_per_100g * KCAL_PER_G_FATS, 2)


# ——————————————————————————————————————————
# Food entry schemas
# ——————————————————————————————————————————

class FoodEntryBase(BaseModel):
    meal_type : MealType = MealType.Other
    grams : Grams
    food_id : PositiveId

class FoodEntryCreate(FoodEntryBase):
    datetime : dt.datetime | None = None

class FoodEntryUpdate(BaseModel):
    meal_type : MealType | None = None
    grams : Grams | None = None
    food_id : PositiveId | None = None
    datetime : dt.datetime | None = None

class FoodEntryOut(FoodEntryBase):
    id : int
    datetime : dt.datetime
    food_name : str | None = None
    model_config = ConfigDict(from_attributes=True)

# ——————————————————————————————————————————
# Macro schemas
# ——————————————————————————————————————————

class MacroSummary(BaseModel):
    carb_g : float = Field(default=0.0, ge=0, description="Total grams of carbohydrates")
    prot_g : float = Field(default=0.0, ge=0, description="Total grams of protein")
    fats : float = Field(default=0.0, ge=0, description="Total grams of fats")
    total_calories : float = Field(default=0.0, ge=0, description="Total calories")

class FoodEntryWithMacros(FoodEntryOut):
    macros: MacroSummary

class DailySummaryOut(BaseModel):
    date : dt.date
    by_meal_type: dict[str, MacroSummary]
    totals : MacroSummary
    entry_count : int = 0

class DayPoint(BaseModel):
    date : dt.date
    macros: MacroSummary
    entry_count : int = 0

class RangeSummaryOut(BaseModel):
    start : dt.date
    end : dt.date
    days: list[DayPoint]
    totals : MacroSummary
    averages: MacroSummary
    logged_days : int = 0

class CopyDayIn(BaseModel):
    source_date : dt.date
    target_date : dt.date
    meal_types: list[MealType] | None = None
    replace: bool = False

    @model_validator(mode="after")
    def check_dates_differ(self) -> Self:
        if self.source_date == self.target_date:
            raise ValueError("Source and target dates must differ.")
        return self

class CopyDayOut(BaseModel):
    source_date : dt.date
    target_date : dt.date
    replaced : int = 0
    copied: int