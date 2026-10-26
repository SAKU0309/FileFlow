"""
Creates a convenient shortcut on the Windows Desktop for FileFlow.
"""
import os
import sys
from pathlib import Path

def create_shortcut():
    try:
        import win32com.client
    except ImportError:
        print("win32com not available. Skipping shortcut creation.")
        return False

    desktop = None
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        dt = shell.SpecialFolders("Desktop")
        if dt and os.path.exists(dt):
            desktop = Path(dt)
    except Exception:
        pass

    if not desktop or not desktop.exists():
        candidates = [Path.home() / "OneDrive" / "Desktop", Path.home() / "Desktop"]
        for c in candidates:
            if c.exists():
                desktop = c
                break

    if not desktop:
        print("Desktop directory could not be located.")
        return False

    app_dir = Path(__file__).resolve().parent
    bat_path = app_dir / "Start_FileFlow.bat"
    shortcut_path = desktop / "FileFlow.lnk"

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = str(bat_path)
        shortcut.WorkingDirectory = str(app_dir)
        shortcut.Description = "FileFlow - Easy File Transfer App"
        shortcut.save()
        print(f"Created shortcut at: {shortcut_path}")
        return True
    except Exception as e:
        print(f"Failed to create desktop shortcut: {e}")
        return False

if __name__ == "__main__":
    create_shortcut()
