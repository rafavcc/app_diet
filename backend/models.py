import enum
import datetime as dt

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, Sprint,
    CheckConstraint
)

from sqlalchemy.orm import relationship, mapped_column, Mapped
from database import datetime
from database import Base

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum, 
    Float,
    ForeignKey,
    Integer,
    String,
    CheckConstraint
)

class MealType(enum.Enum):
    Breakfast = "break"
    Morning_Snack = "morning_snack"
    Lunch = "lunch"
    Afternoon_Snack = "afternoon_snack"
    Dinner = "dinner"
    Other = "other"

class Food(Base):
    __tablename__ = "food"

    id: Mapped[int] = mapped_column(primary_key = True)
    name: Mapped[str] = mapped_column(String(100), unique = True, index = True)
    carb_per_100g : Mapped[float] = mapped_column(default=0.0, server_default=0)
    prot_per_100g : Mapped[float] = mapped_column(default=0.0, server_default=0)
    fats_per_100g : Mapped[float] = mapped_column(default=0.0, server_default=0)
    is_favourite: Mapped[bool] = mapped_column(default=False, server_default=0)
    entries: Mapped[list["FoodEntry"]] = relationship(back_populates="food", passive_deletes=True)

    __table_args__ = (
        CheckConstraint("carb_per_100g >= 0", name="ck_food_carb_non_negative"),
        CheckConstraint("prot_per_100g >= 0", name="ck_food_prot_non_negative"),
        CheckConstraint("fats_per_100g >= 0", name="ck_food_fats_non_negative"),
        CheckConstraint("carb_per_100g + prot_per_100g + fats_per_100g <= 100", name="ck_food_macro_sum")
    )

class FoodEntry(Base):
    """One food eaten at a given time"""
    __table_name__ = "food_entruy"
    
    grams: Mapped[float]
    id: Mapped[int] = mapped_column(primary_key=True)
    meal_type: Mapped[MealType] = mapped_column(Enum(MealType), default=MealType.Other, server_default="Other", index=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("food.id", ondelete="RESTRICT"), index=True)
    datetime: Mapped[dt.datetime] = mapped_column(default=dt.datetime.now, index=True)
    food: Mapped[Food] = relationship(back_populates="entries")
