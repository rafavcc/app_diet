from nicegui import ui

from api import client
from api.client import ApiError
from api.runner import call
import theme
from theme import CALORIE_COLOR, MACRO_COLORS
from widgets.components import empty_state
from widgets.feedback import confirm_dialog, guard, notify_error, notify_success, notify_warning

MACRO_BUDGET = 100.0


def foods_page() -> None:
    cache = {"foods": [], "editing": None, "search": "", "favourites_only": False}

    async def reload() -> None:
        async with guard("load your foods") as ok:
            cache["foods"] = await call(
                client.get_foods, cache["search"] or None, cache["favourites_only"]
            )
        if not ok[0]:
            cache["foods"] = []
        food_list.refresh()

    # --- Toolbar ---
    with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"):
        ui.label("Food library").classes("text-xl font-bold")
        ui.button("Add food", icon="add", on_click=lambda: open_dialog()).props(
            "unelevated no-caps color=primary"
        )

    with ui.row().classes("w-full items-center gap-2 mt-3 flex-wrap"):
        search = (
            ui.input(placeholder="Search foods...")
            .classes("flex-1 min-w-48")
            .props("outlined dense clearable debounce=250")
        )

        async def on_search(event) -> None:
            cache["search"] = event.value or ""
            await reload()

        search.on_value_change(on_search)

        async def on_filter(event) -> None:
            cache["favourites_only"] = bool(event.value)
            await reload()

        ui.switch("Favourites").props("dense").on_value_change(on_filter)

    # --- List ---
    @ui.refreshable
    def food_list() -> None:
        foods = cache["foods"]
        if not foods:
            empty_state(
                "restaurant_menu",
                "No foods yet" if not cache["search"] else "No matches",
                "Add the foods you eat so you can log meals in one tap."
                if not cache["search"]
                else f'Nothing matches "{cache["search"]}".',
                "Add your first food" if not cache["search"] else None,
                (lambda: open_dialog()) if not cache["search"] else None,
            )
            return

        ui.label(f"{len(foods)} food{'s' if len(foods) != 1 else ''}").classes(
            "text-xs opacity-50 mt-3"
        )

        with ui.column().classes("w-full gap-2 mt-1"):
            for food in foods:
                _render_food_card(food)

    def _render_food_card(food: dict) -> None:
        with ui.card().classes("app-card w-full p-3"):
            with ui.row().classes("w-full items-center justify-between gap-2 no-wrap"):
                with ui.column().classes("gap-1 min-w-0 flex-1"):
                    with ui.row().classes("items-baseline gap-2"):
                        ui.label(food["name"]).classes("font-semibold truncate")
                        ui.label(
                            f"({round(food.get('calories_per_100g', 0)):g} kcal / 100g"
                        ).classes("text-xs opacity-60")
                    _macro_bar(food)
                    with ui.row().classes("gap-3"):
                        for key, label, _, _unit in theme.MACRO_META:
                            value = food[f"{'fats' if key == 'fats' else key}_per_100g"]
                            ui.label(f"{label} {round(value, 1):g}g").classes(
                                "text-xs"
                            ).style(f"color: {MACRO_COLORS[key]}")

                with ui.row().classes("gap-0 shrink-0"):
                    ui.button(
                        icon="star" if food.get("is_favourite") else "star_border",
                        on_click=lambda f=food: toggle_favourite(f),
                    ).props("flat dense round").classes(
                        "text-amber-500" if food.get("is_favourite") else "opacity-40"
                    ).tooltip("Favourite")
                    ui.button(
                        icon="edit", on_click=lambda f=food: open_dialog(f)
                    ).props("flat dense round").classes("opacity-60")
                    ui.button(
                        icon="delete",
                        on_click=lambda f=food: ask_delete(
                            f, f"'{f['name']}' will be permanently removed."
                        ),
                    ).props("flat dense round color=negative").classes("opacity-70")

    def _macro_bar(food: dict) -> None:
        with ui.element("div").classes("w-full flex h-1.5 rounded-full overflow-hidden").style(
            "background: rgba(148,163,184,.2)"
        ):
            for key, _label, _field, _unit in theme.MACRO_META:
                value = food[f"{key}_per_100g"] or 0
                if value <= 0:
                    continue
                ui.element("div").style(
                    f"width: {min(value, MACRO_BUDGET)}%; background: {MACRO_COLORS[key]};"
                )

    food_list()

    # --- Add / edit dialog ---
    with ui.dialog() as dialog, ui.card().classes("app-card w-96 max-w-full gap-2 p-5"):
        dialog_title = ui.label("Add food").classes("text-lg font-semibold")
        name_input = ui.input("Name").classes("w-full").props("outlined dense autofocus")

        inputs = {}
        for key, label, _field, _unit in theme.MACRO_META:
            inputs[key] = (
                ui.number(f"{label} per 100g", min=0, max=100, step=0.1, value=0)
                .classes("w-full")
                .props("outlined dense suffix=g")
            )

        budget_bar = ui.linear_progress(value=0, show_value=False, size="8px").props("rounded")
        budget_label = ui.label("").classes("text-xs")
        calories_label = ui.label("").classes("text-xs opacity-60")

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
            save_button = ui.button("Save").props("unelevated no-caps color=primary")

    def _totals() -> float:
        return sum(inputs[key].value or 0 for key, _l, _f, _u in theme.MACRO_META)

    def _update_budget() -> None:
        total = _totals()
        over = total > MACRO_BUDGET
        budget_bar.value = min(total / MACRO_BUDGET, 1.0)
        budget_bar.style(f"color: {'#DC2626' if over else CALORIE_COLOR}")
        budget_label.text = f"{total:.1f} g of 100 g accounted for"
        budget_label.style(f"color: {'#DC2626' if over else 'inherit'}")
        calories_label.text = (
            f"{round((inputs['carbs'].value or 0) * 4 + (inputs['protein'].value or 0) * 4 + (inputs['fats'].value or 0) * 9)} kcal per 100g"
        )
        save_button.set_enabled(not over and bool((name_input.value or "").strip()))

    name_input.on_value_change(lambda _: _update_budget())
    for field in inputs.values():
        field.on_value_change(lambda _: _update_budget())

    def open_dialog(food: dict | None = None) -> None:
        cache["editing"] = food["id"] if food else None
        dialog_title.text = "Edit food" if food else "Add food"
        name_input.value = food["name"] if food else ""
        for key, _l, _f, _u in theme.MACRO_META:
            inputs[key].value = food[f"{key}_per_100g"] if food else 0
        _update_budget()
        dialog.open()

    async def save() -> None:
        name = (name_input.value or "").strip()
        if not name:
            notify_warning("Give the food a name.")
            return

        payload = {"name": name}
        for key, _l, _f, _u in theme.MACRO_META:
            payload[f"{key}_per_100g"] = float(inputs[key].value or 0)

        async with guard("save the food", save_button) as ok:
            if cache["editing"]:
                await call(client.update_food, cache["editing"], payload)
            else:
                await call(client.create_food, payload)
        if ok[0]:
            dialog.close()
            notify_success("Food saved")
            await reload()

    save_button.on_click(save)

    # --- Favourite & delete ---
    async def toggle_favourite(food: dict) -> None:
        async with guard("update the favourite") as ok:
            await call(client.set_favourite, food["id"], not food.get("is_favourite"))
        if ok[0]:
            await reload()

    async def do_delete(food: dict) -> None:
        try:
            await call(client.delete_food, food["id"])
        except ApiError as exc:
            if exc.status_code == 409:
                force_delete_dialog(food, exc.message)
            else:
                notify_error(exc.message)
            return
        notify_success("Food deleted")
        await reload()

    async def do_force_delete(food: dict) -> None:
        async with guard("delete the food") as ok:
            await call(client.delete_food, food["id"], True)
        if ok[0]:
            notify_success("Food and its entries deleted")
            await reload()

    force_delete_dialog = confirm_dialog(
        "Also delete logged entries?",
        "This food is used by logged entries. Delete those entries too?",
        do_force_delete,
        confirm_label="Delete everything",
    )
    ask_delete_dialog = confirm_dialog("Delete food", "", do_delete, confirm_label="Delete")

    def ask_delete(food: dict, message: str) -> None:
        ask_delete_dialog(food, message)

    ui.timer(0.05, reload, once=True)
