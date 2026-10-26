"""
Configuration and settings management for FileFlow.
Handles favorite folders, default paths, user preferences, and history.
"""
import os
import json
from pathlib import Path

def get_app_data_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata) / "FileFlow"
    else:
        base = Path.home() / ".fileflow"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return base

DEFAULT_CONFIG_PATH = str(get_app_data_dir() / "config.json")

def get_system_folders():
    """Return standard user directories on Windows, handling OneDrive redirection."""
    user_home = Path.home()
    folders = {}

    # Check via Windows Shell if available
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        dt = shell.SpecialFolders("Desktop")
        doc = shell.SpecialFolders("MyDocuments")
        if dt and os.path.exists(dt):
            folders["Desktop"] = dt
        if doc and os.path.exists(doc):
            folders["Documents"] = doc
    except Exception:
        pass

    candidates = {
        "Downloads": [user_home / "Downloads"],
        "Desktop": [user_home / "OneDrive" / "Desktop", user_home / "Desktop"],
        "Documents": [user_home / "OneDrive" / "Documents", user_home / "Documents"],
        "Pictures": [user_home / "OneDrive" / "Pictures", user_home / "Pictures"],
        "Videos": [user_home / "Videos"],
        "Music": [user_home / "Music"],
    }

    for name, path_list in candidates.items():
        if name not in folders:
            for p in path_list:
                if p.exists():
                    folders[name] = str(p)
                    break

    return folders

DEFAULT_CONFIG = {
    "theme": "dark",
    "conflict_mode": "rename",  # rename, overwrite, skip
    "source_folder": str(Path.home() / "Downloads" if (Path.home() / "Downloads").exists() else Path.home()),
    "destination_folder": str(Path.home() / "Desktop" if (Path.home() / "Desktop").exists() else Path.home()),
    "favorites": [
        {"name": "Downloads", "path": str(Path.home() / "Downloads")},
        {"name": "Desktop", "path": str(Path.home() / "Desktop")},
        {"name": "Documents", "path": str(Path.home() / "Documents")},
        {"name": "Pictures", "path": str(Path.home() / "Pictures")},
    ],
    "history": [],
    "auto_refresh": True,
}

class ConfigManager:
    def __init__(self, config_path=None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config = self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge with default config to ensure all keys exist
                    merged = dict(DEFAULT_CONFIG)
                    merged.update(data)
                    return merged
            except Exception as e:
                print(f"Failed to load config, using defaults: {e}")
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def add_favorite(self, name, path):
        # Prevent duplicates
        for fav in self.config.get("favorites", []):
            if os.path.normpath(fav.get("path", "")) == os.path.normpath(path):
                fav["name"] = name
                self.save()
                return
        self.config.setdefault("favorites", []).append({"name": name, "path": path})
        self.save()

    def remove_favorite(self, path):
        favs = self.config.get("favorites", [])
        self.config["favorites"] = [
            f for f in favs if os.path.normpath(f.get("path", "")) != os.path.normpath(path)
        ]
        self.save()

    def add_history_entry(self, entry):
        history = self.config.get("history", [])
        history.insert(0, entry)
        # Keep last 50 entries
        self.config["history"] = history[:50]
        self.save()

    def pop_last_history(self):
        history = self.config.get("history", [])
        if history:
            last = history.pop(0)
            self.save()
            return last
        return None
