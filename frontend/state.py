import datetime

from nicegui import app

DEFAULT_GOALS = {"calories": 2000.0, "carbs_g": 250.0, "protein_g": 120.0, "fats_g": 65.0}


def _store() -> dict:
    return app.storage.user


def get_date() -> str:
    return _store().get("selected_date") or datetime.date.today().isoformat()


def set_date(value: str) -> None:
    _store()["selected_date"] = value


def shift_date(days: int) -> str:
    current = datetime.date.fromisoformat(get_date())
    set_date((current + datetime.timedelta(days=days)).isoformat())
    return get_date()


def is_today() -> bool:
    return get_date() == datetime.date.today().isoformat()


def get_dark() -> bool:
    return bool(_store().get("dark_mode", False))


def set_dark(value: bool) -> None:
    _store()["dark_mode"] = value


def get_goals() -> dict:
    stored = _store().get("goals") or {}
    return {**DEFAULT_GOALS, **stored}


def set_goals(goals: dict) -> None:
    _store()["goals"] = {key: float(value) for key, value in goals.items() if value is not None}


def goals_enabled() -> bool:
    return bool(_store().get("goals_enabled", True))


def set_goals_enabled(value: bool) -> None:
    _store()["goals_enabled"] = value