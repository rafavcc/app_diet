from nicegui import ui

PRIMARY = "#16A34A"
SECONDARY = "#0EA5E9"
ACCENT = "#F59E0B"

MACRO_COLORS = {
    "carbs": "#F59E0B",
    "protein": "#3B82F6",
    "fats": "#EF4444"
}

CALORIE_COLOR = "#16A34A"

MACRO_META = (
    ("carbs", "Carbs", "carbs_g", "g"),
    ("protein", "Protein", "protein_g", "g"),
    ("fats", "Fat", "fats_g", "g"),
)

MEAL_TYPES = ["breakfast", "morning_snack", "lunch", "afternoon_snack", "dinner", "other"]

MEAL_TYPE_META = {
    "breakfast": {"label": "Breakfast", "icon": "free_breakfast", "color": "#F59E0B"},
    "morning_snack": {"label": "Morning Snack", "icon": "bakery_dining", "color": "#FBBF24"},
    "lunch": {"label": "Lunch", "icon": "lunch_dining", "color": "#16A34A"},
    "afternoon_snack": {"label": "Afternoon Snack", "icon": "cookie", "color": "#F97316"},
    "dinner": {"label": "Dinner", "icon": "dinner_dining", "color": "#6366F1"},
    "other": {"label": "Other", "icon": "restaurant", "color": "#64748B"},
}


def meal_meta(meal_type: str | None) -> dict:
    return MEAL_TYPE_META.get(meal_type or "other", MEAL_TYPE_META["other"])

def apply_theme() -> None:
    ui.colors(
        primary=PRIMARY,
        secondary=SECONDARY,
        accent=ACCENT,
        positive=PRIMARY,
        negative="#DC2626",
        warning=ACCENT,
        info=SECONDARY,
        dark="#0F172A",
        dark_page="#0B1220",
    )
    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
    )
    ui.add_css("""
        body, .q-field, .q-btn { font-family: 'Inter', system-ui, sans-serif; }
        .nicegui-content { padding: 0; }
        .app-card {
            border-radius: 16px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, .06), 0 8px 24px -12px rgba(15, 23, 42, .18);
            border: 1px solid rgba(148, 163, 184, .18);
        }
        .body--dark .app-card {
            border-color: rgba(148, 163, 184, .16);
            box-shadow: 0 1px 2px rgba(0, 0, 0, .4);
        }
        .macro-chip {
            border-radius: 999px;
            padding: 2px 10px;
            font-size: .75rem;
            font-weight: 600;
            line-height: 1.4;
            white-space: nowrap;
        }
        .meal-card { border-left: 4px solid var(--meal-color, #64748B); }
        .app-table thead th { font-weight: 600; opacity: .7; }
        .app-table tbody tr:last-child td { font-weight: 700; }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-thumb { background: rgba(148, 163, 184, .45); border-radius: 999px; }
        ::-webkit-scrollbar-track { background: transparent; }
    """)

def chart_base(dark: bool) -> dict:
    """Shared ECharts options; the default palette is unreadable on a dark background."""
    text_color = "#E2E8F0" if dark else "#1E293B"
    muted = "rgba(148, 163, 184, .25)"
    return {
        "textStyle": {"color": text_color, "fontFamily": "Inter, sans-serif"},
        "backgroundColor": "transparent",
        "grid": {"left": 48, "right": 16, "top": 48, "bottom": 32, "containLabel": True},
        "legend": {"textStyle": {"color": text_color}, "top": 0},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "_axis": {
            "axisLine": {"lineStyle": {"color": muted}},
            "splitLine": {"lineStyle": {"color": muted}},
            "axisLabel": {"color": text_color},
        },
    }