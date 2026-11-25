"""Apple-style Settings dialog for managing accounts, language, and performance."""

import copy
import re
import time

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.i18n import t
from app.ui.theme import FONT_FAMILY_STACK

ACCENT_COLORS = [
    ("Blue", "#0A84FF"),
    ("Green", "#30D158"),
    ("Purple", "#BF5AF2"),
    ("Orange", "#FF9F0A"),
    ("Pink", "#FF375F"),
    ("Teal", "#64D2FF"),
]

IDLE_OPTIONS = [5, 10, 15, 30, 60, 0]


def _slugify_profile_id(name, existing_ids):
    """Generate a unique filesystem-safe profile ID from a display name."""
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    base = ascii_part or f"profile_{int(time.time())}"
    candidate = base
    counter = 2
    while candidate in existing_ids:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def _color_dot_icon(hex_color):
    """Create a small circular color swatch icon."""
    pixmap = QPixmap(14, 14)
    pixmap.fill(Qt.GlobalColor.transparent)
    from PyQt6.QtGui import QPainter
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(hex_color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, 12, 12)
    painter.end()
    return QIcon(pixmap)


class SettingsDialog(QDialog):
    """Modal settings dialog for configuring accounts, UI language, and behavior."""

    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.settings = copy.deepcopy(current_settings)
        self.lang = self.settings.get("language", "vi")
        self.profiles = self.settings.get("profiles", [])

        self.setWindowTitle(t(self.lang, "settings_title"))
        self.setFixedSize(500, 440)
        self.setStyleSheet(self._dialog_stylesheet())

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_accounts_tab(), t(self.lang, "tab_accounts"))
        self.tabs.addTab(self._build_general_tab(), t(self.lang, "tab_general"))
        root_layout.addWidget(self.tabs)

        footer = QHBoxLayout()
        footer.addStretch()
        cancel_btn = QPushButton(t(self.lang, "cancel_btn"))
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)

        save_btn = QPushButton(t(self.lang, "save_btn"))
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self._on_save)
        footer.addWidget(save_btn)
        root_layout.addLayout(footer)

    def _build_accounts_tab(self):
        """Build the account profiles management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        desc = QLabel(t(self.lang, "accounts_desc"))
        desc.setWordWrap(True)
        desc.setObjectName("MutedText")
        layout.addWidget(desc)

        self.profile_list = QListWidget()
        self._refresh_profile_list()
        layout.addWidget(self.profile_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(t(self.lang, "add_account"))
        add_btn.setObjectName("SecondaryBtn")
        add_btn.clicked.connect(self._add_profile)
        btn_row.addWidget(add_btn)

        edit_btn = QPushButton(t(self.lang, "edit_account"))
        edit_btn.setObjectName("SecondaryBtn")
        edit_btn.clicked.connect(self._edit_profile)
        btn_row.addWidget(edit_btn)

        del_btn = QPushButton(t(self.lang, "delete_account"))
        del_btn.setObjectName("DangerBtn")
        del_btn.clicked.connect(self._delete_profile)
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        return tab

    def _build_general_tab(self):
        """Build the general, language, and performance settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(14)

        lang_label = QLabel(t(self.lang, "lang_label"))
        layout.addWidget(lang_label)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Tiếng Việt", "vi")
        self.lang_combo.addItem("English", "en")
        idx = self.lang_combo.findData(self.lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        layout.addWidget(self.lang_combo)

        idle_label = QLabel(t(self.lang, "idle_label"))
        layout.addWidget(idle_label)
        self.idle_combo = QComboBox()
        for mins in IDLE_OPTIONS:
            label = (
                t(self.lang, "idle_never")
                if mins == 0
                else t(self.lang, "idle_minutes", m=mins)
            )
            self.idle_combo.addItem(label, mins)
        idle_idx = self.idle_combo.findData(self.settings.get("idle_timeout_minutes", 15))
        if idle_idx >= 0:
            self.idle_combo.setCurrentIndex(idle_idx)
        layout.addWidget(self.idle_combo)

        self.tray_checkbox = QCheckBox(t(self.lang, "tray_close_label"))
        self.tray_checkbox.setChecked(self.settings.get("minimize_to_tray", True))
        layout.addWidget(self.tray_checkbox)

        layout.addStretch()
        return tab

    def _refresh_profile_list(self):
        self.profile_list.clear()
        for p in self.profiles:
            item = QListWidgetItem(_color_dot_icon(p.get("color", "#0A84FF")), p["name"])
            self.profile_list.addItem(item)
        if self.profiles:
            self.profile_list.setCurrentRow(0)

    def _pick_color(self, current_hex="#0A84FF"):
        color_names = [f"{label} ({code})" for label, code in ACCENT_COLORS]
        current_idx = next(
            (i for i, (_, code) in enumerate(ACCENT_COLORS) if code.lower() == current_hex.lower()),
            0,
        )
        choice, ok = QInputDialog.getItem(
            self,
            t(self.lang, "settings_title"),
            t(self.lang, "account_color_label"),
            color_names,
            current_idx,
            False,
        )
        if not ok:
            return None
        return ACCENT_COLORS[color_names.index(choice)][1]

    def _add_profile(self):
        name, ok = QInputDialog.getText(
            self, t(self.lang, "add_account"), t(self.lang, "account_name_label")
        )
        if not ok or not name.strip():
            return
        color = self._pick_color("#0A84FF") or "#0A84FF"
        existing_ids = {p["id"] for p in self.profiles}
        self.profiles.append({
            "id": _slugify_profile_id(name.strip(), existing_ids),
            "name": name.strip(),
            "color": color,
        })
        self._refresh_profile_list()

    def _edit_profile(self):
        row = self.profile_list.currentRow()
        if row < 0 or row >= len(self.profiles):
            return
        profile = self.profiles[row]
        name, ok = QInputDialog.getText(
            self,
            t(self.lang, "edit_account"),
            t(self.lang, "account_name_label"),
            text=profile["name"],
        )
        if not ok or not name.strip():
            return
        color = self._pick_color(profile.get("color", "#0A84FF"))
        profile["name"] = name.strip()
        if color:
            profile["color"] = color
        self._refresh_profile_list()
        self.profile_list.setCurrentRow(row)

    def _delete_profile(self):
        if len(self.profiles) <= 1:
            QMessageBox.warning(
                self, t(self.lang, "settings_title"), t(self.lang, "min_one_account")
            )
            return
        row = self.profile_list.currentRow()
        if 0 <= row < len(self.profiles):
            self.profiles.pop(row)
            self._refresh_profile_list()

    def _on_save(self):
        self.settings["language"] = self.lang_combo.currentData()
        self.settings["idle_timeout_minutes"] = self.idle_combo.currentData()
        self.settings["minimize_to_tray"] = self.tray_checkbox.isChecked()
        self.settings["profiles"] = self.profiles
        self.accept()

    def get_settings(self):
        """Return the updated settings dictionary."""
        return self.settings

    def _dialog_stylesheet(self):
        return f"""
        * {{ font-family: {FONT_FAMILY_STACK}; color: #F5F5F7; font-size: 13px; }}
        QDialog {{ background-color: #161618; }}
        #MutedText {{ color: #98989D; font-size: 12px; }}
        QTabWidget::pane {{
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            background-color: #1C1C1E;
        }}
        QTabBar::tab {{
            background: transparent;
            color: #98989D;
            padding: 8px 16px;
            border-radius: 8px;
            margin-right: 4px;
            font-weight: 600;
        }}
        QTabBar::tab:selected {{
            background-color: rgba(10, 132, 255, 0.18);
            color: #409CFF;
        }}
        QListWidget, QComboBox {{
            background-color: #2C2C2E;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 9px;
            padding: 6px 10px;
        }}
        QListWidget::item {{ padding: 8px 6px; border-radius: 6px; }}
        QListWidget::item:selected {{
            background-color: rgba(10, 132, 255, 0.25);
            color: #FFFFFF;
        }}
        QPushButton {{
            padding: 8px 14px;
            border-radius: 9px;
            font-weight: 600;
            border: none;
        }}
        #PrimaryBtn {{ background-color: #0A84FF; color: #FFFFFF; }}
        #PrimaryBtn:hover {{ background-color: #0070E0; }}
        #SecondaryBtn {{
            background-color: rgba(255, 255, 255, 0.08);
            color: #F5F5F7;
        }}
        #SecondaryBtn:hover {{ background-color: rgba(255, 255, 255, 0.14); }}
        #DangerBtn {{
            background-color: rgba(255, 69, 58, 0.16);
            color: #FF453A;
        }}
        #DangerBtn:hover {{ background-color: #FF453A; color: #FFFFFF; }}
        """
