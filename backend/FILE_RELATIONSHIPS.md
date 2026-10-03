# Backend file relationships

This document describes the files currently present in `backend/` and how the API pieces are intended to fit together. The Python package uses direct imports such as `from config import settings`; run the app from this directory (for example, with Uvicorn's import path set to `main:app`) for those imports to resolve as written.

## Request and data flow

```text
HTTP client
    |
    v
main.py  (FastAPI application and router registration; currently unfinished)
    |
    +--> routers/foods.py   --> schemas.py --> models.py --> database.py --> SQL database
    |                               |             |
    |                               +--> services/macros.py
    |
    +--> routers/entries.py --> schemas.py --> models.py --> database.py
                                    |
                                    +--> services/macros.py
```

The routers define HTTP operations, use Pydantic schemas to validate input and shape output, and read or change SQLAlchemy models through a request-scoped database session. `services/macros.py` contains reusable portion and nutrition calculations used by the schemas and the entries API.

## Files

| File | Role and relationships |
| --- | --- |
| `config.py` | Defines `Settings` and the cached module-level `settings` object. `database.py` reads `settings.database_url` to create the SQLAlchemy engine. The routers use settings for API limits. `logging_config.py` also expects a logging-level setting. |
| `database.py` | Builds the SQLAlchemy engine and `SessionLocal`, declares the shared ORM `Base`, and provides `get_db`/`DBSession` for FastAPI dependency injection. It also provides `ping()` for a basic database connection check. `models.py` is intended to inherit from its `Base`. |
| `models.py` | Declares the `MealType` enum and ORM entities `Food` and `FoodEntry`. A food has many entries; each entry points back to one food through `food_id` and the `food` relationship. Both routers query or mutate these models. |
| `schemas.py` | Defines Pydantic request and response types for foods, food entries, and daily/range summaries. It imports `MealType` from `models.py`, and imports calorie constants from `services/macros.py`. `FoodOut` also calculates calories per 100 g for API responses. The routers use these schemas as endpoint inputs and `response_model`s. |
| `routers/foods.py` | Defines the `/foods` router for creating, listing, retrieving, editing, favouriting, and deleting foods. It uses `Food` and `FoodEntry` for persistence, food schemas for validation/serialization, and configuration for pagination. It checks entry usage before deleting a food. |
| `routers/entries.py` | Defines the `/entries` router and imports the models, entry/summary schemas, database dependency, settings, and macro helpers needed for logging foods and producing summaries. The file currently contains only the router declaration and a commit helper; its endpoint implementations are not present yet. |
| `services/macros.py` | Holds nutrition calculation helpers and the per-gram calorie constants. `macros_for` scales a food's per-100-g values to a portion, `add_macros` combines totals, and `divide_macros` calculates averages. It is shared by schemas and the entries router. |
| `main.py` | Intended application entry point: it should create the FastAPI app, configure startup/lifespan behavior, and include the food and entry routers. The file currently stops at an incomplete FastAPI import, so no app or router registration exists yet. |
| `logging_config.py` | Defines `configure_logging()` and `get_logger()`. It reads `settings` from `config.py`; the main application is the natural place to call `configure_logging()` during startup. |
| `requirements.txt` | Lists Python packages needed by the backend, including FastAPI, SQLAlchemy, Pydantic, and Uvicorn. It supports the modules above rather than being imported by them. |
| `review.txt` | Contains a short list of Python learning/resource names. No backend source file imports it; it has no runtime connection to the API. |

The local `.venv/` directory contains the backend's Python environment and installed command-line tools; it is generated environment state, not application source, and is not listed individually here.

## Data model and shared behavior

`Food` stores a food name, its carbohydrate/protein/fat values per 100 g, and its favourite flag. `FoodEntry` represents an amount of a food eaten at a date/time and meal type. The `Food.entries` and `FoodEntry.food` ORM relationships express the one-to-many association, while the foreign key connects each entry to its food in the database.

The food router owns food catalog operations. The entries router is intended to own consumption logging and summaries. Both depend on the same database setup and model definitions, so food deletion must account for entries that reference that food. Schemas keep API payload validation and output conversion separate from the ORM entities, while macro helpers keep nutrition arithmetic reusable.

## Wiring issues visible in the current files

These are current source-state notes, because some of the intended links above are not executable yet:

- `main.py` is syntactically incomplete, and `routers/entries.py` has no endpoints beyond its commit helper.
- `database.py` exports `DBSession`, but `routers/foods.py` imports `DbSession` with different capitalization. `models.py` also imports `datetime` from `database.py`, where it is not defined.
- `models.py` imports `Sprint` from SQLAlchemy, which is not a standard SQLAlchemy symbol, and `FoodEntry` uses `__table_name__` rather than SQLAlchemy's `__tablename__` attribute.
- `logging_config.py` reads `settings.log_level`, but `config.py` does not currently define that setting.
- Some schema names referenced by `routers/entries.py` differ from the names declared in `schemas.py` (`CopyDayOut`/`CopyDatOut`), and the entries router's functionality is only scaffolded.

The relationship diagram and role descriptions show the intended architecture; the notes above identify places where the current code still needs alignment before the full backend can run.
