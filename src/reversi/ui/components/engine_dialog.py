from __future__ import annotations

from typing import Callable, Dict, Optional

import flet as ft

from reversi.engine.metadata import (
    get_engine_metadata,
    list_engine_metadata,
    resolve_engine_key,
)


class EngineConfigDialog:
    """Encapsulates the engine configuration dialog UI."""

    def __init__(
        self,
        page_getter: Callable[[], Optional[ft.Page]],
        color_label_provider: Callable[[str], str],
        default_config_provider: Callable[[str], dict],
        on_save: Callable[[str, str, Dict[str, object]], None],
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._page_getter = page_getter
        self._color_label = color_label_provider
        self._default_config = default_config_provider
        self._on_save = on_save
        self._log = log_callback or (lambda msg: None)

        self._dialog: ft.AlertDialog | None = None
        self._context: dict | None = None
        self._params_column: ft.Column | None = None
        self._description: ft.Text | None = None

    def open(self, color: str, config: dict | None) -> None:
        page = self._page_getter()
        if not page:
            return
        if not config:
            config = self._default_config("minimax")
        selected_key = resolve_engine_key(config.get("engine_key", "minimax"))
        initial_params = dict(config.get("params", {}))

        dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(meta.key, meta.label) for meta in list_engine_metadata()],
            value=selected_key,
            dense=True,
            on_change=lambda e: self._handle_engine_choice_change(e.control.value),
        )

        self._context = {
            "color": color,
            "selected_key": selected_key,
            "param_controls": {},
            "param_meta": {},
        }
        self._description = ft.Text(
            get_engine_metadata(selected_key).description,
            size=12,
            italic=True,
            color="#555555",
        )
        self._params_column = ft.Column(
            controls=self._build_param_controls(selected_key, initial_params),
            spacing=8,
        )

        content = ft.Column(
            [
                ft.Text(f"{self._color_label(color)} Engine", size=18, weight=ft.FontWeight.BOLD),
                dropdown,
                self._description,
                ft.Divider(height=1),
                self._params_column,
            ],
            tight=True,
            spacing=12,
            width=360,
        )
        self._dialog = ft.AlertDialog(
            modal=True,
            content=content,
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog),
                ft.FilledButton("Save", on_click=self._save_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self._dialog not in page.overlay:
            page.overlay.append(self._dialog)
        self._dialog.open = True
        page.update()

    def _handle_engine_choice_change(self, engine_key: str) -> None:
        if not self._context:
            return
        canonical = resolve_engine_key(engine_key)
        self._context["selected_key"] = canonical
        defaults = self._default_config(canonical)["params"]
        if self._description:
            self._description.value = get_engine_metadata(canonical).description
            if self._description.page:
                self._description.update()
        if self._params_column:
            self._params_column.controls = self._build_param_controls(canonical, defaults)
            if self._params_column.page:
                self._params_column.update()

    def _build_param_controls(self, engine_key: str, current_values: dict) -> list[ft.Control]:
        meta = get_engine_metadata(engine_key)
        controls: list[ft.Control] = []
        if not self._context:
            return controls
        self._context["param_controls"] = {}
        self._context["param_meta"] = {}
        for param in meta.parameters:
            value = current_values.get(param.name, param.default)
            keyboard = ft.KeyboardType.NUMBER if param.type in ("int", "float") else ft.KeyboardType.TEXT
            field = ft.TextField(
                label=param.label,
                value=str(value),
                helper_text=param.help_text,
                keyboard_type=keyboard,
                dense=True,
            )
            self._context["param_controls"][param.name] = field
            self._context["param_meta"][param.name] = param
            controls.append(field)
        return controls

    def _close_dialog(self, e=None):  # type: ignore[override]
        page = self._page_getter()
        if self._dialog:
            self._dialog.open = False
            if page:
                page.update()
        self._dialog = None
        self._context = None
        self._params_column = None
        self._description = None

    def _save_dialog(self, e=None):  # type: ignore[override]
        if not self._context:
            self._close_dialog()
            return
        color = self._context.get("color")
        selected_raw = self._context.get("selected_key") or "minimax"
        selected_key = resolve_engine_key(selected_raw)
        params: dict[str, object] = {}
        for name, control in self._context.get("param_controls", {}).items():
            meta = self._context.get("param_meta", {}).get(name)
            if not meta:
                continue
            raw_value = control.value or ""
            try:
                if meta.type == "int":
                    parsed = int(float(raw_value))
                elif meta.type == "float":
                    parsed = float(raw_value)
                else:
                    parsed = raw_value
            except ValueError:
                control.error_text = "Invalid value"
                if control.page:
                    control.update()
                return
            if meta.min_value is not None and parsed < meta.min_value:
                control.error_text = f"Min {meta.min_value}"
                if control.page:
                    control.update()
                return
            if meta.max_value is not None and parsed > meta.max_value:
                control.error_text = f"Max {meta.max_value}"
                if control.page:
                    control.update()
                return
            control.error_text = None
            if control.page:
                control.update()
            params[name] = parsed
        if color:
            self._on_save(color, selected_key, params)
            self._log(
                f"Settings: {self._color_label(color)} engine -> {get_engine_metadata(selected_key).label}"
            )
        self._close_dialog()
