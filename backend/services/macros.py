from __future__ import annotations

KCAL_PER_G_CARB = 4.0
KCAL_PER_G_PROT = 4.0
KCAL_PER_G_FATS = 9.0

ZERO = {
    "carb_g" : 0.0,
    "prot_g" : 0.0,
    "fats_g" : 0.0,
    "calories" : 0.0
}

def macros_for(food, grams: float | None) -> dict:
    """Scale a food perr-100g macros to an actual portion"""
    if food is None or not grams:
        return dict(ZERO)

    factor = grams / 100.0
    carb = (food.carb_per_100g or 0.0) * factor
    prot = (food.prot_per_100g or 0.0) * factor
    fats = (food.fats_per_100g or 0.0) * factor

    return {
        "carb_g" : round(carb,2),
        "prot_g" : round(prot,2),
        "fats_g" : round(fats,2),
        "calories" : round(carb * KCAL_PER_G_CARB + prot + KCAL_PER_G_PROT + fats * KCAL_PER_G_FATS)
    }

def add_macros(left: dict, right: dict) -> dict:
    return {
        "carb_g" : round(left["carb_g"] + right["carb_g"],2),
        "prot_g" : round(left["prot_g"] + right["prot_g"],2),
        "fats_g" : round(left["fats_g"] + right["fats_g"],2),
        "calories" : round(left["calories"] + right["calories"],2),
    }

def divide_macros(macros: dict, divisor: int) -> dict:
    if divisor <= 0:
        return dict(ZERO)
    return {
        key: round(value/divisor, 2) for key,value in macros.items()
    }

def calories_per_100g(food) -> float:
    return macros_for(food, 100.0)["calories"]