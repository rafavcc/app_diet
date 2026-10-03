import logging
import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

BASE_URL = os.getenv("DIET_API", "http://127.0.0.1:8000")

DEFAULT_TIMEOUT = (1.0, 6.0)

class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"API request failed ({response.status_code})"

    detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
    if isinstance(detail, list):
        return "; ".join(
            str(item.get("msg", item)) if isinstance(item, dict) else str(item)
            for item in detail
        )
    return str(detail)


def _build_session() -> requests.Session:
    session = requests.Session()

    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

_session = _build_session()

def _detail_from(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"Request failed ({response.status_code})"

    detail = payload.get("detail") if isinstance(payload,dict) else None
    if isinstance(detail,str):
        return detail
    if isinstance(detail,list) and detail:
        first = detail[0]
        field = ".".join(str(part) for part in first.get("loc", []) if part != "body")
        message = first.get("msg", "Invalid input.")
        return f"{field}: {message}"  if field else message
    return str(detail) if detail is not None else f"Request failed ({response.status_code})"

def _request(method:str, path: str, **kwargs: Any) -> Any:
    url = f"{BASE_URL}{path}"
    try:
        response = _session.request(method, url, timeout=DEFAULT_TIMEOUT, **kwargs)
    except requests.exceptions.Timeout as exc:
        log.warning("%s %s timed out", method, url)
        raise ApiError("The server took too long to respond.") from exc
    except requests.exceptions.ConnectionError as exc:
        log.warning("%s %s unreachable", method, url)
        raise ApiError("Cannot reach the server. Is the backend running?") from exc
    except requests.exceptions.RequestException as exc:
        log.warning("%s %s failed", method, url)
        raise ApiError("Unexpected network error") from exc

    if not response.ok:
        detail = _detail_from(response)
        log.warning("%s %s -> %s %s", method, url, response.status_code, detail)
        raise ApiError(detail, status_code=response.status_code)

    if response.status_code == 204 or not response.content:
        return None
    return response.json()


def _food_for_ui(food: dict) -> dict:
    return {
        **food,
        "carbs_per_100g": food.get("carbs_per_100g", food.get("carb_per_100g", 0)),
        "protein_per_100g": food.get("protein_per_100g", food.get("prot_per_100g", 0)),
    }


def _food_payload(data: dict) -> dict:
    payload = dict(data)
    for ui_field, api_field in (
        ("carbs_per_100g", "carb_per_100g"),
        ("protein_per_100g", "prot_per_100g"),
    ):
        if ui_field in payload:
            payload[api_field] = payload.pop(ui_field)
    return payload


def _macros_for_ui(macros: dict) -> dict:
    return {
        **macros,
        "carbs_g": macros.get("carbs_g", macros.get("carb_g", 0)),
        "protein_g": macros.get("protein_g", macros.get("prot_g", 0)),
        "fats_g": macros.get("fats_g", macros.get("fats", 0)),
        "calories": macros.get("calories", macros.get("total_calories", 0)),
    }


def _entry_for_ui(entry: dict) -> dict:
    if isinstance(entry.get("macros"), dict):
        return {**entry, "macros": _macros_for_ui(entry["macros"])}
    return entry


def _summary_for_ui(summary: dict) -> dict:
    result = dict(summary)
    for key in ("totals", "averages"):
        if isinstance(result.get(key), dict):
            result[key] = _macros_for_ui(result[key])
    if isinstance(result.get("by_meal_type"), dict):
        result["by_meal_type"] = {
            key: _macros_for_ui(value) for key, value in result["by_meal_type"].items()
        }
    if isinstance(result.get("days"), list):
        result["days"] = [
            {**day, "macros": _macros_for_ui(day["macros"])}
            if isinstance(day.get("macros"), dict)
            else day
            for day in result["days"]
        ]
    return result


def health() -> bool:
    try:
        return _request("GET", "/health").get("status") == "ok"
    except ApiError:
        return False

def get_foods(
        name : str | None = None,
        favourites_only : bool = False,
        sort: str = "name",
        limit: int = 500
) -> list:
    params: dict[str, Any] = {"sort" : sort, "limit": limit}
    if name:
        params["name"] = name
    if favourites_only:
        params["favourites_only"] = True
    return [_food_for_ui(food) for food in _request("GET", "/foods", params=params)]

def get_recent_foods(limit: int = 8) -> list:
    return [_food_for_ui(food) for food in _request("GET", "/foods/recent", params={"limit": limit})]

def create_food(data: dict) -> dict:
    return _food_for_ui(_request("POST", "/foods", json=_food_payload(data)))

def update_food(food_id: int, data: dict) -> dict:
    return _food_for_ui(_request("PUT", f"/foods/{food_id}", json=_food_payload(data)))

def set_favourite(food_id: int, is_favourite:bool) -> dict:
    return _request("PATCH", f"/foods/{food_id}/favourite", json={"is_favourite": is_favourite})

def delete_food(food_id: int, force : bool = False) -> None:
    _request("DELETE", f"/foods/{food_id}", params={"force": force})

def get_entries(date: str | None = None, meal_type: str | None = None, include_macros : bool = False) -> list:
    params: dict[str, Any] = {"limit": 500}
    if date:
        params["date"] = date
    if meal_type:
        params["meal_type"] = meal_type
    if include_macros:
        params["include_macros"] = True
    return [_entry_for_ui(entry) for entry in _request("GET", "/entries", params=params)]

def create_entry(data: dict) -> dict:
    return _request("POST", "/entries", json=data)

def update_entry(entry_id: int, data: dict) -> dict:
    return _request("PUT", f"/entries/{entry_id}", json=data)

def delete_entry(entry_id: int) -> None:
    return _request("DELETE", f"/entries/{entry_id}")

def get_entry_macros(entry_id: int) -> dict:
    return _entry_for_ui(_request("GET", f"/entries/{entry_id}/macros"))

def get_daily_summary(date: str) -> dict:
    return _summary_for_ui(_request("GET", "/entries/daily-summary", params={"date": date}))

def get_range_summary(start: str, end: str) -> dict:
    return _summary_for_ui(_request("GET", "/entries/range-summary", params={"start": start, "end": end}))

def copy_day(
        source_date: str,
        target_date: str,
        meal_types: list[str] | None = None,
        replace: bool = False) -> dict:
    payload: dict[str, Any]={
        "source_date": source_date,
        "target_date": target_date,
        "replace": replace
    }
    if meal_types:
        payload["meal_types"] = meal_types
    return _request("POST", "/entries/copy", json=payload)
