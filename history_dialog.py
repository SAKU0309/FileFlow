"""
History and Undo Dialog for FileFlow.
Displays past file transfers and allows rolling them back with 1-click Undo.
"""
import os
import customtkinter as ctk
from typing import Callable, List, Optional
from tkinter import messagebox

class HistoryDialog(ctk.CTkToplevel):
    def __init__(self, parent, history: List[dict], on_undo_callback: Callable[[dict], None]):
        super().__init__(parent)
        self.title("Transfer History & Undo")
        self.geometry("720x520")
        self.minsize(600, 400)
        self.history = history
        self.on_undo_callback = on_undo_callback

        # Make modal-like
        self.transient(parent)
        self.grab_set()

        self.setup_ui()

    def setup_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        title = ctk.CTkLabel(
            header_frame,
            text="📜 Transfer History & Undo Log",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(side="left")

        count_badge = ctk.CTkLabel(
            header_frame,
            text=f"{len(self.history)} Records",
            fg_color=("gray85", "gray25"),
            corner_radius=6,
            padx=10,
            pady=4,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        count_badge.pack(side="right")

        # Instructions / note
        info_label = ctk.CTkLabel(
            self,
            text="Below are your recent file transfers. You can click 'Undo' to move files back to their original locations.",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        info_label.pack(fill="x", padx=20, pady=(0, 10))

        # Scrollable container for records
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        if not self.history:
            empty_label = ctk.CTkLabel(
                self.scroll_frame,
                text="No transfers recorded yet in this session.\nTransfer some files to see history and undo options here!",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.pack(pady=60)
        else:
            for idx, entry in enumerate(self.history):
                self.create_history_card(entry, idx)

        # Bottom Close Button
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=(10, 15))

        close_btn = ctk.CTkButton(
            bottom_frame,
            text="Close",
            width=100,
            command=self.destroy
        )
        close_btn.pack(side="right")

    def create_history_card(self, entry: dict, index: int):
        card = ctk.CTkFrame(self.scroll_frame, corner_radius=10)
        card.pack(fill="x", pady=6, padx=5)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 5))

        action = entry.get("action", "move").upper()
        action_color = "#2fa572" if action == "COPY" else "#1f6aa5"

        badge = ctk.CTkLabel(
            header,
            text=action,
            fg_color=action_color,
            text_color="white",
            corner_radius=4,
            padx=8,
            pady=2,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        badge.pack(side="left")

        time_str = entry.get("display_time", entry.get("timestamp", "Recent"))
        time_label = ctk.CTkLabel(
            header,
            text=f"🕒 {time_str}",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        time_label.pack(side="left", padx=10)

        count = entry.get("success_count", len(entry.get("items", [])))
        size = entry.get("formatted_size", "")
        summary_text = f"{count} item{'s' if count != 1 else ''}"
        if size:
            summary_text += f" ({size})"

        summary_label = ctk.CTkLabel(
            header,
            text=summary_text,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        summary_label.pack(side="left", padx=5)

        # Undo button if it was a move and hasn't been undone
        is_undone = entry.get("undone", False)
        if action == "MOVE":
            if is_undone:
                undone_badge = ctk.CTkLabel(
                    header,
                    text="✓ Undone",
                    text_color="#2fa572",
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                undone_badge.pack(side="right")
            else:
                undo_btn = ctk.CTkButton(
                    header,
                    text="↩️ Undo Transfer",
                    width=120,
                    height=28,
                    fg_color="#d97706",
                    hover_color="#b45309",
                    command=lambda e=entry, b=card: self.trigger_undo(e, b)
                )
                undo_btn.pack(side="right")

        # Items list preview (show up to 4 items)
        items = entry.get("items", [])
        if items:
            items_box = ctk.CTkFrame(card, fg_color=("gray90", "gray17"), corner_radius=6)
            items_box.pack(fill="x", padx=12, pady=(0, 10))

            display_count = min(len(items), 4)
            for i in range(display_count):
                it = items[i]
                src_name = os.path.basename(it.get("src", ""))
                dst_name = it.get("dst", "")
                dest_dir = os.path.basename(os.path.dirname(dst_name))
                line_text = f"• {src_name}  ➔  ...\\{dest_dir}\\{os.path.basename(dst_name)}"
                item_lbl = ctk.CTkLabel(
                    items_box,
                    text=line_text,
                    font=ctk.CTkFont(size=11),
                    anchor="w"
                )
                item_lbl.pack(fill="x", padx=8, pady=2)

            if len(items) > 4:
                more_lbl = ctk.CTkLabel(
                    items_box,
                    text=f"... and {len(items) - 4} more files",
                    font=ctk.CTkFont(size=10, slant="italic"),
                    text_color="gray",
                    anchor="w"
                )
                more_lbl.pack(fill="x", padx=8, pady=(0, 4))

    def trigger_undo(self, entry: dict, card_frame: ctk.CTkFrame):
        items_count = len(entry.get("items", []))
        confirm = messagebox.askyesno(
            "Confirm Undo",
            f"Are you sure you want to move {items_count} item(s) back to their original locations?",
            parent=self
        )
        if confirm:
            self.on_undo_callback(entry)
            entry["undone"] = True
            # Refresh the card UI
            for widget in card_frame.winfo_children():
                widget.destroy()
            # Recreate card content
            self.create_history_card_content(entry, card_frame)

    def create_history_card_content(self, entry: dict, card: ctk.CTkFrame):
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 5))

        action = entry.get("action", "move").upper()
        badge = ctk.CTkLabel(
            header,
            text=action,
            fg_color="#1f6aa5",
            text_color="white",
            corner_radius=4,
            padx=8,
            pady=2,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        badge.pack(side="left")

        time_str = entry.get("display_time", entry.get("timestamp", "Recent"))
        time_label = ctk.CTkLabel(
            header,
            text=f"🕒 {time_str}",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        time_label.pack(side="left", padx=10)

        undone_badge = ctk.CTkLabel(
            header,
            text="✓ Successfully Restored (Undone)",
            text_color="#2fa572",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        undone_badge.pack(side="right")
