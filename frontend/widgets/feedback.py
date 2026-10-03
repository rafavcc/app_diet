"""User-facing feedback: toasts, spinners and a shared confirmation dialog."""

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from nicegui import ui

from api.client import ApiError

log = logging.getLogger(__name__)


def notify_error(message: str) -> None:
    ui.notify(message, type="negative", position="top", multi_line=True, close_button="✕")


def notify_success(message: str) -> None:
    ui.notify(message, type="positive", position="top")


def notify_warning(message: str) -> None:
    ui.notify(message, type="warning", position="top")


@asynccontextmanager
async def guard(action: str, button: Any = None):
    """Run an API interaction with a busy button and a toast on failure.

    Yields a one-item list used as an 'ok' flag so callers can branch after the block.
    """
    outcome = [True]
    if button is not None:
        button.props("loading")
    try:
        yield outcome
    except ApiError as exc:
        outcome[0] = False
        notify_error(exc.message)
    except Exception:
        outcome[0] = False
        log.exception("Unexpected failure while %s", action)
        notify_error(f"Could not {action}. Check the logs for details.")
    finally:
        if button is not None:
            button.props(remove="loading")


def confirm_dialog(
    title: str,
    message: str,
    on_confirm: Callable[[Any], Any],
    confirm_label: str = "Delete",
    colour: str = "negative",
):
    """Build a reusable confirmation dialog; returns an 'open(context)' callable."""
    payload: dict = {}

    with ui.dialog() as dialog, ui.card().classes("w-80 rounded-xl"):
        ui.label(title).classes("text-lg font-semibold")
        body = ui.label(message).classes("text-sm opacity-70 mb-4")
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat no-caps")

            async def _confirm() -> None:
                dialog.close()
                await on_confirm(payload.get("context"))

            ui.button(confirm_label, on_click=_confirm).props(f"unelevated no-caps color={colour}")

    def open_dialog(context: Any = None, custom_message: str | None = None) -> None:
        payload["context"] = context
        body.text = custom_message or message
        dialog.open()

    return open_dialog