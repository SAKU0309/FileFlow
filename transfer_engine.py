"""
Core file transfer engine for FileFlow.
Handles moving, copying, conflict resolution (auto-rename, overwrite, skip),
undo capabilities, and background operation dispatch.
"""
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable

# Extension categories for easy filtering
FILE_CATEGORIES = {
    "All": set(),
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls", ".csv", ".pptx", ".ppt", ".odt", ".rtf", ".md"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".raw"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".m4v"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".iso"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".cs", ".json", ".xml", ".sql", ".sh"},
}

def format_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def get_unique_destination_path(target_path: str) -> str:
    """
    If target_path already exists, find a unique name like:
    'filename (1).ext', 'filename (2).ext', etc.
    """
    if not os.path.exists(target_path):
        return target_path

    parent = os.path.dirname(target_path)
    base_name = os.path.basename(target_path)

    if os.path.isdir(target_path):
        name = base_name
        ext = ""
    else:
        name, ext = os.path.splitext(base_name)

    counter = 1
    while True:
        candidate_name = f"{name} ({counter}){ext}"
        candidate_path = os.path.join(parent, candidate_name)
        if not os.path.exists(candidate_path):
            return candidate_path
        counter += 1

class TransferResult:
    def __init__(self):
        self.transferred_items: List[Tuple[str, str]] = []  # (source, dest)
        self.failed_items: List[Tuple[str, str]] = []       # (source, error_reason)
        self.skipped_items: List[str] = []                  # source paths
        self.action = "move"
        self.timestamp = datetime.now().isoformat()
        self.total_bytes = 0

    @property
    def success_count(self) -> int:
        return len(self.transferred_items)

    @property
    def fail_count(self) -> int:
        return len(self.failed_items)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped_items)

    def to_history_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "display_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": self.action,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "skipped_count": self.skipped_count,
            "total_bytes": self.total_bytes,
            "formatted_size": format_size(self.total_bytes),
            "items": [{"src": src, "dst": dst} for src, dst in self.transferred_items],
        }

class TransferEngine:
    """Manages file transfers, collisions, and undos."""

    def __init__(self):
        self.undo_stack: List[dict] = []

    def execute_transfer(
        self,
        source_paths: List[str],
        destination_folder: str,
        action: str = "move",  # "move" or "copy"
        conflict_mode: str = "rename",  # "rename", "overwrite", "skip"
        progress_callback: Optional[Callable[[int, int, str, float], None]] = None,
    ) -> TransferResult:
        """
        Transfers files/folders from source_paths to destination_folder.
        """
        result = TransferResult()
        result.action = action
        total_items = len(source_paths)

        if not os.path.isdir(destination_folder):
            try:
                os.makedirs(destination_folder, exist_ok=True)
            except Exception as e:
                for p in source_paths:
                    result.failed_items.append((p, f"Cannot create destination folder: {e}"))
                return result

        for idx, src in enumerate(source_paths):
            if not os.path.exists(src):
                result.failed_items.append((src, "Source file/folder does not exist"))
                continue

            item_name = os.path.basename(src.rstrip("/\\"))
            dest_target = os.path.join(destination_folder, item_name)

            # Prevent moving folder into itself or subfolder
            if os.path.isdir(src):
                src_abs = os.path.abspath(src).lower()
                dest_abs = os.path.abspath(dest_target).lower()
                if dest_abs.startswith(src_abs + os.sep) or dest_abs == src_abs:
                    result.failed_items.append((src, "Cannot move a folder into itself"))
                    continue

            # Calculate size for stats
            try:
                if os.path.isfile(src):
                    result.total_bytes += os.path.getsize(src)
                elif os.path.isdir(src):
                    for dirpath, _, filenames in os.walk(src):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if os.path.isfile(fp):
                                result.total_bytes += os.path.getsize(fp)
            except Exception:
                pass

            # Handle existing destination
            final_dest = dest_target
            if os.path.exists(dest_target):
                # Don't transfer onto the exact same file in the same folder
                if os.path.abspath(src).lower() == os.path.abspath(dest_target).lower():
                    result.skipped_items.append(src)
                    continue

                if conflict_mode == "skip":
                    result.skipped_items.append(src)
                    continue
                elif conflict_mode == "rename":
                    final_dest = get_unique_destination_path(dest_target)
                elif conflict_mode == "overwrite":
                    try:
                        if os.path.isdir(dest_target):
                            shutil.rmtree(dest_target)
                        else:
                            os.remove(dest_target)
                    except Exception as e:
                        result.failed_items.append((src, f"Failed to overwrite destination: {e}"))
                        continue

            if progress_callback:
                percent = ((idx + 1) / total_items) * 100
                progress_callback(idx + 1, total_items, item_name, percent)

            # Perform the action
            try:
                if action == "move":
                    shutil.move(src, final_dest)
                elif action == "copy":
                    if os.path.isdir(src):
                        shutil.copytree(src, final_dest)
                    else:
                        shutil.copy2(src, final_dest)
                else:
                    raise ValueError(f"Unknown action: {action}")

                result.transferred_items.append((src, final_dest))
            except Exception as e:
                result.failed_items.append((src, str(e)))

        # If move was successful, save to undo stack
        if result.success_count > 0 and action == "move":
            self.undo_stack.append(result.to_history_dict())

        return result

    def undo(self, history_entry: Optional[dict] = None) -> Tuple[int, int, List[str]]:
        """
        Undoes a transfer by moving files back to their original source paths.
        Returns: (restored_count, failed_count, errors)
        """
        record = history_entry or (self.undo_stack.pop() if self.undo_stack else None)
        if not record:
            return 0, 0, ["No transfer history to undo"]

        action = record.get("action", "move")
        if action != "move":
            return 0, 0, [f"Undo is only supported for 'move' transfers, not '{action}'."]

        items = record.get("items", [])
        restored = 0
        failed = 0
        errors = []

        for item in reversed(items):
            src_orig = item.get("src")
            dst_curr = item.get("dst")

            if not dst_curr or not os.path.exists(dst_curr):
                failed += 1
                errors.append(f"Destination file missing: {dst_curr}")
                continue

            try:
                orig_dir = os.path.dirname(src_orig)
                if not os.path.exists(orig_dir):
                    os.makedirs(orig_dir, exist_ok=True)

                # If original path is now taken by another file, rename it safely
                final_restore_path = src_orig
                if os.path.exists(src_orig) and os.path.abspath(src_orig).lower() != os.path.abspath(dst_curr).lower():
                    final_restore_path = get_unique_destination_path(src_orig)

                shutil.move(dst_curr, final_restore_path)
                restored += 1
            except Exception as e:
                failed += 1
                errors.append(f"Could not restore {dst_curr} -> {src_orig}: {e}")

        return restored, failed, errors
