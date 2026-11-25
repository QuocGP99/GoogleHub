"""Main application window with Apple-style collapsible sidebar, settings, and workspaces."""

from PyQt6.QtCore import QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import GOOGLE_SERVICES
from app.core.settings_manager import load_settings, save_settings
from app.i18n import t
from app.ui.settings_dialog import SettingsDialog
from app.ui.theme import create_default_icon, get_dark_theme
from app.ui.tray_manager import TrayManager
from app.web.workspace import ProfileWorkspace

SIDEBAR_EXPANDED_WIDTH = 224
SIDEBAR_COLLAPSED_WIDTH = 66

SERVICE_ICONS = {
    "Gemini": "✦",
    "Gmail": "✉",
    "Drive": "▲",
    "YouTube": "▶",
    "Photos": "✿",
    "Maps": "⌖",
    "Dịch": "文",
    "Docs": "≡",
    "Sheets": "⊞",
    "Slides": "◫",
    "Calendar": "◷",
    "Meet": "◉",
}
CHROME_ICON = "◎"


class GoogleHubApp(QMainWindow):
    """Main window hosting the collapsible Apple-style sidebar and per-profile workspaces."""

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.profiles = self.settings["profiles"]
        self.lang = self.settings["language"]

        self.setWindowTitle("Google Workspace Multi-Account Hub")
        self.resize(1460, 920)
        self.setStyleSheet(get_dark_theme())

        self.app_icon = create_default_icon()
        self.setWindowIcon(self.app_icon)

        self.workspaces = []
        self.current_profile_idx = 0
        self.current_service_idx = 0
        self.service_buttons = []
        self.profile_buttons = []
        self.sidebar_collapsed = False
        self._sidebar_anim = None

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.workspace_stack = QStackedWidget()
        self.sidebar = self._build_sidebar()

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.workspace_stack)

        self.tray_manager = TrayManager(self, self.app_icon, self.profiles, self.lang)
        self.hibernation_timer = QTimer(self)
        self.hibernation_timer.timeout.connect(self.run_auto_hibernation)
        self.hibernation_timer.start(60 * 1000)

        self.switch_profile(0)

    def _build_sidebar(self):
        """Construct the collapsible left sidebar with profile switcher and service tabs."""
        sidebar = QFrame()
        sidebar.setMinimumWidth(SIDEBAR_EXPANDED_WIDTH)
        sidebar.setMaximumWidth(SIDEBAR_EXPANDED_WIDTH)
        sidebar.setObjectName("Sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(2, 0, 2, 4)
        self.title_label = QLabel("GOOGLE HUB")
        self.title_label.setObjectName("AppTitle")
        header_row.addWidget(self.title_label)
        header_row.addStretch()

        self.collapse_btn = QPushButton("‹")
        self.collapse_btn.setObjectName("CollapseBtn")
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setToolTip(t(self.lang, "collapse_tooltip"))
        self.collapse_btn.clicked.connect(self.toggle_sidebar)
        header_row.addWidget(self.collapse_btn)
        layout.addLayout(header_row)

        self.profile_section_label = QLabel(t(self.lang, "accounts_section"))
        self.profile_section_label.setObjectName("SectionLabel")
        layout.addWidget(self.profile_section_label)

        self.profile_btn_container = QVBoxLayout()
        self.profile_btn_container.setContentsMargins(0, 0, 0, 0)
        self.profile_btn_container.setSpacing(4)
        layout.addLayout(self.profile_btn_container)
        self._rebuild_profiles_ui()

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("Divider")
        layout.addWidget(line)

        self.service_section_label = QLabel(t(self.lang, "apps_section"))
        self.service_section_label.setObjectName("SectionLabel")
        layout.addWidget(self.service_section_label)

        for s_idx, (name, _) in enumerate(GOOGLE_SERVICES):
            icon = SERVICE_ICONS.get(name, "•")
            btn = QPushButton(f"{icon}  {name}")
            btn.setCheckable(True)
            btn.setToolTip(name)
            btn.clicked.connect(lambda checked, idx=s_idx: self.switch_service(idx))
            layout.addWidget(btn)
            self.service_buttons.append(btn)

        chrome_idx = len(GOOGLE_SERVICES)
        btn_chrome = QPushButton(f"{CHROME_ICON}  Google Chrome")
        btn_chrome.setCheckable(True)
        btn_chrome.setToolTip("Google Chrome")
        btn_chrome.clicked.connect(lambda checked, idx=chrome_idx: self.switch_service(idx))
        layout.addWidget(btn_chrome)
        self.service_buttons.append(btn_chrome)

        layout.addStretch()

        self.btn_auth = QPushButton(f"🔑  {t(self.lang, 'auth_btn')}")
        self.btn_auth.setObjectName("ActionBtn")
        self.btn_auth.setToolTip(t(self.lang, "auth_tooltip"))
        self.btn_auth.clicked.connect(self.trigger_profile_auth)
        layout.addWidget(self.btn_auth)

        self.btn_freeze_all = QPushButton(f"❄  {t(self.lang, 'freeze_btn')}")
        self.btn_freeze_all.setObjectName("ActionBtn")
        self.btn_freeze_all.setToolTip(t(self.lang, "freeze_tooltip"))
        self.btn_freeze_all.clicked.connect(self.freeze_all_now)
        layout.addWidget(self.btn_freeze_all)

        self.btn_settings = QPushButton(f"⚙  {t(self.lang, 'settings_btn')}")
        self.btn_settings.setObjectName("ActionBtn")
        self.btn_settings.setToolTip(t(self.lang, "settings_tooltip"))
        self.btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.btn_settings)

        return sidebar

    def _rebuild_profiles_ui(self):
        """Sync profile workspaces and sidebar buttons with self.profiles."""
        existing_ws = {ws.profile_id: ws for ws in self.workspaces}
        for btn in self.profile_buttons:
            self.profile_btn_container.removeWidget(btn)
            btn.deleteLater()
        self.profile_buttons.clear()

        while self.workspace_stack.count():
            self.workspace_stack.removeWidget(self.workspace_stack.widget(0))

        new_workspaces = []
        for p_idx, p_cfg in enumerate(self.profiles):
            pid = p_cfg["id"]
            if pid in existing_ws:
                ws = existing_ws[pid]
                ws.profile_name = p_cfg["name"]
                ws.accent_color = p_cfg["color"]
            else:
                ws = ProfileWorkspace(p_cfg, self)
            new_workspaces.append(ws)
            self.workspace_stack.addWidget(ws)

            p_btn = QPushButton(
                p_cfg["name"].split()[0] if self.sidebar_collapsed else p_cfg["name"]
            )
            p_btn.setCheckable(True)
            p_btn.setObjectName("ProfileBtn")
            p_btn.setToolTip(p_cfg["name"])
            self._set_btn_collapsed_prop(p_btn)
            p_btn.clicked.connect(lambda checked, idx=p_idx: self.switch_profile(idx))
            self.profile_btn_container.addWidget(p_btn)
            self.profile_buttons.append(p_btn)

        for pid, ws in existing_ws.items():
            if pid not in {p["id"] for p in self.profiles}:
                ws.deleteLater()

        self.workspaces = new_workspaces

    def open_settings(self):
        """Open SettingsDialog and apply changes immediately on save."""
        dialog = SettingsDialog(self.settings, self)
        if not dialog.exec():
            return

        self.settings = dialog.get_settings()
        save_settings(self.settings)

        self.lang = self.settings["language"]
        self.profiles = self.settings["profiles"]

        active_pid = (
            self.workspaces[self.current_profile_idx].profile_id
            if 0 <= self.current_profile_idx < len(self.workspaces)
            else None
        )
        self._rebuild_profiles_ui()
        self.tray_manager.rebuild_menu(self.profiles, self.lang)
        self._apply_collapsed_button_states()

        next_idx = next(
            (i for i, p in enumerate(self.profiles) if p["id"] == active_pid),
            0,
        )
        self.switch_profile(next_idx)

    def toggle_sidebar(self):
        """Animate the sidebar between expanded and compact icon-only widths."""
        self.sidebar_collapsed = not self.sidebar_collapsed
        start_w = self.sidebar.width()
        end_w = SIDEBAR_COLLAPSED_WIDTH if self.sidebar_collapsed else SIDEBAR_EXPANDED_WIDTH

        self.collapse_btn.setText("›" if self.sidebar_collapsed else "‹")
        self.title_label.setVisible(not self.sidebar_collapsed)
        self.profile_section_label.setVisible(not self.sidebar_collapsed)
        self.service_section_label.setVisible(not self.sidebar_collapsed)

        self._apply_collapsed_button_states()

        anim_min = QPropertyAnimation(self.sidebar, b"minimumWidth")
        anim_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        for anim in (anim_min, anim_max):
            anim.setDuration(180)
            anim.setStartValue(start_w)
            anim.setEndValue(end_w)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._sidebar_anim = QParallelAnimationGroup(self)
        self._sidebar_anim.addAnimation(anim_min)
        self._sidebar_anim.addAnimation(anim_max)
        self._sidebar_anim.start()

    def _set_btn_collapsed_prop(self, btn):
        """Update dynamic QSS collapsed property and repolish widget."""
        btn.setProperty("collapsed", self.sidebar_collapsed)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def _apply_collapsed_button_states(self):
        """Update button labels, localization, and alignment for current sidebar mode."""
        self.collapse_btn.setToolTip(
            t(self.lang, "expand_tooltip" if self.sidebar_collapsed else "collapse_tooltip")
        )
        self.profile_section_label.setText(t(self.lang, "accounts_section"))
        self.service_section_label.setText(t(self.lang, "apps_section"))

        for i, btn in enumerate(self.profile_buttons):
            full_name = self.profiles[i]["name"]
            btn.setText(full_name.split()[0] if self.sidebar_collapsed else full_name)
            btn.setToolTip(full_name)
            self._set_btn_collapsed_prop(btn)

        self.btn_auth.setText("🔑" if self.sidebar_collapsed else f"🔑  {t(self.lang, 'auth_btn')}")
        self.btn_auth.setToolTip(t(self.lang, "auth_tooltip"))
        self._set_btn_collapsed_prop(self.btn_auth)

        self.btn_freeze_all.setText(
            "❄" if self.sidebar_collapsed else f"❄  {t(self.lang, 'freeze_btn')}"
        )
        self.btn_freeze_all.setToolTip(t(self.lang, "freeze_tooltip"))
        self._set_btn_collapsed_prop(self.btn_freeze_all)

        self.btn_settings.setText(
            "⚙" if self.sidebar_collapsed else f"⚙  {t(self.lang, 'settings_btn')}"
        )
        self.btn_settings.setToolTip(t(self.lang, "settings_tooltip"))
        self._set_btn_collapsed_prop(self.btn_settings)

        self.refresh_sidebar_labels()

    def trigger_profile_auth(self):
        """Open standalone browser sign-in for the currently active profile."""
        if 0 <= self.current_profile_idx < len(self.workspaces):
            self.workspaces[self.current_profile_idx].handle_google_auth_required(
                "https://accounts.google.com"
            )

    def switch_profile(self, profile_idx):
        """Switch active account workspace and update sidebar styling."""
        self.current_profile_idx = profile_idx
        active_ws = self.workspaces[profile_idx]

        for i, btn in enumerate(self.profile_buttons):
            is_selected = i == profile_idx
            btn.setChecked(is_selected)
            if is_selected:
                color = self.profiles[i].get("color", "#0A84FF")
                btn.setStyleSheet(
                    f"background-color: {color}; color: #FFFFFF; "
                    f"border-color: {color}; font-weight: 600;"
                )
            else:
                btn.setStyleSheet("")

        self.workspace_stack.setCurrentIndex(profile_idx)
        self.switch_service(self.current_service_idx)
        self.setWindowTitle(f"Google Hub — {active_ws.profile_name}")

    def switch_service(self, service_idx):
        """Switch active service tab within the current profile workspace."""
        self.current_service_idx = service_idx
        active_ws = self.workspaces[self.current_profile_idx]
        active_ws.open_service(service_idx)
        self.refresh_sidebar_labels()

    def refresh_sidebar_labels(self):
        """Update active button state and ❄ frozen indicators for the active profile."""
        active_ws = self.workspaces[self.current_profile_idx]
        for idx, btn in enumerate(self.service_buttons):
            btn.setChecked(idx == self.current_service_idx)
            self._set_btn_collapsed_prop(btn)

            if idx < len(GOOGLE_SERVICES):
                base_name = GOOGLE_SERVICES[idx][0]
                icon = SERVICE_ICONS.get(base_name, "•")
                is_frozen = idx in active_ws.frozen_tabs
                if self.sidebar_collapsed:
                    btn.setText(icon)
                    btn.setToolTip(
                        f"{base_name}{t(self.lang, 'frozen_suffix')}" if is_frozen else base_name
                    )
                else:
                    btn.setText(f"{icon}  {base_name}  ❄" if is_frozen else f"{icon}  {base_name}")
                    btn.setToolTip(base_name)
            else:
                btn.setText(CHROME_ICON if self.sidebar_collapsed else f"{CHROME_ICON}  Google Chrome")
                btn.setToolTip("Google Chrome")

    def run_auto_hibernation(self):
        """Periodically freeze idle tabs across all workspaces."""
        idle_secs = self.settings.get("idle_timeout_minutes", 15) * 60
        for idx, ws in enumerate(self.workspaces):
            ws.freeze_idle_tabs(
                is_active_workspace=(idx == self.current_profile_idx),
                idle_timeout=idle_secs,
            )
        self.refresh_sidebar_labels()

    def freeze_all_now(self):
        """Immediately freeze all non-visible tabs across all workspaces."""
        for idx, ws in enumerate(self.workspaces):
            ws.freeze_all_now(is_active_workspace=(idx == self.current_profile_idx))
        self.refresh_sidebar_labels()

    def closeEvent(self, event):
        """Minimize to system tray or quit based on user settings."""
        if self.settings.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
            self.tray_manager.notify_minimized()
        else:
            self.tray_manager.quit_application()
            event.accept()
