"""Entry point for Google Workspace Multi-Account Hub."""

import os
import sys

from PyQt6.QtWidgets import QApplication

from app.config import CHROMIUM_FLAGS
from app.ui.main_window import GoogleHubApp
from app.ui.theme import get_app_font


def main():
    """Configure Chromium flags, initialize Qt application, and launch main window."""
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = CHROMIUM_FLAGS
    sys.argv.extend(CHROMIUM_FLAGS.split())

    app = QApplication(sys.argv)
    app.setFont(get_app_font())
    app.setQuitOnLastWindowClosed(False)

    window = GoogleHubApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()