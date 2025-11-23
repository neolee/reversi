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
        on_save: Callable[[str, str, Dict[str, object], bool], None],
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
        self._engine_config_container: ft.Column | None = None

    def open(self, color: str, config: dict | None, is_human: bool = False) -> None:
        page = self._page_getter()
        if not page:
            return

        # Default config if None
        if not config:
            config = self._default_config("minimax")
            if is_human:
                config["enabled"] = False

        # Filter engines if is_human (analysis mode)
        available_engines = list_engine_metadata()
        if is_human:
            available_engines = [meta for meta in available_engines if meta.supports_analysis]

        selected_key = resolve_engine_key(config.get("engine_key", "minimax"))
        # Ensure selected key is valid for this mode
        if is_human and not get_engine_metadata(selected_key).supports_analysis:
            selected_key = "minimax"
            initial_params = self._default_config("minimax")["params"]
        else:
            initial_params = dict(config.get("params", {}))

        analysis_enabled = config.get("enabled", False) if is_human else True

        dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(meta.key, meta.label) for meta in available_engines],
            value=selected_key,
            dense=True,
            on_change=lambda e: self._handle_engine_choice_change(e.control.value),
        )

        self._context = {
            "color": color,
            "selected_key": selected_key,
            "param_controls": {},
            "param_meta": {},
            "is_human": is_human,
            "analysis_enabled": analysis_enabled,
            "think_delay_control": None,
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

        config_controls = [
            dropdown,
            self._description,
            ft.Divider(height=1),
        ]

        # Add think_delay control if not analysis mode
        if not is_human:
            current_delay = initial_params.get("think_delay", get_engine_metadata(selected_key).default_think_delay)
            think_delay_control = ft.TextField(
                label="Think Delay (s)",
                value=str(current_delay),
                keyboard_type=ft.KeyboardType.NUMBER,
                dense=True,
            )
            self._context["think_delay_control"] = think_delay_control
            config_controls.append(think_delay_control)

        config_controls.append(self._params_column)

        self._engine_config_container = ft.Column(
            config_controls,
            spacing=12,
            visible=analysis_enabled
        )

        dialog_content_controls: list[ft.Control] = [
            ft.Text(f"{self._color_label(color)} {'Analysis' if is_human else 'Engine'}", size=18, weight=ft.FontWeight.BOLD),
        ]

        enable_switch = None
        if is_human:
            enable_switch = ft.Switch(
                label="Enable Analysis Assist",
                value=analysis_enabled,
                on_change=self._handle_enable_change
            )
            self._context["enable_switch"] = enable_switch
            dialog_content_controls.append(enable_switch)

        if self._engine_config_container:
            dialog_content_controls.append(self._engine_config_container)

        content = ft.Column(
            dialog_content_controls,
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

    def _handle_enable_change(self, e):
        if self._engine_config_container:
            self._engine_config_container.visible = e.control.value
            self._engine_config_container.update()
        if self._context:
            self._context["analysis_enabled"] = e.control.value

    def _handle_engine_choice_change(self, engine_key: str) -> None:
        if not self._context:
            return
        canonical = resolve_engine_key(engine_key)
        self._context["selected_key"] = canonical
        defaults = self._default_config(canonical)["params"]
        meta = get_engine_metadata(canonical)

        if self._description:
            self._description.value = meta.description
            if self._description.page:
                self._description.update()

        # Update think_delay default if control exists
        think_delay_control = self._context.get("think_delay_control")
        if think_delay_control:
            think_delay_control.value = str(meta.default_think_delay)
            if think_delay_control.page:
                think_delay_control.update()

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

        is_analysis = self._context.get("is_human", False)

        for param in meta.parameters:
            if is_analysis and param.auto_managed_in_analysis:
                continue

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
        self._engine_config_container = None

    def _save_dialog(self, e=None):  # type: ignore[override]
        if not self._context:
            self._close_dialog()
            return
        color = self._context.get("color")
        selected_raw = self._context.get("selected_key") or "minimax"
        selected_key = resolve_engine_key(selected_raw)
        params: dict[str, object] = {}

        # Handle think_delay
        think_delay_control = self._context.get("think_delay_control")
        if think_delay_control:
            try:
                delay_val = float(think_delay_control.value or "0")
                if delay_val < 0:
                    think_delay_control.error_text = "Min 0.0"
                    if think_delay_control.page:
                        think_delay_control.update()
                    return
                params["think_delay"] = delay_val
            except ValueError:
                think_delay_control.error_text = "Invalid value"
                if think_delay_control.page:
                    think_delay_control.update()
                return

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
            enabled = self._context.get("analysis_enabled", True)
            self._on_save(color, selected_key, params, enabled)
            if self._context.get("is_human"):
                status = "Enabled" if enabled else "Disabled"
                self._log(f"Analysis: {self._color_label(color)} -> {status} ({get_engine_metadata(selected_key).label})")
            else:
                self._log(
                    f"Settings: {self._color_label(color)} engine -> {get_engine_metadata(selected_key).label}"
                )
        self._close_dialog()
