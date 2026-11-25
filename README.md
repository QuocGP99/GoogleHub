# Google Hub

Google Workspace Multi-Account Hub built with Python & PyQt6.

## Features
- **Multi-Account Isolation**: Separate cookies, storage, and cache per account profile.
- **12 Google Web Services + Embedded Browser**: Gemini, Gmail, Drive, YouTube, Photos, Maps, Translate, Docs, Sheets, Slides, Calendar, Meet.
- **Safe Standalone Login & Cookie Sync**: Automatically opens Chrome/Edge for Google sign-in (avoiding embedded WebView blocks) and syncs decrypted session cookies back into the Hub.
- **Apple-style Collapsible Sidebar**: Smooth animated sidebar with SF Pro typography and dark mode styling.
- **RAM Optimization**: Auto-freeze idle background tabs (with exemptions for Meet & YouTube) and system tray support.
- **Settings**: Manage account profiles, UI language (Vietnamese / English), idle timeout, and tray behavior.

## Run from Source
```bash
pip install PyQt6 PyQt6-WebEngine pywin32
python main.py
```

## Build `.exe` & `.msi`
```powershell
python -m PyInstaller GoogleHub.spec --noconfirm
wix build installer\GoogleHub.wxs -ext WixToolset.UI.wixext/5.0.2 -arch x64 -o dist\GoogleHub-Setup-1.0.0.msi
```
