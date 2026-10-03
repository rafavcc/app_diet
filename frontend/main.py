import datetime
import os

from nicegui import app, ui

import state
import theme
from api import client
from api.runner import call
from pages.day import day_page
from pages.foods import foods_page
from pages.trends import trends_page

NAV_ITEMS = [
    ("/", "Today", "today"),
    ("/foods", "Foods", "restaurant_menu"),
    ("/trends", "Trends", "insights"),
]


def _nav_buttons(active: str) -> None:
    for path, label, icon in NAV_ITEMS:
        button = ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p))
        button.props("flat no-caps dense").classes("text-white px-2")
        if path == active:
            button.classes("bg-white/25 rounded-lg")
        else:
            button.classes("opacity-80")


def _connection_banner() -> None:
    """Polls /health so a dead backend is visible instead of silently failing every action."""
    banner = ui.row().classes(
        "w-full items-center justify-center gap-2 bg-red-600 text-white text-sm py-1"
    )
    banner.visible = False
    with banner:
        ui.icon("cloud_off")
        ui.label("Backend unreachable - retrying...")

    async def check() -> None:
        banner.visible = not await call(client.health)

    ui.timer(10.0, check)
    # Delayed rather than immediate: updates made before the websocket connects are lost.
    ui.timer(1.0, check, once=True)


def _date_navigator(on_change) -> None:
    label = ui.label().classes("font-semibold text-sm text-white min-w-32 text-center")

    def render() -> None:
        selected = datetime.date.fromisoformat(state.get_date())
        today = datetime.date.today()
        if selected == today:
            label.text = "Today"
        elif selected == today - datetime.timedelta(days=1):
            label.text = "Yesterday"
        else:
            label.text = selected.strftime("%a, %d %b")

    async def shift(days: int) -> None:
        state.shift_date(days)
        render()
        date_picker.value = state.get_date()
        await on_change()

    async def pick(value: str) -> None:
        if not value:
            return
        state.set_date(value)
        render()
        await on_change()

    with ui.row().classes("items-center gap-0"):
        ui.button(icon="chevron_left", on_click=lambda: shift(-1)).props(
            "flat dense round"
        ).classes("text-white")

        with ui.button(on_click=lambda: menu.open()).props("flat dense no-caps").classes(
            "text-white"
        ):
            label.move()
            with ui.menu() as menu:
                date_picker = ui.date(
                    value=state.get_date(), on_change=lambda e: pick(e.value)
                ).props("today-btn")

        ui.button(icon="chevron_right", on_click=lambda: shift(1)).props(
            "flat dense round"
        ).classes("text-white")

    render()


def _goals_dialog():
    goals = state.get_goals()
    with ui.dialog() as dialog, ui.card().classes("app-card w-80 gap-2 p-5"):
        ui.label("Daily goals").classes("text-lg font-semibold")
        ui.label("Used for the progress bars on the Today page.").classes("text-xs opacity-6")

        enabled = ui.switch("Show goal progress", value=state.goals_enabled())
        calories = ui.number("Calories", value=goals["calories"], min=0, step=50).props(
            "outlined dense"
        )
        carbs = ui.number("Carbs (g)", value=goals["carbs_g"], min=0, step=5).props("outlined dense")
        protein = ui.number("Protein (g)", value=goals["protein_g"], min=0, step=5).props(
            "outlined dense"
        )
        fats = ui.number("Fat (g)", value=goals["fats_g"], min=0, step=5).props("outlined dense")

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat no-caps")

            def save() -> None:
                state.set_goals_enabled(enabled.value)
                state.set_goals(
                    {
                        "calories": calories.value,
                        "carbs_g": carbs.value,
                        "protein_g": protein.value,
                        "fats_g": fats.value,
                    }
                )
                dialog.close()
                ui.navigate.reload()

            ui.button("Save", on_click=save).props("unelevated no-caps color=primary")
    return dialog


def layout(active: str, date_nav_handler=None):
    """Header, connection banner and the centred content column shared by every page."""
    theme.apply_theme()
    dark = ui.dark_mode(value=state.get_dark())

    with ui.header(elevated=False).classes(
        "items-center justify-between px-4 py-2 gap-2 flex-wrap"
    ).style(f"background: linear-gradient(90deg, {theme.PRIMARY}, {theme.SECONDARY});"):
        with ui.row().classes("items-center gap-1"):
            ui.icon("eco").classes("text-2xl text-white cursor-pointer").on(
                "click", lambda: ui.navigate.to("/")
            )
            _nav_buttons(active)

        if date_nav_handler is not None:
            _date_navigator(date_nav_handler)

        with ui.row().classes("items-center gap-0"):
            goals = _goals_dialog()
            ui.button(icon="tune", on_click=goals.open).props("flat dense round").classes(
                "text-white"
            ).tooltip("Daily goals")

            def toggle_dark() -> None:
                dark.toggle()
                state.set_dark(bool(dark.value))
                toggle.props(f'icon="{"light_mode" if dark.value else "dark_mode"}"')

            toggle = ui.button(
                icon="light_mode" if dark.value else "dark_mode", on_click=toggle_dark
            ).props("flat dense round").classes("text-white")

    _connection_banner()

    return ui.column().classes("w-full max-w-5xl mx-auto px-4 pb-24 pt-4 gap-6")


@ui.page("/")
def day_route() -> None:
    ui.page_title("Today - Food Intake")
    day_page(layout)


@ui.page("/foods")
def foods_route() -> None:
    ui.page_title("Foods - Food Intake")
    with layout("/foods"):
        foods_page()


@ui.page("/trends")
def trends_route() -> None:
    ui.page_title("Trends - Food Intake")
    with layout("/trends"):
        trends_page()


ui.run(
    title="Food Intake",
    # Localhost only: the app has no login. Set FOOD_INTAKE_HOST=0.0.0.0 to reach it from your phone.
    host=os.getenv("FOOD_INTAKE_HOST", "127.0.0.1"),
    port=8080,
    favicon="🍃",
    storage_secret=os.getenv("FOOD_INTAKE_SECRET", "foodapp_secret"),
    reconnect_timeout=10,
)
