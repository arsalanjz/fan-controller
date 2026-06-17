from __future__ import annotations

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from src.core.fan import set_all_fans_auto, set_all_fans_max
from src.core.sensors import NbfcError


class TrayIcon(QSystemTrayIcon):
    def __init__(self, main_window, icon_path: str | None = None) -> None:
        if icon_path:
            icon = QIcon(icon_path)
        else:
            icon = main_window.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        super().__init__(icon, main_window)

        self.main_window = main_window
        self.setToolTip("Fan Controller")

        menu = QMenu()

        show_action = menu.addAction("Show")
        show_action.triggered.connect(self._show_window)

        menu.addSeparator()

        auto_action = menu.addAction("Auto All")
        auto_action.triggered.connect(self._on_auto_all)

        max_action = menu.addAction("Max All")
        max_action.triggered.connect(self._on_max_all)

        menu.addSeparator()

        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._on_quit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self) -> None:
        self.main_window.showNormal()
        self.main_window.activateWindow()
        self.main_window.raise_()

    def _on_auto_all(self) -> None:
        try:
            set_all_fans_auto()
        except NbfcError as exc:
            QMessageBox.critical(self.main_window, "Fan Control Error", str(exc))
            return
        self.main_window.set_all_fans_mode("auto")

    def _on_max_all(self) -> None:
        try:
            set_all_fans_max()
        except NbfcError as exc:
            QMessageBox.critical(self.main_window, "Fan Control Error", str(exc))
            return
        self.main_window.set_all_fans_mode("max")

    def _on_quit(self) -> None:
        QApplication.quit()