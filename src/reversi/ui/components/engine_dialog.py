from __future__ import annotations
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QFormLayout, QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt

from reversi.engine.metadata import (
    get_engine_metadata,
    list_engine_metadata,
    resolve_engine_key,
    EngineMetadata,
    EngineParamMetadata
)

class EngineConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.setMinimumWidth(480)

        self.color = "BLACK"
        self.is_human_mode = False
        self.current_config = {}

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 1. Header Information
        self.header_label = QLabel("Configure Player")
        self.header_label.setObjectName("dialog_header")
        layout.addWidget(self.header_label)

        # 2. Enabled Checkbox (for Analysis Assist)
        self.enabled_checkbox = QCheckBox("Enable AI Analysis Assist")
        self.enabled_checkbox.setToolTip("Show move evaluations while it's your turn")
        self.enabled_checkbox.toggled.connect(self._handle_enabled_toggled)
        layout.addWidget(self.enabled_checkbox)
        layout.addSpacing(10)

        # 3. Engine Selection Box
        self.engine_group = QGroupBox("Engine")
        engine_layout = QVBoxLayout(self.engine_group)
        engine_layout.setContentsMargins(15, 5, 15, 15)
        engine_layout.setSpacing(4)

        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumHeight(32)
        self.engine_combo.currentTextChanged.connect(self._handle_engine_changed)
        engine_layout.addWidget(self.engine_combo)

        self.description_text = QLabel()
        self.description_text.setWordWrap(True)
        self.description_text.setObjectName("info_label")
        engine_layout.addWidget(self.description_text)

        layout.addWidget(self.engine_group)

        # 4. Parameters Area
        self.params_group = QGroupBox("Parameters")
        self.params_form = QFormLayout(self.params_group)
        self.params_form.setContentsMargins(15, 5, 15, 15)
        self.params_form.setSpacing(4)
        self.params_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.params_group)

        self.param_controls = {}

        # 5. Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("primary_button")
        self.btn_save.setFixedSize(100, 24)
        self.btn_save.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(100, 24)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def load_config(self, color: str, is_human: bool, config: Dict[str, Any]):
        self.color = color
        self.is_human_mode = is_human
        self.current_config = config

        self.header_label.setText(f"Configure {color} ({'Human' if is_human else 'Engine'})")

        # Show/Hide enabled checkbox
        self.enabled_checkbox.setVisible(is_human)
        if is_human:
            self.enabled_checkbox.setChecked(config.get("enabled", False))
            self.params_group.setVisible(self.enabled_checkbox.isChecked())
            self.engine_group.setVisible(self.enabled_checkbox.isChecked())
        else:
            self.params_group.setVisible(True)
            self.engine_group.setVisible(True)

        # Filter engines
        all_meta = list_engine_metadata()
        if is_human:
            available = [m for m in all_meta if m.supports_analysis]
        else:
            available = all_meta

        self.engine_combo.clear()
        for meta in available:
            self.engine_combo.addItem(meta.label, meta.key)

        # Select current engine
        current_key = resolve_engine_key(config.get("key") or config.get("engine_key") or "minimax")
        idx = self.engine_combo.findData(current_key)
        if idx >= 0:
            self.engine_combo.setCurrentIndex(idx)
        else:
            self.engine_combo.setCurrentIndex(0)

        self._refresh_params()
        self.adjustSize()

    def _handle_enabled_toggled(self, checked):
        self.params_group.setVisible(checked)
        self.engine_group.setVisible(checked)
        # Force the dialog to shrink back to its smallest necessary size
        self.adjustSize()

    def _handle_engine_changed(self):
        self._refresh_params()

    def _refresh_params(self):
        # Clear existing form
        while self.params_form.rowCount() > 0:
            self.params_form.removeRow(0)
        self.param_controls = {}

        engine_key = self.engine_combo.currentData()
        if not engine_key:
            return

        meta = get_engine_metadata(engine_key)
        self.description_text.setText(meta.description)

        params = self.current_config.get("params", {})

        # Build form
        for p in meta.parameters:
            # Skip if auto-managed in analysis and we are in human (analysis) mode
            if self.is_human_mode and p.auto_managed_in_analysis:
                continue

            control = self._create_param_control(p, params.get(p.name, p.default))
            self.param_controls[p.name] = control
            self.params_form.addRow(p.label + ":", control)

        # Add Think Delay if not in analysis mode
        if not self.is_human_mode:
            delay = params.get("think_delay", meta.default_think_delay)
            delay_spin = QDoubleSpinBox()
            delay_spin.setRange(0.0, 5.0)
            delay_spin.setSingleStep(0.05)
            delay_spin.setValue(delay)
            self.param_controls["think_delay"] = delay_spin
            self.params_form.addRow("Think Delay (s):", delay_spin)

    def _create_param_control(self, meta: EngineParamMetadata, current_val: Any):
        control = None
        if meta.type == "int":
            spin = QSpinBox()
            spin.setRange(int(meta.min_value or 0), int(meta.max_value or 100))
            spin.setValue(int(current_val))
            control = spin
        elif meta.type == "float":
            spin = QDoubleSpinBox()
            spin.setRange(float(meta.min_value or 0.0), float(meta.max_value or 1.0))
            spin.setSingleStep(meta.step or 0.1)
            spin.setValue(float(current_val))
            control = spin
        elif meta.type == "choice" and meta.choices:
            combo = QComboBox()
            for val, label in meta.choices:
                combo.addItem(label, val)
                if val == str(current_val):
                    combo.setCurrentIndex(combo.count() - 1)
            control = combo
        else:
            control = QLabel(str(current_val))

        if meta.help_text:
            control.setToolTip(meta.help_text)

        return control

    def get_config(self) -> Dict[str, Any]:
        params = {}
        for name, ctrl in self.param_controls.items():
            if isinstance(ctrl, QSpinBox):
                params[name] = ctrl.value()
            elif isinstance(ctrl, QDoubleSpinBox):
                params[name] = ctrl.value()
            elif isinstance(ctrl, QComboBox):
                params[name] = ctrl.currentData()

        config = {
            "key": self.engine_combo.currentData(),
            "params": params
        }
        if self.is_human_mode:
            config["enabled"] = self.enabled_checkbox.isChecked()
            # For backward compatibility with Flet version's key names if needed
            config["engine_key"] = config["key"]

        return config
