from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, HTTPException, Response
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from config import settings
from database import DbSession
from models import Food, FoodEntry
from schemas import FavouriteUpdate, FoodCreate, FoodOut, FoodUpdate, validate_macro_sum

router = APIRouter(prefix="/foods" , tags=["foods"])

def _commit (db: Session) -> None:
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise

@router.post("", response_model=FoodOut, status_code = 201)
def create_food(food: FoodCreate, db: DbSession):
    food = Food(**food.model_dump())
    db.add(food)
    _commit(db)
    db.refresh(food)
    return food

@router.get("", response_model=list[FoodOut])
def list_foods(
        db: DbSession,
        name : str | None = None,
        favourites_only: bool = False,
        sort : Literal["name", "carbs", "protein", " fats"] = "name",
        limit: Annotated[int, Query(ge=1, le=settings.max_page_size)] = settings.default_page_size,
        offset: Annotated[int, Query(ge=0)] = 0
):
    stmt = select(Food)
    if name:
        stmt = stmt.where(Food.name.ilike(f"%{name}%"))
    if favourites_only:
        stmt = stmt.where(Food.is_favourite.is_(True))

    order_columns = {
        "name": Food.name,
        "carbs": Food.carb_per_100g.desc(),
        "protein": Food.prot_per_100g.desc(),
        "fats": Food.fats_per_100g.desc()
    }
    return db.scalars(stmt.order_by(order_columns[sort]).offset(offset).limit(limit)).all()

@router.get(" /recent", response_model=list[FoodOut])
def recent_foods(db: DbSession, limit: Annotated[int, Query(ge=1, le=50)] = 8):
    """Distinct foods ordered by the most recent entry date, limited to the specified number of results, for the quick add strip"""
    
    last_eaten = (
        select(FoodEntry.food_id, func.max(FoodEntry.datetime).label("last_at"))
        .group_by(FoodEntry.food_id)
        .subquery
    )
    stmt = (
        select(Food)
        .join(last_eaten, Food.id == last_eaten.c.food_id)
        .order_by(last_eaten.c.last_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()

@router.get("/{food_id}", response_model=FoodOut)
def get_food(food_id: int, db: DbSession):
    food = db.get(Food,food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    return food

@router.put("/{food_id}", response_model=FoodOut)
def update_food(db: DbSession, food_id: int, body: FoodUpdate):
    food = db.get(Food, food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    changes = body.model_dump(exclude_unset=True)
    merged = {
        "carb" : changes.get("carb_per_100g", food.carb_per_100g),
        "prot" : changes.get("prot_per_100g", food.prot_per_100g),
        "fats" : changes.get("fats_per_100g", food.fats_per_100g),
    }
    try:
        validate_macro_sum(merged["carb"], merged["prot"], merged["fats"])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    for field, value in changes.items():
        setattr(food, field, value)
    _commit(db)
    db.refresh(food)
    return food

@router.patch("/{food_id}/favourite", response_model=FoodOut)
def set_favourite(db: DbSession, food_id: int, body: FavouriteUpdate):
    food = db.get(Food, food_id) # Retrieve food from the database using the provided food_id
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    food.is_favourite = body.is_favourite # Update the is_favourite attr from the object received in this call
    _commit(db) # return the updated food object to the client after committing the changes to the database
    db.refresh(food)
    return food

@router.delete("/{food_id}", status_code=204)
def delete_food(db: DbSession, food_id : int, force : bool = False):
    food = db.get(Food, food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    entry_count = (
        db.scalar(
            select(func.count()).select_from(FoodEntry).where(FoodEntry.food_id == food_id)
        ) or 0
    )
    
    if entry_count and not force:
        raise HTTPException(
            status_code=409,
            detail=f"'{food.name}' is used by {entry_count} entries. Delete them first")

    if entry_count:
        db.execute(
            delete(FoodEntry)
            .where(FoodEntry.food_id == food_id)
            .execution_options(synchronize_session=False)
        )
    db.delete(food)
    _commit(db)
    return Response(status_code=204)