"""System tray icon and context menu management."""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app.i18n import t


class TrayManager:
    """Manage the system tray icon, quick profile switching, and background notifications."""

    def __init__(self, main_window, app_icon, profiles, lang="vi"):
        self.main_window = main_window
        self.lang = lang
        self.tray_icon = QSystemTrayIcon(app_icon, main_window)
        self.tray_icon.setToolTip("Google Multi-Account Hub")
        self.rebuild_menu(profiles, lang)
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()

    def rebuild_menu(self, profiles, lang):
        """Rebuild tray context menu when profiles or UI language change."""
        self.lang = lang
        tray_menu = QMenu()
        show_action = QAction(t(lang, "tray_open"), self.main_window)
        show_action.triggered.connect(self.restore_window)
        tray_menu.addAction(show_action)

        switch_prefix = t(lang, "tray_switch")
        for idx, p_cfg in enumerate(profiles):
            p_action = QAction(f"{switch_prefix} {p_cfg['name']}", self.main_window)
            p_action.triggered.connect(lambda checked, i=idx: self.quick_switch(i))
            tray_menu.addAction(p_action)

        tray_menu.addSeparator()
        freeze_action = QAction(t(lang, "tray_freeze"), self.main_window)
        freeze_action.triggered.connect(self.main_window.freeze_all_now)
        tray_menu.addAction(freeze_action)

        quit_action = QAction(t(lang, "tray_quit"), self.main_window)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)

    def _on_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.restore_window()

    def quick_switch(self, profile_idx):
        """Restore the main window and switch to the selected account profile."""
        self.restore_window()
        self.main_window.switch_profile(profile_idx)

    def restore_window(self):
        """Show and bring the main window to the foreground."""
        self.main_window.showNormal()
        self.main_window.activateWindow()
        self.main_window.raise_()

    def notify_minimized(self):
        """Display a tray notification when the window is hidden to background."""
        self.tray_icon.showMessage(
            t(self.lang, "tray_bg_title"),
            t(self.lang, "tray_bg_msg"),
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def quit_application(self):
        """Hide the tray icon and terminate the application."""
        self.tray_icon.hide()
        QApplication.quit()
