"""Reusable presentation pieces shared by the Day, Foods and Trends pages."""

from collections.abc import Callable

from nicegui import ui

from theme import CALORIE_COLOR, MACRO_COLORS, MACRO_META


def macro_chips(macros: dict, show_calories: bool = True) -> None:
    macros = macros or {}
    with ui.row().classes("gap-1 flex-wrap items-center"):
        if show_calories:
            _chip(f"{round(macros.get('calories', 0)):g} kcal", CALORIE_COLOR)
        for key, label, field, unit in MACRO_META:
            _chip(f"{label} {round(macros.get(field, 0), 1):g}{unit}", MACRO_COLORS[key])


def _chip(text: str, color: str) -> None:
    ui.label(text).classes("macro-chip").style(f"background: {color}1F; color: {color};")


def stat_card(
    label: str,
    value: float,
    unit: str,
    color: str,
    goal: float | None = None,
    icon: str | None = None,
) -> None:
    with ui.card().classes("app-card flex-1 min-w-36 p-4 gap-1"):
        with ui.row().classes("items-center gap-2 w-full"):
            if icon:
                ui.icon(icon).classes("text-base").style(f"color: {color}")
            ui.label(label).classes("text-xs uppercase tracking-wide opacity-60 font-semibold")
        with ui.row().classes("items-baseline gap-1"):
            ui.label(f"{round(value, 1):g}").classes("text-2xl font-bold").style(f"color: {color}")
            ui.label(unit).classes("text-xs opacity-60")
        if goal:
            share = min(value / goal, 1.0) if goal else 0.0
            ui.linear_progress(value=share, show_value=False, size="6px").props(
                "rounded"
            ).style(f"color: {color}")
            ui.label(f"{round(share * 100)}% of {round(goal):g}{unit}").classes(
                "text-xs opacity-60"
            )


def macro_split_bar(macros: dict) -> None:
    """A single bar showing how the day's calories divide between the three macros."""
    macros = macros or {}
    parts = [
        ("carbs", (macros.get("carbs_g", 0) or 0) * 4),
        ("protein", (macros.get("protein_g", 0) or 0) * 4),
        ("fats", (macros.get("fats_g", 0) or 0) * 9),
    ]
    total = sum(value for _, value in parts)
    if total <= 0:
        return
    with ui.element("div").classes("w-full flex h-2 rounded-full overflow-hidden"):
        for key, value in parts:
            share = value / total * 100
            if share <= 0:
                continue
            ui.element("div").style(f"width: {share}%; background: {MACRO_COLORS[key]};").tooltip(
                f"{key.title()}: {round(share)}%"
            )


def empty_state(
    icon: str,
    title: str,
    subtitle: str = "",
    cta_label: str | None = None,
    on_cta: Callable | None = None,
) -> None:
    with ui.column().classes("w-full items-center justify-center py-10 gap-2 text-center"):
        ui.icon(icon).classes("text-5xl opacity-25")
        ui.label(title).classes("text-base font-semibold opacity-70")
        if subtitle:
            ui.label(subtitle).classes("text-sm opacity-50 max-w-xs")
        if cta_label and on_cta:
            ui.button(cta_label, on_click=on_cta).props("unelevated no-caps color=primary").classes(
                "mt-2"
            )


def skeleton_cards(count: int = 3) -> None:
    with ui.column().classes("w-full gap-2"):
        for _ in range(count):
            ui.skeleton().classes("w-full h-16 rounded-xl")


def section_title(text: str, icon: str | None = None, trailing: Callable | None = None) -> None:
    with ui.row().classes("w-full items-center justify-between mt-6 mb-2"):
        with ui.row().classes("items-center gap-2"):
            if icon:
                ui.icon(icon).classes("opacity-60")
            ui.label(text).classes("text-base font-semibold")
        if trailing:
            trailing()