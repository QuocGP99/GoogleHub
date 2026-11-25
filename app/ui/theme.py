"""Apple macOS-inspired dark theme stylesheet, SF Pro typography, and app icon."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap

FONT_FAMILY_STACK = (
    '"SF Pro Display", "SF Pro Text", "SF Pro", '
    '"-apple-system", "Segoe UI Variable", "Segoe UI", sans-serif'
)


def get_app_font():
    """Return the default application QFont prioritizing SF Pro."""
    font = QFont("SF Pro Text", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    return font


def create_default_icon():
    """Render an Apple-style squircle gradient 'G' application icon."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, 0, 64, 64)
    gradient.setColorAt(0.0, QColor("#0A84FF"))
    gradient.setColorAt(1.0, QColor("#5E5CE6"))
    painter.setBrush(gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

    painter.setPen(QColor("#FFFFFF"))
    font = QFont("SF Pro Display", 28, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "G")
    painter.end()
    return QIcon(pixmap)


def get_dark_theme():
    """Return the QSS stylesheet styled after macOS dark mode with SF Pro."""
    return f"""
    * {{
        font-family: {FONT_FAMILY_STACK};
    }}
    QMainWindow {{
        background-color: #0D0D0F;
    }}
    #Sidebar {{
        background-color: #161618;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }}
    #AppTitle {{
        color: #F5F5F7;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.4px;
        padding: 2px 4px;
    }}
    #SectionLabel {{
        color: #6E6E73;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.9px;
        padding: 8px 8px 2px 8px;
    }}
    #Divider {{
        background-color: rgba(255, 255, 255, 0.08);
        max-height: 1px;
        margin: 6px 4px;
    }}
    QPushButton {{
        background-color: transparent;
        color: #AEAEB2;
        text-align: left;
        padding: 8px 10px;
        border-radius: 9px;
        font-size: 13px;
        font-weight: 500;
        border: none;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 0.07);
        color: #F5F5F7;
    }}
    QPushButton:checked {{
        background-color: rgba(10, 132, 255, 0.18);
        color: #409CFF;
        font-weight: 600;
    }}
    QPushButton[collapsed="true"] {{
        text-align: center;
        padding: 9px 0px;
        font-size: 15px;
    }}
    #CollapseBtn {{
        background-color: rgba(255, 255, 255, 0.05);
        color: #98989D;
        text-align: center;
        padding: 0px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }}
    #CollapseBtn:hover {{
        background-color: rgba(255, 255, 255, 0.12);
        color: #F5F5F7;
    }}
    #ProfileBtn {{
        padding: 8px 10px;
        border: 1px solid rgba(255, 255, 255, 0.07);
        background-color: rgba(255, 255, 255, 0.03);
        color: #D1D1D6;
    }}
    #ProfileBtn:hover {{
        background-color: rgba(255, 255, 255, 0.08);
        color: #FFFFFF;
    }}
    #ProfileBtn[collapsed="true"] {{
        padding: 8px 0px;
        text-align: center;
        font-size: 16px;
    }}
    #ActionBtn {{
        background-color: rgba(10, 132, 255, 0.12);
        color: #409CFF;
        border: 1px solid rgba(10, 132, 255, 0.28);
        text-align: center;
        padding: 8px 10px;
        margin-top: 4px;
        font-weight: 600;
    }}
    #ActionBtn:hover {{
        background-color: #0A84FF;
        color: #FFFFFF;
        border-color: #0A84FF;
    }}
    #ActionBtn[collapsed="true"] {{
        padding: 8px 0px;
        font-size: 15px;
    }}
    QToolTip {{
        background-color: #2C2C2E;
        color: #F5F5F7;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 6px;
        padding: 5px 8px;
        font-size: 12px;
    }}
    """
