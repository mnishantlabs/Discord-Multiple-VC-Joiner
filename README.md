# Discord Token Manager

Organize, validate, and manage voice channels across multiple Discord accounts from a single desktop window. Everything is stored locally on your machine.

**Website:** https://mnishantlabs.github.io/Discord-Multiple-VC-Joiner/

![release](https://img.shields.io/badge/release-v1.0.0-5865f2?style=for-the-badge)
![license](https://img.shields.io/badge/license-MIT-lightgrey?style=for-the-badge)
![Windows](https://img.shields.io/badge/platform-Windows_10_11-0078d6?style=for-the-badge)

---

## About

Discord Token Manager is a Windows desktop tool built with Python and CustomTkinter. It replaces juggling a plain-text file of account tokens with a clean, resizable three-pane interface:

- **Accounts** – import, validate, filter, and quickly inspect every token.
- **Server List** – searchable, pinnable servers with a collapsible members panel.
- **Voice Channels** – one-click joining of selected accounts with configurable delays, proxies, and self-mute/self-deaf toggles.

Focus on what you manage, not how you manage it.

## Features

- Resizable panels — drag the dividers between Accounts / Server List / Voice; double-click resets; layout is remembered between sessions
- Vertical Members splitter inside the server panel
- Bulk token validation with smart concurrency and rate-limit handling
- All / Valid / Invalid filters, search, and dense/compact card modes
- Server pinning and smart search
- Voice join with delay, proxy, and self-mute / self-deaf options
- Activity/reason presets and automatic validation on startup
- Command palette (`Ctrl+Shift+P`)
- Windows 11 Mica/Acrylic backdrop effects (falls back gracefully on Windows 10)
- Tabbed settings dialog (General, Appearance, Validation, Voice, Network, Activity, Advanced, About)

## Download

Pick the flavor that suits you. All three are the same **v1.0.0** build.

| Edition | File | Notes |
| --- | --- | --- |
| Compact | `DiscordTokenManager-compact.exe` | Single self-contained EXE, no install |
| Portable | `DiscordTokenManager-portable.zip` | Zipped folder, extract and run anywhere |
| Setup | `DiscordTokenManager-setup.exe` | Guideyouinstaller with Start Menu/Desktop shortcuts and uninstall |

Get them from the [releases page](https://github.com/mnishantlabs/Discord-Multiple-VC-Joiner/releases) or download directly from the [website](https://mnishantlabs.github.io/Discord-Multiple-VC-Joiner/).

**System requirements:** Windows 10 or 11 (64-bit).

## Privacy

- All tokens, servers, and settings live in your user profile (`%APPDATA%\DiscordTokenManager`).
- The app never uploads your tokens anywhere and contains no tracking or telemetry.

## Building from source

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### Packaging

The repository ships three PyInstaller specs sharing a common analysis helper:

```powershell
# Portable (onedir folder  -> dist\DiscordTokenManager\)
python -m PyInstaller DiscordTokenManager.spec --noconfirm

# Compact (single file -> dist\DiscordTokenManager-compact.exe)
python -m PyInstaller compact.spec --noconfirm

# Setup installer (embeds the portable build; run the portable build first)
python -m PyInstaller setup.spec --noconfirm
```

Note: the `dist/` output folder is git-ignored.

## Project layout

```
core/          domain logic, events, enums, predicates
services/      clients, validation, voice, channels, settings, state
storage/       token + settings repositories, data paths
controllers/   action orchestration and shortcuts
ui/            theme, widgets, dialogs, views (main window)
utils/         async bridge, clipboard, platform helpers
main.py        app entry point
```

## Disclaimer

This is an independent, community-made tool. It is not affiliated with, endorsed by, or connected to Discord Inc. in any way.

Automated use of Discord accounts (including token-based login and bulk actions) may violate Discord's Terms of Service and can result in account restrictions. Use this tool only on accounts you own, responsibly, and at your own risk.