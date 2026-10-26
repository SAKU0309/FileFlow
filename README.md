# ⚡ FileFlow — Effortless File Transfer for Windows

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue.svg?logo=windows)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://python.org)
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet)](https://github.com/TomSchimansky/CustomTkinter)


> Move and organize files across folders on your laptop with **1 click** — completely eliminating the tedious **Ctrl+C / Ctrl+V** copy-paste routine.

---

## 💡 The Problem FileFlow Solves
Moving files between folders on Windows usually requires:
- Opening multiple Explorer windows and resizing them side-by-side.
- Pressing `Ctrl+X` / `Ctrl+C`, navigating into deep folders, and pressing `Ctrl+V`.
- Worrying about accidental overwrites or misplacing files.

**FileFlow solves this with a dedicated dual-pane workspace:** select your files, click **`➡️ MOVE`**, and you're done!

---

## 🌟 Key Features

- 🚀 **1-Click Move & Copy:** Transfer files instantly without touching the clipboard.
- ↩️ **Instant Undo System:** Accidentally moved something? Revert any transfer with 1 click.
- 📥 **Drag-and-Drop:** Drag files directly from your desktop or Windows Explorer into the target pane.
- ⇄ **1-Click Folder Swap:** Instantly switch source and destination folders.
- ⭐ **Quick Presets & Favorites:** Fast access to `Downloads`, `Desktop`, `Documents`, `Pictures`, and custom starred folders.
- 🔍 **Real-Time Search & Type Filters:** Filter by `Documents`, `Images`, `Videos`, `Audio`, `Archives`, or live filename search.
- 🛡️ **Conflict Protection:** Automatically renames duplicates (`file (1).pdf`), overwrites, or skips.
- 📦 **Standalone Installer:** Runs on any Windows laptop without needing Python or admin privileges.
- 🌗 **Modern Dark & Light Mode:** Sleek Windows 11-style UI.

---

## 🚀 Quick Download & Install (No Python Required)

1. Download **`FileFlow-Windows-v1.0.zip`** from the [Releases](https://github.com) section.
2. Extract the ZIP folder.
3. Double-click **`Install_FileFlow.bat`**.
4. Shortcuts will automatically be placed on your **Desktop** and **Start Menu**!

---

## 🛠️ Running from Source (Developers)

```bash
# Clone the repository
git clone https://github.com/your-username/FileFlow.git
cd FileFlow

# Install dependencies
pip install -r requirements.txt

# Launch application
python main.py
```

---

## 📂 Project Structure

```text
FileFlow/
├── main.py                  # CustomTkinter GUI & drag-and-drop controller
├── transfer_engine.py       # Core transfer, collision handling, and undo logic
├── config_manager.py        # Settings, presets, and history storage
├── history_dialog.py        # Transfer History modal window
├── Start_FileFlow.bat       # Windows launcher script
├── Install_FileFlow.bat     # 1-click batch setup installer
├── installer.ps1            # Windows installation automation script
├── icon.ico                 # App icon
├── requirements.txt         # Dependencies list
└── README.md                # Documentation
```

---


