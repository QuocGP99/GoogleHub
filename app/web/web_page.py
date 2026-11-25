"""Custom QWebEnginePage handling permissions and Google authentication redirects."""

from PyQt6.QtCore import QTimer
from PyQt6.QtWebEngineCore import QWebEnginePage


class CustomWebPage(QWebEnginePage):
    """WebEngine page that auto-grants permissions and intercepts Google login redirects."""

    def __init__(self, profile, workspace, parent=None):
        super().__init__(profile, parent)
        self.workspace = workspace
        self.featurePermissionRequested.connect(self.handle_permission)

    def handle_permission(self, security_origin, feature):
        """Grant requested browser feature permissions (mic, camera, notifications, etc.)."""
        self.setFeaturePermission(
            security_origin,
            feature,
            QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
        )

    def createWindow(self, _type):
        """Keep popup windows inside the current page."""
        return self

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """Intercept hub:// actions and accounts.google.com login redirects."""
        if url.scheme() == "hub":
            action = url.host().lower()
            if action == "auth-complete":
                QTimer.singleShot(0, self.workspace.finish_login_and_reload)
            elif action == "reopen-login":
                QTimer.singleShot(0, lambda: self.workspace.launch_auth_browser())
            return False

        host = url.host().lower()
        if "accounts.google.com" in host and is_main_frame:
            auth_url = url.toString()
            QTimer.singleShot(0, lambda: self.workspace.handle_google_auth_required(auth_url))
            return False

        return super().acceptNavigationRequest(url, nav_type, is_main_frame)
