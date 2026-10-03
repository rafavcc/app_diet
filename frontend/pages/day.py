import datetime

from nicegui import ui

import state
import theme
from api import client
from api.runner import call
from theme import CALORIE_COLOR, MACRO_COLORS, MEAL_TYPES, meal_meta
from widgets.components import (
    empty_state,
    macro_chips,
    macro_split_bar,
    section_title,
    stat_card,
)
from widgets.feedback import confirm_dialog, guard, notify_success, notify_warning


def day_page(layout) -> None:
    cache = {"foods": [], "food_names": {}, "summary": None, "entries": [], "editing": None}

    async def reload_all() -> None:
        await load_entries()
        hero.refresh()
        meals_list.refresh()
        summary_panel.refresh()
        charts_panel.refresh()

    async def load_entries() -> None:
        day = state.get_date()
        async with guard("load this day") as ok:
            cache["entries"] = await call(client.get_entries, date=day, include_macros=True)
            cache["summary"] = await call(client.get_daily_summary, day)
        if not ok[0]:
            cache["entries"], cache["summary"] = [], None

    with layout("/", date_nav_handler=reload_all):
        # --- Hero: totals for the selected day ---
        @ui.refreshable
        def hero() -> None:
            totals = (cache["summary"] or {}).get("totals", {}) or {}
            goals = state.get_goals()
            show_goals = state.goals_enabled()

            with ui.column().classes("w-full gap-2"):
                with ui.row().classes("w-full gap-2 flex-wrap"):
                    stat_card(
                        "Calories",
                        totals.get("calories", 0),
                        "kcal",
                        CALORIE_COLOR,
                        goal=goals["calories"] if show_goals else None,
                        icon="local_fire_department",
                    )
                    for key, label, field, unit in theme.MACRO_META:
                        stat_card(
                            label,
                            totals.get(field, 0),
                            unit,
                            MACRO_COLORS[key],
                            goal=goals[field] if show_goals else None,
                        )
                macro_split_bar(totals)

        hero()

        # --- Quick add ---
        @ui.refreshable
        def quick_add() -> None:
            shortcuts = cache["foods"][:10]
            if not shortcuts:
                return
            section_title("Quick add", "bolt")
            with ui.row().classes("w-full gap-2 flex-wrap"):
                for food in shortcuts:
                    chip = ui.button(
                        food["name"],
                        icon="star" if food.get("is_favourite") else None,
                        on_click=lambda f=food: open_log_dialog(f),
                    ).props("outline no-caps dense rounded")
                    chip.tooltip(f"{round(food.get('calories_per_100g', 0))} kcal / 100g")

        quick_add()

        # --- Meals: entries grouped by meal type ---
        section_title(
            "Meals",
            "restaurant",
            trailing=lambda: ui.button(
                "Copy day", icon="content_copy", on_click=lambda: open_copy_dialog()
            ).props("flat dense no-caps"),
        )

        @ui.refreshable
        def meals_list() -> None:
            entries = cache["entries"]
            if not entries:
                empty_state(
                    "no_meals",
                    "Nothing logged yet",
                    "Log the first food for this day, or copy meals from another date.",
                    "Log food",
                    lambda: open_log_dialog(),
                )
                return

            grouped: dict[str, list] = {}
            for entry in entries:
                grouped.setdefault(entry.get("meal_type") or "other", []).append(entry)

            with ui.column().classes("w-full gap-3"):
                for meal_type in MEAL_TYPES:
                    if meal_type not in grouped:
                        continue
                    _render_meal(meal_type, grouped[meal_type])

        def _render_meal(meal_type: str, entries: list) -> None:
            meta = meal_meta(meal_type)
            calories = sum((e.get("macros") or {}).get("calories", 0) for e in entries)

            with ui.row().classes("w-full items-center justify-between px-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon(meta["icon"]).style(f"color: {meta['color']}")
                    ui.label(meta["label"]).classes("text-sm font-semibold")
                ui.label(f"{round(calories)} kcal").classes("text-xs font-semibold opacity-60")

            with ui.column().classes("w-full gap-2"):
                for entry in entries:
                    _render_entry_card(entry, meta)

        def _render_entry_card(entry: dict, meta: dict) -> None:
            with ui.card().classes("app-card meal-card w-full p-3").style(
                f"--meal-color: {meta['color']}"
            ):
                with ui.row().classes("w-full items-start justify-between gap-2 no-wrap"):
                    with ui.column().classes("gap-1 min-w-0"):
                        with ui.row().classes("items-baseline gap-2 flex-wrap"):
                            ui.label(entry.get("food_name") or f"Food #{entry['food_id']}").classes(
                                "font-semibold truncate"
                            )
                            ui.label(f"({round(entry.get('grams', 0))} g)").classes(
                                "text-xs opacity-60"
                            )
                        ui.label(_time_of(entry)).classes("text-xs opacity-40")
                        macro_chips(entry.get("macros") or {})
                    with ui.row().classes("gap-0 shrink-0"):
                        ui.button(
                            icon="edit", on_click=lambda e=entry: open_log_dialog(entry=e)
                        ).props("flat dense round").classes("opacity-60")
                        ui.button(
                            icon="delete",
                            on_click=lambda e=entry: ask_delete(
                                e, f"Remove {e.get('food_name')} from this day?"
                            ),
                        ).props("flat dense round color=negative").classes("opacity-70")

        meals_list()

    # --- Summary ---
        @ui.refreshable
        def summary_panel() -> None:
            summary = cache["summary"]
            by_meal = (summary or {}).get("by_meal_type") or {}
            if not by_meal:
                return

            section_title("Breakdown", "table_chart")
            columns = [
                {"name": "meal_type", "label": "Meal", "field": "meal_type", "align": "left"},
                {"name": "calories", "label": "kcal", "field": "calories", "align": "right"},
                {"name": "carbs", "label": "Carbs (g)", "field": "carbs", "align": "right"},
                {"name": "protein", "label": "Protein (g)", "field": "protein", "align": "right"},
                {"name": "fats", "label": "Fat (g)", "field": "fats", "align": "right"},
            ]
            rows = [
                {
                    "meal_type": meal_meta(key)["label"],
                    "calories": round(value.get("calories", 0), 1),
                    "carbs": round(value.get("carbs_g", 0), 1),
                    "protein": round(value.get("protein_g", 0), 1),
                    "fats": round(value.get("fats_g", 0), 1),
                }
                for key, value in by_meal.items()
            ]
            totals = summary.get("totals", {})
            rows.append({
                "meal_type": "Total",
                "calories": round(totals.get("calories", 0), 1),
                "carbs": round(totals.get("carbs_g", 0), 1),
                "protein": round(totals.get("protein_g", 0), 1),
                "fats": round(totals.get("fats_g", 0), 1),
            })
            ui.table(columns=columns, rows=rows, row_key="meal_type").classes(
                "app-table w-full app-card"
            ).props("flat dense")

        summary_panel()

        # --- Charts ---

# --- Charts ---
        @ui.refreshable
        def charts_panel() -> None:
            summary = cache["summary"]
            by_meal = (summary or {}).get("by_meal_type") or {}
            if not by_meal:
                return

            dark = state.get_dark()
            base = theme.chart_base(dark)
            axis = base.pop("_axis")
            totals = summary.get("totals", {})

            section_title("Charts", "donut_small")
            with ui.row().classes("w-full gap-3 flex-wrap"):
                with ui.card().classes("app-card flex-1 min-w-72 p-2"):
                    ui.echart({
                        **base,
                        "tooltip": {"trigger": "item"},
                        "series": [{
                            "type": "pie",
                            "radius": ["55%", "78%"],
                            "avoidLabelOverlap": True,
                            "itemStyle": {"borderRadius": 6, "borderWidth": 2},
                            "label": {"show": False},
                            "data": [
                                {
                                    "name": label,
                                    "value": round(totals.get(field, 0), 1),
                                    "itemStyle": {"color": MACRO_COLORS[key]},
                                }
                                for key, label, field, _ in theme.MACRO_META
                            ],
                        }],
                    }).classes("w-full h-64")

                with ui.card().classes("app-card flex-1 min-w-72 p-2"):
                    labels = [meal_meta(key)["label"] for key in by_meal]
                    ui.echart({
                        **base,
                        "xAxis": {"type": "category", "data": labels, **axis},
                        "yAxis": {"type": "value", **axis},
                        "series": [
                            {
                                "name": label,
                                "type": "bar",
                                "stack": "total",
                                "itemStyle": {"color": MACRO_COLORS[key]},
                                "data": [
                                    round(value.get(field, 0), 1) for value in by_meal.values()
                                ],
                            }
                            for key, label, field, _ in theme.MACRO_META
                        ],
                    }).classes("w-full h-64")

        charts_panel()

        # --- Floating add button ---
        with ui.page_sticky(position="bottom-right", x_offset=18, y_offset=80):
            ui.button(icon="add", on_click=lambda: open_log_dialog()).props(
                "fab color=primary"
            ).tooltip("Log food")

    # --- Log / edit dialog ---
    with ui.dialog() as log_dialog, ui.card().classes("app-card w-96 max-w-full gap-2 p-5"):
        dialog_title = ui.label("Log food").classes("text-lg font-semibold")
        food_select = ui.select({}, value=None, with_input=True).classes("w-full").props(
            "outlined"
        )
        with ui.row().classes("w-full gap-2 no-wrap"):
            grams_input = ui.number("Grams", min=1, step=10, value=100).classes("flex-1").props(
                "outlined dense suffix=g"
            )
            time_input = ui.input("Time").classes("flex-1").props('outlined dense type=time')
        meal_type_select = ui.select(
            {key: meal_meta(key)["label"] for key in MEAL_TYPES}, label="Meal"
        ).classes("w-full").props("outlined dense")
        preview = ui.label("").classes("text-xs opacity-60 min-h-4")

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=log_dialog.close).props("flat no-caps")
            save_button = ui.button("Save").props("unelevated no-caps color=primary")

    def _update_preview() -> None:
        food = cache["food_names"].get(food_select.value)
        grams = grams_input.value or 0
        if not food or not grams:
            preview.text = ""
            return
        factor = grams / 100
        preview.text = (
            f"{round(food.get('calories_per_100g', 0) * factor):g} kcal • "
            f"C {round(food['carb_per_100g'] * factor, 1):g}g • "
            f"P {round(food['prot_per_100g'] * factor, 1):g}g • "
            f"F {round(food['fats_per_100g'] * factor, 1):g}g"
        )

    food_select.on_value_change(lambda _: _update_preview())
    grams_input.on_value_change(lambda _: _update_preview())

    def open_log_dialog(food: dict | None = None, entry: dict | None = None) -> None:
        cache["editing"] = entry["id"] if entry else None
        dialog_title.text = "Edit entry" if entry else "Log food"
        food_select.options = {f["id"]: f["name"] for f in cache["foods"]}
        food_select.update()

        if entry:
            food_select.value = entry["food_id"]
            grams_input.value = entry["grams"]
            meal_type_select.value = entry.get("meal_type") or "other"
            time_input.value = _time_of(entry)
        else:
            food_select.value = food["id"] if food else None
            grams_input.value = 100
            meal_type_select.value = _suggested_meal_type()
            time_input.value = datetime.datetime.now().strftime("%H:%M")

        _update_preview()
        log_dialog.open()

    async def save_entry() -> None:
        if not food_select.value:
            notify_warning("Pick a food first.")
            return
        if not grams_input.value or grams_input.value <= 0:
            notify_warning("Grams must be greater than zero.")
            return

        payload = {
            "food_id": food_select.value,
            "grams": float(grams_input.value),
            "meal_type": meal_type_select.value or "other",
            "datetime": _combine(state.get_date(), time_input.value),
        }

        async with guard("save the entry", save_button) as ok:
            if cache["editing"]:
                await call(client.update_entry, cache["editing"], payload)
            else:
                await call(client.create_entry, payload)

        if ok[0]:
            log_dialog.close()
            notify_success("Entry saved")
            await reload_all()

    save_button.on_click(save_entry)

    # --- Delete confirmation ---
    async def do_delete(entry: dict) -> None:
        async with guard("delete the entry") as ok:
            await call(client.delete_entry, entry["id"])
        if ok[0]:
            notify_success("Entry deleted")
            await reload_all()

    ask_delete_dialog = confirm_dialog("Delete entry", "", do_delete, confirm_label="Delete")

    def ask_delete(entry: dict, message: str) -> None:
        ask_delete_dialog(entry, message)

    # --- Copy day dialog ---
    with ui.dialog() as copy_dialog, ui.card().classes("app-card w-80 gap-2 p-5"):
        ui.label("Copy meals").classes("text-lg font-semibold")
        ui.label("Duplicate another day's meals onto this one.").classes("text-xs opacity-60")
        source_picker = ui.date(value=state.get_date()).props("minimal").classes("w-full")
        copy_types = ui.select(
            {key: meal_meta(key)["label"] for key in MEAL_TYPES},
            label="Meals to copy (all if empty)",
            multiple=True,
        ).classes("w-full").props("outlined dense use-chips")
        replace_switch = ui.switch("Replace what is already logged", value=False)

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=copy_dialog.close).props("flat no-caps")
            copy_button = ui.button("Copy").props("unelevated no-caps color=primary")

    def open_copy_dialog() -> None:
        yesterday = datetime.date.fromisoformat(state.get_date()) - datetime.timedelta(days=1)
        source_picker.value = yesterday.isoformat()
        copy_types.value = []
        replace_switch.value = False
        copy_dialog.open()

    async def do_copy() -> None:
        if not source_picker.value or source_picker.value == state.get_date():
            notify_warning("Pick a different source day.")
            return
        async with guard("copy the meals", copy_button) as ok:
            result = await call(
                client.copy_day,
                source_picker.value,
                state.get_date(),
                copy_types.value or None,
                replace_switch.value,
            )
        if ok[0]:
            copy_dialog.close()
            copied = result["copied"]
            notify_success(f"Copied {copied} {'entry' if copied == 1 else 'entries'}")
            await reload_all()

    copy_button.on_click(do_copy)

    async def bootstrap() -> None:
        favourites, everything = [], []
        async with guard("load your foods") as ok:
            favourites = await call(client.get_foods, None, True)
            everything = await call(client.get_foods)
        if not ok[0]:
            return

        seen, ordered = set(), []
        for food in favourites + everything:
            if food["id"] not in seen:
                seen.add(food["id"])
                ordered.append(food)
        cache["foods"] = ordered
        cache["food_names"] = {f["id"]: f for f in ordered}
        quick_add.refresh()
        await reload_all()

    ui.timer(0.05, bootstrap, once=True)


def _time_of(entry: dict) -> str:
    try:
        return datetime.datetime.fromisoformat(entry.get("datetime", "")).strftime("%H:%M")
    except ValueError:
        return ""


def _combine(day: str, clock: str) -> str:
    try:
        parsed = datetime.datetime.strptime(clock or "", "%H:%M").time()
    except ValueError:
        parsed = datetime.datetime.now().time()
    return datetime.datetime.combine(datetime.date.fromisoformat(day), parsed).isoformat()


def _suggested_meal_type() -> str:
    hour = datetime.datetime.now().hour
    if hour < 10:
        return "breakfast"
    if hour < 12:
        return "morning_snack"
    if hour < 15:
        return "lunch"
    if hour < 18:
        return "afternoon_snack"
    return "dinner"
