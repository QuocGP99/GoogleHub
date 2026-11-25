"""Isolated per-account workspace managing WebEngine tabs, hibernation, and Chrome embedding."""

import os
import subprocess
import time

import win32gui
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QWindow
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from app.config import (
    GOOGLE_SERVICES,
    IDLE_TIMEOUT_SECONDS,
    NEVER_FREEZE_TABS,
    USER_AGENT,
    get_profiles_root,
)
from app.core.browser_finder import find_standalone_browser
from app.core.cookie_sync import extract_and_inject_cookies
from app.web.auth_templates import get_auth_waiting_html
from app.web.web_page import CustomWebPage


class ProfileWorkspace(QWidget):
    """Independent workspace for one Google account containing 12 Web Apps + 1 embedded browser."""

    def __init__(self, profile_cfg, parent=None):
        super().__init__(parent)
        self.profile_id = profile_cfg["id"]
        self.profile_name = profile_cfg["name"]
        self.accent_color = profile_cfg["color"]

        self.profile_dir = os.path.join(get_profiles_root(), self.profile_id)
        os.makedirs(self.profile_dir, exist_ok=True)

        self.web_profile = QWebEngineProfile(f"Profile_{self.profile_id}", self)
        self.web_profile.setPersistentStoragePath(os.path.join(self.profile_dir, "storage"))
        self.web_profile.setCachePath(os.path.join(self.profile_dir, "cache"))
        self.web_profile.setHttpUserAgent(USER_AGENT)
        self._configure_web_settings()

        self.web_views = {}          # {tab_idx: QWebEngineView}
        self.last_active_time = {}   # {tab_idx: timestamp}
        self.frozen_tabs = set()     # Set of frozen tab indices
        self.current_tab_index = 0
        self.chrome_embedded = False
        self.last_auth_launch = 0
        self.auth_poll_timer = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        for _ in GOOGLE_SERVICES:
            self.stack.addWidget(QWidget())

        self.chrome_idx = len(GOOGLE_SERVICES)
        self.chrome_container = QWidget()
        self.stack.addWidget(self.chrome_container)

    def _configure_web_settings(self):
        """Enable WebEngine attributes required by Google Workspace apps."""
        settings = self.web_profile.settings()
        for attr in (
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard,
            QWebEngineSettings.WebAttribute.LocalStorageEnabled,
            QWebEngineSettings.WebAttribute.WebGLEnabled,
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,
            QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled,
            QWebEngineSettings.WebAttribute.PluginsEnabled,
        ):
            settings.setAttribute(attr, True)

    def open_service(self, tab_idx):
        """Switch to or lazily initialize the requested service tab."""
        self.current_tab_index = tab_idx
        self.last_active_time[tab_idx] = time.time()

        if tab_idx == self.chrome_idx:
            self.open_embedded_chrome()
            self.stack.setCurrentIndex(self.chrome_idx)
            return

        url = GOOGLE_SERVICES[tab_idx][1]
        if tab_idx not in self.web_views:
            view = QWebEngineView()
            page = CustomWebPage(self.web_profile, self, view)
            view.setPage(page)
            view.load(QUrl(url))

            old_widget = self.stack.widget(tab_idx)
            self.stack.removeWidget(old_widget)
            self.stack.insertWidget(tab_idx, view)
            self.web_views[tab_idx] = view
        elif tab_idx in self.frozen_tabs:
            self.web_views[tab_idx].page().setLifecycleState(
                QWebEnginePage.LifecycleState.Active
            )
            self.frozen_tabs.remove(tab_idx)

        self.stack.setCurrentIndex(tab_idx)

    def handle_google_auth_required(self, auth_url):
        """Break redirect loops with a waiting page and launch an external auth window."""
        now = time.time()
        if (now - self.last_auth_launch) < 5:
            return
        self.last_auth_launch = now

        if self.current_tab_index in self.web_views:
            service_name = GOOGLE_SERVICES[self.current_tab_index][0]
            self.web_views[self.current_tab_index].setHtml(
                get_auth_waiting_html(service_name)
            )

        self.launch_auth_browser(auth_url)

    def launch_auth_browser(self, target_url="https://accounts.google.com"):
        """Launch a standalone Chrome/Edge app window for safe Google sign-in."""
        browser_exe = find_standalone_browser()
        if not browser_exe:
            print("Không tìm thấy trình duyệt độc lập (Chrome/Edge) trên hệ thống.")
            return

        login_dir = os.path.join(self.profile_dir, "browser_login")
        os.makedirs(login_dir, exist_ok=True)

        cmd = [
            browser_exe,
            f"--user-data-dir={login_dir}",
            f"--app={target_url}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        subprocess.Popen(cmd)
        self._start_auth_completion_watcher()

    def _start_auth_completion_watcher(self):
        """Poll for the post-login Google Account window to auto-close and sync cookies."""
        if self.auth_poll_timer is None:
            self.auth_poll_timer = QTimer(self)
            self.auth_poll_timer.setInterval(1500)
            self.auth_poll_timer.timeout.connect(self._check_auth_window_completed)
        self.auth_poll_timer.start()

    def _find_post_login_hwnd(self):
        """Find the standalone auth window once it redirects to Google Account home."""
        found_hwnd = None

        def enum_handler(hwnd, _):
            nonlocal found_hwnd
            if found_hwnd is None and win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title in ("Tài khoản Google", "Google Account"):
                    found_hwnd = hwnd

        win32gui.EnumWindows(enum_handler, None)
        return found_hwnd

    def _check_auth_window_completed(self):
        """Close the external auth window once signed in, then sync cookies into Hub."""
        hwnd = self._find_post_login_hwnd()
        if not hwnd:
            return

        self.auth_poll_timer.stop()
        # Send WM_CLOSE (0x0010) so the browser flushes and unlocks its Cookies SQLite DB
        win32gui.PostMessage(hwnd, 0x0010, 0, 0)
        QTimer.singleShot(800, self.finish_login_and_reload)

    def finish_login_and_reload(self):
        """Sync cookies from the standalone login profile and reload all workspace tabs."""
        if self.auth_poll_timer and self.auth_poll_timer.isActive():
            self.auth_poll_timer.stop()

        login_dir = os.path.join(self.profile_dir, "browser_login")
        count = extract_and_inject_cookies(login_dir, self.web_profile)
        print(f"Đã đồng bộ {count} cookie vào profile {self.profile_id}")

        for tab_idx, view in self.web_views.items():
            service_url = GOOGLE_SERVICES[tab_idx][1]
            view.load(QUrl(service_url))

        main_win = self.window()
        if main_win:
            main_win.raise_()
            main_win.activateWindow()

    def open_embedded_chrome(self):
        """Launch and embed a standalone Chrome/Edge window inside the Chrome tab."""
        if self.chrome_embedded:
            return

        browser_path = find_standalone_browser()
        if not browser_path or not os.path.exists(browser_path):
            return

        user_data = os.path.join(self.profile_dir, "chrome_data")
        marker_url = f"https://www.google.com/?profile={self.profile_id}"
        subprocess.Popen([browser_path, f"--user-data-dir={user_data}", marker_url])
        time.sleep(1.5)

        hwnd = self.find_latest_chrome_hwnd()
        if hwnd:
            window = QWindow.fromWinId(hwnd)
            widget = QWidget.createWindowContainer(window, self.chrome_container)
            c_layout = QVBoxLayout(self.chrome_container)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.addWidget(widget)
            self.chrome_embedded = True

    def find_latest_chrome_hwnd(self):
        """Find the top-level window handle for the launched Chrome/Edge instance."""
        target_hwnd = None

        def enum_handler(hwnd, _):
            nonlocal target_hwnd
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if any(b in title for b in ["Google Chrome", "Edge"]) and target_hwnd is None:
                    target_hwnd = hwnd

        win32gui.EnumWindows(enum_handler, None)
        return target_hwnd

    def _freeze_tabs(self, is_active_workspace, check_idle=False, idle_timeout=IDLE_TIMEOUT_SECONDS):
        """Freeze background tabs, optionally checking the idle timeout."""
        if check_idle and idle_timeout <= 0:
            return

        now = time.time()
        for idx, view in self.web_views.items():
            if is_active_workspace and idx == self.current_tab_index:
                continue
            if idx in self.frozen_tabs:
                continue
            if GOOGLE_SERVICES[idx][0] in NEVER_FREEZE_TABS:
                continue
            if check_idle and (now - self.last_active_time.get(idx, now)) < idle_timeout:
                continue

            view.page().setLifecycleState(QWebEnginePage.LifecycleState.Frozen)
            self.frozen_tabs.add(idx)

    def freeze_idle_tabs(self, is_active_workspace, idle_timeout=IDLE_TIMEOUT_SECONDS):
        """Freeze tabs idle for longer than idle_timeout seconds."""
        self._freeze_tabs(is_active_workspace, check_idle=True, idle_timeout=idle_timeout)

    def freeze_all_now(self, is_active_workspace):
        """Immediately freeze all non-visible tabs."""
        self._freeze_tabs(is_active_workspace, check_idle=False)
