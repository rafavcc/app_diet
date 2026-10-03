import datetime

from nicegui import ui

import state
import theme
from api import client
from api.runner import call
from theme import CALORIE_COLOR, MACRO_COLORS
from widgets.components import empty_state, section_title, stat_card
from widgets.feedback import guard

RANGES = {"7": "7 days", "30": "30 days", "90": "90 days"}


def trends_page() -> None:
    cache = {"days": 30, "summary": None}

    async def reload() -> None:
        end = datetime.date.today()
        start = end - datetime.timedelta(days=cache["days"] - 1)
        async with guard("load your trends") as ok:
            cache["summary"] = await call(
                client.get_range_summary, start.isoformat(), end.isoformat()
            )
        if not ok[0]:
            cache["summary"] = None
        content.refresh()

    with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"):
        ui.label("Trends").classes("text-xl font-bold")

        async def on_range(event) -> None:
            cache["days"] = int(event.value)
            await reload()

        ui.toggle(RANGES, value="30").props("dense no-caps").on_value_change(on_range)

    @ui.refreshable
    def content() -> None:
        summary = cache["summary"]
        if not summary:
            empty_state("insights", "No data yet", "Log some meals and your trends appear here.")
            return
        if not summary.get("logged_days"):
            empty_state(
                "event_busy",
                "Nothing logged in this period",
                "Try a wider range, or start logging meals on the Today page.",
            )
            return

        days = summary["days"]
        averages = summary["averages"]
        goals = state.get_goals()
        show_goals = state.goals_enabled()

        section_title("Daily average", "functions")
        with ui.row().classes("w-full gap-2 flex-wrap"):
            stat_card(
                "Calories",
                averages.get("calories", 0),
                "kcal",
                CALORIE_COLOR,
                goal=goals["calories"] if show_goals else None,
                icon="local_fire_department",
            )
            for key, label, field, unit in theme.MACRO_META:
                stat_card(
                    label,
                    averages.get(field, 0),
                    unit,
                    MACRO_COLORS[key],
                    goal=goals[field] if show_goals else None,
                )

        logged = [day for day in days if day["entry_count"]]
        best = max(logged, key=lambda d: d["macros"]["calories"])
        lightest = min(logged, key=lambda d: d["macros"]["calories"])

        with ui.row().classes("w-full gap-2 flex-wrap mt-2"):
            _callout("Highest day", best, "trending_up", MACRO_COLORS["fats"])
            _callout("Lightest day", lightest, "trending_down", MACRO_COLORS["protein"])
            with ui.card().classes("app-card flex-1 min-w-36 p-4 gap-1"):
                ui.label("Days logged").classes(
                    "text-xs uppercase tracking-wide opacity-60 font-semibold"
                )
                ui.label(f"{summary['logged_days']} / {len(days)}").classes(
                    "text-2xl font-bold"
                ).style(f"color: {CALORIE_COLOR}")

        dark = state.get_dark()
        base = theme.chart_base(dark)
        axis = base.pop("_axis")
        labels = [datetime.date.fromisoformat(day["date"]).strftime("%d %b") for day in days]

        section_title("Calories per day", "local_fire_department")
        with ui.card().classes("app-card w-full p-2"):
            series = [{
                "name": "Calories",
                "type": "bar",
                "itemStyle": {"color": CALORIE_COLOR, "borderRadius": [4, 4, 0, 0]},
                "data": [round(day["macros"]["calories"], 1) for day in days],
            }]
            if show_goals:
                series[0]["markLine"] = {
                    "silent": True,
                    "symbol": "none",
                    "lineStyle": {"color": MACRO_COLORS["fats"], "type": "dashed"},
                    "data": [{"yAxis": goals["calories"], "name": "Goal"}],
                }
            ui.echart({
                **base,
                "xAxis": {"type": "category", "data": labels, **axis},
                "yAxis": {"type": "value", **axis},
                "series": series,
            }).classes("w-full h-72")

        section_title("Macros over time", "stacked_line_chart")
        with ui.card().classes("app-card w-full p-2"):
            ui.echart({
                **base,
                "xAxis": {"type": "category", "boundaryGap": False, "data": labels, **axis},
                "yAxis": {"type": "value", **axis},
                "series": [
                    {
                        "name": label,
                        "type": "line",
                        "smooth": True,
                        "stack": "macros",
                        "areaStyle": {"opacity": 0.25},
                        "showSymbol": False,
                        "itemStyle": {"color": MACRO_COLORS[key]},
                        "lineStyle": {"color": MACRO_COLORS[key]},
                        "data": [round(day["macros"][field], 1) for day in days],
                    }
                    for key, label, field, _unit in theme.MACRO_META
                ],
            }).classes("w-full h-72")

    def _callout(title: str, day: dict, icon: str, colour: str) -> None:
        with ui.card().classes("app-card flex-1 min-w-36 p-4 gap-1"):
            with ui.row().classes("items-center gap-2"):
                ui.icon(icon).style(f"color: {colour}")
                ui.label(title).classes("text-xs uppercase tracking-wide opacity-60 font-semibold")
            ui.label(f"{round(day['macros']['calories']):g} kcal").classes(
                "text-2xl font-bold"
            ).style(f"color: {colour}")
            ui.label(datetime.date.fromisoformat(day["date"]).strftime("%a, %d %b")).classes(
                "text-xs opacity-60"
            )

    content()
    ui.timer(0.05, reload, once=True)