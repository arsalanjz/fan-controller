from __future__ import annotations

import sys

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.core.fan import (
    set_all_fans_auto,
    set_all_fans_max,
    set_fan_auto,
    set_fan_max,
    set_fan_speed,
)
from src.core.sensors import FanStatus, NbfcError, get_fan_statuses

REFRESH_INTERVAL_MS = 2000
SLIDER_APPLY_DELAY_MS = 200
SLIDER_ANIMATION_MS = 400
MAX_MODE_THRESHOLD = 99.0

LABEL_STYLE = "font-size: 16px;"

SLIDER_ENABLED_STYLE = ""
SLIDER_DISABLED_STYLE = """
QSlider::groove:horizontal {
    background: #3a3a3a;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #5a5a5a;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #4a4a4a;
    border-radius: 3px;
}
"""


def _detect_initial_mode(status: FanStatus) -> str:
    if status.auto_control_enabled:
        return "auto"
    if status.target_speed >= MAX_MODE_THRESHOLD:
        return "max"
    return "manual"


class FanWidget(QGroupBox):
    def __init__(self, fan_index: int, fan_name: str) -> None:
        super().__init__(fan_name)
        self.fan_index = fan_index
        self._initialized = False
        self._mode = "auto"
        self._last_auto_target: int | None = None

        layout = QVBoxLayout()

        self.temp_label = QLabel("Temperature: -- °C")
        self.speed_label = QLabel("Current speed: -- %")
        self.target_label = QLabel("Target speed: -- %")
        self.mode_label = QLabel("Mode: --")

        for label in (self.temp_label, self.speed_label, self.target_label, self.mode_label):
            label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(self.temp_label)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.target_label)
        layout.addWidget(self.mode_label)

        slider_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(50)
        self.slider.setEnabled(False)
        self.slider.setStyleSheet(SLIDER_DISABLED_STYLE)
        self.slider_value_label = QLabel("50%")
        self.slider_value_label.setStyleSheet(LABEL_STYLE)
        self.slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.slider_value_label)
        layout.addLayout(slider_layout)

        button_layout = QHBoxLayout()

        self.auto_button = QPushButton("Auto")
        self.manual_button = QPushButton("Manual")
        self.max_button = QPushButton("Max")

        self.auto_button.clicked.connect(self._on_auto_clicked)
        self.manual_button.clicked.connect(self._on_manual_clicked)
        self.max_button.clicked.connect(self._on_max_clicked)

        button_layout.addWidget(self.auto_button)
        button_layout.addWidget(self.manual_button)
        button_layout.addWidget(self.max_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self._slider_timer = QTimer(self)
        self._slider_timer.setSingleShot(True)
        self._slider_timer.timeout.connect(self._apply_slider_speed)

        self._slider_animation = QPropertyAnimation(self.slider, b"value")
        self._slider_animation.setDuration(SLIDER_ANIMATION_MS)
        self._slider_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def update_status(self, status: FanStatus) -> None:
        self.temp_label.setText(f"Temperature: {status.temperature:.1f} °C")
        self.speed_label.setText(f"Current speed: {status.current_speed:.1f} %")
        self.target_label.setText(f"Target speed: {status.target_speed:.1f} %")

        if not self._initialized:
            self._initialized = True
            self._mode = _detect_initial_mode(status)
            if self._mode == "auto":
                self._last_auto_target = int(round(status.target_speed))
            self.slider.blockSignals(True)
            self.slider.setValue(int(round(status.target_speed)))
            self.slider_value_label.setText(f"{int(round(status.target_speed))}%")
            self.slider.blockSignals(False)
            self._set_slider_enabled(self._mode == "manual")
            self.mode_label.setText(f"Mode: {self._mode.capitalize()}")
            return

        if self._mode == "auto":
            self._last_auto_target = int(round(status.target_speed))

        self.mode_label.setText(f"Mode: {self._mode.capitalize()}")

    def _set_slider_enabled(self, enabled: bool) -> None:
        self.slider.setEnabled(enabled)
        self.slider.setStyleSheet(SLIDER_ENABLED_STYLE if enabled else SLIDER_DISABLED_STYLE)

    def animate_slider_to(self, target_value: int) -> None:
        self.slider.blockSignals(True)
        self._slider_animation.stop()
        self._slider_animation.setStartValue(self.slider.value())
        self._slider_animation.setEndValue(target_value)
        self._slider_animation.finished.connect(self._on_animation_finished)
        self._slider_animation.valueChanged.connect(self._on_animation_value_changed)
        self._slider_animation.start()

    def _on_animation_value_changed(self, value) -> None:
        self.slider_value_label.setText(f"{int(value)}%")

    def _on_animation_finished(self) -> None:
        self.slider.blockSignals(False)
        try:
            self._slider_animation.finished.disconnect(self._on_animation_finished)
            self._slider_animation.valueChanged.disconnect(self._on_animation_value_changed)
        except TypeError:
            pass

    def _on_slider_changed(self, value: int) -> None:
        self.slider_value_label.setText(f"{value}%")
        self._slider_timer.start(SLIDER_APPLY_DELAY_MS)

    def _apply_slider_speed(self) -> None:
        if self._mode != "manual":
            return
        speed = self.slider.value()
        self._run_action(lambda: set_fan_speed(self.fan_index, speed))

    def set_mode(self, mode: str, animate_to: int | None = None) -> None:
        self._mode = mode
        self.mode_label.setText(f"Mode: {mode.capitalize()}")
        self._set_slider_enabled(mode == "manual")
        if animate_to is not None:
            self.animate_slider_to(animate_to)

    def _on_auto_clicked(self) -> None:
        target = self._last_auto_target if self._last_auto_target is not None else self.slider.value()
        self.set_mode("auto", animate_to=target)
        self._run_action(lambda: set_fan_auto(self.fan_index))

    def _on_manual_clicked(self) -> None:
        self.set_mode("manual")
        self._apply_slider_speed()

    def _on_max_clicked(self) -> None:
        self.set_mode("max", animate_to=100)
        self._run_action(lambda: set_fan_max(self.fan_index))

    def _run_action(self, action) -> None:
        try:
            action()
        except (NbfcError, ValueError) as exc:
            QMessageBox.critical(self, "Fan Control Error", str(exc))


class AllFansWidget(QGroupBox):
    def __init__(self) -> None:
        super().__init__("All Fans")

        layout = QHBoxLayout()

        self.auto_button = QPushButton("Auto")
        self.max_button = QPushButton("Max")

        self.auto_button.clicked.connect(self._on_auto_clicked)
        self.max_button.clicked.connect(self._on_max_clicked)

        layout.addWidget(self.auto_button)
        layout.addWidget(self.max_button)

        self.setLayout(layout)

        self.on_auto_applied = None
        self.on_max_applied = None

    def _on_auto_clicked(self) -> None:
        try:
            set_all_fans_auto()
        except NbfcError as exc:
            QMessageBox.critical(self, "Fan Control Error", str(exc))
            return
        if self.on_auto_applied:
            self.on_auto_applied()

    def _on_max_clicked(self) -> None:
        try:
            set_all_fans_max()
        except NbfcError as exc:
            QMessageBox.critical(self, "Fan Control Error", str(exc))
            return
        if self.on_max_applied:
            self.on_max_applied()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fan Controller")
        self.resize(700, 650)

        central_widget = QWidget()
        self.layout = QVBoxLayout()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

        self.fan_widgets: list[FanWidget] = []
        self._init_fan_widgets()

        self.all_fans_widget = AllFansWidget()
        self.all_fans_widget.on_auto_applied = self._on_all_fans_auto
        self.all_fans_widget.on_max_applied = self._on_all_fans_max
        self.layout.addWidget(self.all_fans_widget)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(REFRESH_INTERVAL_MS)

        self.refresh_status()

        self.tray_icon = None

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.tray_icon is not None and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
        else:
            event.accept()

    def _init_fan_widgets(self) -> None:
        try:
            statuses = get_fan_statuses()
        except NbfcError as exc:
            QMessageBox.critical(self, "Initialization Error", str(exc))
            statuses = []

        for index, status in enumerate(statuses):
            widget = FanWidget(index, status.name)
            self.fan_widgets.append(widget)
            self.layout.addWidget(widget)

    def refresh_status(self) -> None:
        try:
            statuses = get_fan_statuses()
        except NbfcError:
            return

        for widget, status in zip(self.fan_widgets, statuses):
            widget.update_status(status)

    def set_all_fans_mode(self, mode: str) -> None:
        for widget in self.fan_widgets:
            if mode == "auto":
                target = widget._last_auto_target if widget._last_auto_target is not None else widget.slider.value()
                widget.set_mode("auto", animate_to=target)
            elif mode == "max":
                widget.set_mode("max", animate_to=100)

    def _on_all_fans_auto(self) -> None:
        self.set_all_fans_mode("auto")

    def _on_all_fans_max(self) -> None:
        self.set_all_fans_mode("max")


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()

    from src.gui.tray import TrayIcon

    tray_icon = TrayIcon(window)
    tray_icon.show()
    window.tray_icon = tray_icon

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()