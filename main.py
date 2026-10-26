"""
FileFlow - Easy & Fast File Transfer Application for Windows.
Transfer files between folders without copy-pasting.
Supports Drag & Drop, 1-Click Move, Quick Favorites, Auto-Rename, and Undo.
"""
import os
import sys
import shutil
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES

from config_manager import ConfigManager, get_system_folders
from transfer_engine import (
    TransferEngine,
    FILE_CATEGORIES,
    format_size,
)
from history_dialog import HistoryDialog

# Set default theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

class FileFlowApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        # Config and Engine
        self.config_mgr = ConfigManager()
        self.engine = TransferEngine()

        # Load saved history into engine
        saved_history = self.config_mgr.get("history", [])
        self.engine.undo_stack = [h for h in saved_history if h.get("action") == "move" and not h.get("undone")]

        # Window settings
        self.title("FileFlow — Effortless File Transfer")
        self.geometry("1200x780")
        self.minsize(980, 640)

        # App Icon
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # State
        self.source_dir = self.config_mgr.get("source_folder") or str(Path.home() / "Downloads")
        self.dest_dir = self.config_mgr.get("destination_folder") or str(Path.home() / "Desktop")
        self.current_category = "All"
        self.search_query = ""
        self.source_items = []
        self.dest_items = []
        self.sort_column = "Name"
        self.sort_reverse = False
        self.is_transferring = False
        self.checked_items = set()

        # Theme
        saved_theme = self.config_mgr.get("theme", "dark")
        self.current_theme = saved_theme
        ctk.set_appearance_mode(saved_theme.capitalize())

        # Build UI
        self.setup_styles()
        self.create_widgets()

        # Initial folder scan
        self.refresh_source()
        self.refresh_dest()

    def setup_styles(self):
        """Configure ttk styles to match CustomTkinter theme."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.update_tree_theme()

    def update_tree_theme(self):
        """Update Treeview styling when switching dark/light mode."""
        is_dark = (self.current_theme == "dark")
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        fg_color = "#f3f4f6" if is_dark else "#111827"
        field_bg = "#1e1e1e" if is_dark else "#ffffff"
        head_bg = "#2d3748" if is_dark else "#e2e8f0"
        head_fg = "#ffffff" if is_dark else "#1a202c"
        select_bg = "#2563eb" if is_dark else "#3b82f6"

        self.style.configure(
            "Custom.Treeview",
            background=bg_color,
            foreground=fg_color,
            fieldbackground=field_bg,
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        self.style.map(
            "Custom.Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", "#ffffff")],
        )
        self.style.configure(
            "Custom.Treeview.Heading",
            background=head_bg,
            foreground=head_fg,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=(8, 4),
        )
        self.style.map(
            "Custom.Treeview.Heading",
            background=[("active", "#3b82f6" if is_dark else "#cbd5e1")],
            foreground=[("active", "#ffffff" if is_dark else "#000000")],
        )

    def create_widgets(self):
        # 1. Top Header Bar
        self.create_header()

        # 2. Source & Destination Path Selector Bar
        self.create_path_bars()

        # 3. Main Split View: Left Source Pane, Center Action Hub, Right Dest Pane
        self.create_main_content()

        # 4. Bottom Status & Progress Bar
        self.create_status_bar()

    def create_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))

        # Brand / Logo
        brand_frame = ctk.CTkFrame(header, fg_color="transparent")
        brand_frame.pack(side="left")

        logo_lbl = ctk.CTkLabel(
            brand_frame,
            text="⚡ FileFlow",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        logo_lbl.pack(side="left")

        tagline = ctk.CTkLabel(
            brand_frame,
            text="— Effortless file transfer without copy-paste",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        tagline.pack(side="left", padx=10)

        # Right control buttons (Theme toggle & History)
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right")

        self.history_btn = ctk.CTkButton(
            right_frame,
            text="📜 Transfer History & Undo",
            width=170,
            height=32,
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray35"),
            text_color=("black", "white"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_history_dialog
        )
        self.history_btn.pack(side="left", padx=6)

        self.theme_btn = ctk.CTkButton(
            right_frame,
            text="☀️ Light Mode" if self.current_theme == "dark" else "🌙 Dark Mode",
            width=110,
            height=32,
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray35"),
            text_color=("black", "white"),
            font=ctk.CTkFont(size=12),
            command=self.toggle_theme
        )
        self.theme_btn.pack(side="left", padx=6)

    def create_path_bars(self):
        container = ctk.CTkFrame(self, fg_color=("gray90", "gray17"), corner_radius=12)
        container.pack(fill="x", padx=16, pady=6)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=0)
        container.columnconfigure(2, weight=1)

        # --- LEFT: Source Path Card ---
        src_card = ctk.CTkFrame(container, fg_color="transparent")
        src_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)

        src_title_row = ctk.CTkFrame(src_card, fg_color="transparent")
        src_title_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            src_title_row,
            text="📥 SOURCE FOLDER",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#1f6aa5", "#60a5fa")
        ).pack(side="left")

        # Open in Explorer button
        ctk.CTkButton(
            src_title_row,
            text="📂 Open in Explorer",
            width=120,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=("gray80", "gray25"),
            text_color=("gray30", "gray70"),
            command=lambda: self.open_in_explorer(self.source_dir)
        ).pack(side="right")

        src_input_row = ctk.CTkFrame(src_card, fg_color="transparent")
        src_input_row.pack(fill="x")

        self.src_entry = ctk.CTkEntry(
            src_input_row,
            placeholder_text="Source folder path...",
            font=ctk.CTkFont(size=12)
        )
        self.src_entry.insert(0, self.source_dir)
        self.src_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.src_entry.bind("<Return>", lambda e: self.on_source_path_entered())

        browse_src_btn = ctk.CTkButton(
            src_input_row,
            text="📁 Browse",
            width=80,
            height=30,
            command=self.browse_source
        )
        browse_src_btn.pack(side="left")

        # Source quick shortcuts
        src_shortcuts = ctk.CTkFrame(src_card, fg_color="transparent")
        src_shortcuts.pack(fill="x", pady=(6, 0))

        ctk.CTkLabel(
            src_shortcuts,
            text="Quick:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray"
        ).pack(side="left", padx=(0, 4))

        system_folders = get_system_folders()
        for name in ["Downloads", "Desktop", "Documents", "Pictures"]:
            if name in system_folders:
                p = system_folders[name]
                btn = ctk.CTkButton(
                    src_shortcuts,
                    text=name,
                    width=65,
                    height=22,
                    font=ctk.CTkFont(size=11),
                    fg_color=("gray85", "gray25"),
                    hover_color=("gray75", "gray35"),
                    text_color=("black", "white"),
                    command=lambda path=p: self.set_source_dir(path)
                )
                btn.pack(side="left", padx=2)

        # --- CENTER: Swap Button ---
        swap_frame = ctk.CTkFrame(container, fg_color="transparent")
        swap_frame.grid(row=0, column=1, padx=6, pady=8)

        swap_btn = ctk.CTkButton(
            swap_frame,
            text="⇄\nSwap",
            width=50,
            height=54,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("gray80", "gray25"),
            hover_color=("#1f6aa5", "#2563eb"),
            text_color=("black", "white"),
            command=self.swap_folders
        )
        swap_btn.pack()

        # --- RIGHT: Destination Path Card ---
        dest_card = ctk.CTkFrame(container, fg_color="transparent")
        dest_card.grid(row=0, column=2, sticky="nsew", padx=10, pady=8)

        dest_title_row = ctk.CTkFrame(dest_card, fg_color="transparent")
        dest_title_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            dest_title_row,
            text="📤 DESTINATION FOLDER",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#2fa572", "#34d399")
        ).pack(side="left")

        # Open in Explorer button
        ctk.CTkButton(
            dest_title_row,
            text="📂 Open in Explorer",
            width=120,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=("gray80", "gray25"),
            text_color=("gray30", "gray70"),
            command=lambda: self.open_in_explorer(self.dest_dir)
        ).pack(side="right")

        # Add to favorites button
        ctk.CTkButton(
            dest_title_row,
            text="⭐ Save Favorite",
            width=110,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=("gray80", "gray25"),
            text_color=("#d97706", "#f59e0b"),
            command=self.save_current_dest_as_favorite
        ).pack(side="right", padx=4)

        dest_input_row = ctk.CTkFrame(dest_card, fg_color="transparent")
        dest_input_row.pack(fill="x")

        self.dest_entry = ctk.CTkEntry(
            dest_input_row,
            placeholder_text="Destination folder path...",
            font=ctk.CTkFont(size=12)
        )
        self.dest_entry.insert(0, self.dest_dir)
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.dest_entry.bind("<Return>", lambda e: self.on_dest_path_entered())

        browse_dest_btn = ctk.CTkButton(
            dest_input_row,
            text="📁 Browse",
            width=80,
            height=30,
            fg_color=("#2fa572", "#10b981"),
            hover_color=("#25875c", "#059669"),
            command=self.browse_dest
        )
        browse_dest_btn.pack(side="left")

        # Destination favorites row
        self.dest_favorites_frame = ctk.CTkFrame(dest_card, fg_color="transparent")
        self.dest_favorites_frame.pack(fill="x", pady=(6, 0))
        self.render_dest_favorites()

    def render_dest_favorites(self):
        """Render favorite chips for destinations."""
        for widget in self.dest_favorites_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.dest_favorites_frame,
            text="Favorites:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray"
        ).pack(side="left", padx=(0, 4))

        favs = self.config_mgr.get("favorites", [])
        for fav in favs[:6]:
            name = fav.get("name", "Folder")
            path = fav.get("path", "")
            if not os.path.exists(path):
                continue
            btn = ctk.CTkButton(
                self.dest_favorites_frame,
                text=name,
                width=65,
                height=22,
                font=ctk.CTkFont(size=11),
                fg_color=("gray85", "gray25"),
                hover_color=("gray75", "gray35"),
                text_color=("black", "white"),
                command=lambda p=path: self.set_dest_dir(p)
            )
            btn.pack(side="left", padx=2)

    def create_main_content(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=16, pady=6)

        # 3 columns: Left (Source), Middle (Actions), Right (Destination)
        main_frame.columnconfigure(0, weight=10)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=8)
        main_frame.rowconfigure(0, weight=1)

        # --- LEFT PANE: Source Files List ---
        self.create_source_pane(main_frame)

        # --- CENTER PANE: Action Hub ---
        self.create_action_hub(main_frame)

        # --- RIGHT PANE: Destination Preview & Drop Target ---
        self.create_destination_pane(main_frame)

    def create_source_pane(self, parent):
        source_frame = ctk.CTkFrame(parent, corner_radius=10)
        source_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        # Top search & filter bar
        filter_bar = ctk.CTkFrame(source_frame, fg_color="transparent")
        filter_bar.pack(fill="x", padx=10, pady=(10, 6))

        # Search box
        self.search_entry = ctk.CTkEntry(
            filter_bar,
            placeholder_text="🔍 Filter files by name...",
            height=30,
            font=ctk.CTkFont(size=12)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda e: self.on_search_changed())

        # Category pills
        cats_frame = ctk.CTkFrame(source_frame, fg_color="transparent")
        cats_frame.pack(fill="x", padx=10, pady=(0, 6))

        self.cat_buttons = {}
        for cat in ["All", "Documents", "Images", "Videos", "Audio", "Archives", "Code"]:
            btn = ctk.CTkButton(
                cats_frame,
                text=cat,
                width=55,
                height=24,
                font=ctk.CTkFont(size=11),
                fg_color=("#1f6aa5", "#2563eb") if cat == "All" else ("gray85", "gray25"),
                hover_color=("#1a5276", "#1d4ed8"),
                text_color="white" if cat == "All" else ("black", "white"),
                command=lambda c=cat: self.select_category(c)
            )
            btn.pack(side="left", padx=2)
            self.cat_buttons[cat] = btn

        # Selection Control Row (Option to select one or more files)
        sel_row = ctk.CTkFrame(source_frame, fg_color="transparent")
        sel_row.pack(fill="x", padx=10, pady=(0, 4))

        # 1. Native Windows Multi-File Picker Button
        ctk.CTkButton(
            sel_row,
            text="📑 Pick Files...",
            width=92,
            height=24,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#1f6aa5", "#2563eb"),
            hover_color=("#1a5276", "#1d4ed8"),
            command=self.open_multi_file_picker
        ).pack(side="left", padx=(0, 4))

        # 2. Select All
        ctk.CTkButton(
            sel_row,
            text="☑ All",
            width=50,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
            text_color=("black", "white"),
            command=self.select_all_source
        ).pack(side="left", padx=(0, 4))

        # 3. Clear All
        ctk.CTkButton(
            sel_row,
            text="☐ Clear",
            width=54,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
            text_color=("black", "white"),
            command=self.clear_source_selection
        ).pack(side="left", padx=(0, 4))

        # 4. Invert
        ctk.CTkButton(
            sel_row,
            text="🔄 Invert",
            width=54,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
            text_color=("black", "white"),
            command=self.invert_source_selection
        ).pack(side="left", padx=(0, 4))

        # 5. Select by extension
        ctk.CTkButton(
            sel_row,
            text="🎯 By Type...",
            width=70,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
            text_color=("black", "white"),
            command=self.select_by_type_dialog
        ).pack(side="left")

        # Selection Count Badge
        self.sel_count_label = ctk.CTkLabel(
            sel_row,
            text="0 selected",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#1f6aa5", "#60a5fa")
        )
        self.sel_count_label.pack(side="right")

        # Treeview for source files with checkbox column
        tree_container = tk.Frame(source_frame, bg="#1e1e1e" if self.current_theme == "dark" else "#ffffff")
        tree_container.pack(fill="both", expand=True, padx=10, pady=4)

        columns = ("check", "name", "size", "type", "date")
        self.src_tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            style="Custom.Treeview",
            selectmode="extended"
        )

        self.src_tree.heading("check", text="☑", command=self.toggle_all_checks)
        self.src_tree.heading("name", text="File Name", command=lambda: self.sort_tree("Name"))
        self.src_tree.heading("size", text="Size", command=lambda: self.sort_tree("Size"))
        self.src_tree.heading("type", text="Type", command=lambda: self.sort_tree("Type"))
        self.src_tree.heading("date", text="Date Modified", command=lambda: self.sort_tree("Date"))

        self.src_tree.column("check", width=36, anchor="center")
        self.src_tree.column("name", width=210, anchor="w")
        self.src_tree.column("size", width=75, anchor="e")
        self.src_tree.column("type", width=80, anchor="w")
        self.src_tree.column("date", width=120, anchor="center")

        # Scrollbar
        src_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.src_tree.yview)
        self.src_tree.configure(yscrollcommand=src_scroll.set)

        self.src_tree.pack(side="left", fill="both", expand=True)
        src_scroll.pack(side="right", fill="y")

        # Bindings
        self.src_tree.bind("<Button-1>", self.on_tree_click)
        self.src_tree.bind("<space>", lambda e: self.toggle_focused_item_check())
        self.src_tree.bind("<<TreeviewSelect>>", lambda e: self.update_selection_count())
        self.src_tree.bind("<Double-1>", lambda e: self.on_source_item_double_click())
        self.src_tree.bind("<Button-3>", self.show_source_context_menu)

        # Drag and Drop support on source pane
        self.src_tree.drop_target_register(DND_FILES)
        self.src_tree.dnd_bind("<<Drop>>", self.on_source_drop)

        # Bottom info bar of source pane
        src_bottom = ctk.CTkFrame(source_frame, fg_color="transparent")
        src_bottom.pack(fill="x", padx=10, pady=(4, 8))

        self.src_summary_label = ctk.CTkLabel(
            src_bottom,
            text="0 items",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.src_summary_label.pack(side="left")

        ctk.CTkLabel(
            src_bottom,
            text="💡 Tip: Double-click to open | Drag files here",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="gray"
        ).pack(side="right")

    def create_action_hub(self, parent):
        hub_frame = ctk.CTkFrame(parent, fg_color="transparent")
        hub_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=20)

        # Centered action buttons container
        hub_center = ctk.CTkFrame(hub_frame, fg_color="transparent")
        hub_center.pack(expand=True)

        ctk.CTkLabel(
            hub_center,
            text="ACTIONS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray"
        ).pack(pady=(0, 10))

        # 1. Big MOVE Button
        self.move_btn = ctk.CTkButton(
            hub_center,
            text="➡️ MOVE\nSelected",
            width=135,
            height=58,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#1f6aa5", "#2563eb"),
            hover_color=("#1a5276", "#1d4ed8"),
            command=self.transfer_move
        )
        self.move_btn.pack(pady=6)

        # 2. COPY Button
        self.copy_btn = ctk.CTkButton(
            hub_center,
            text="📋 COPY\nSelected",
            width=135,
            height=46,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#2fa572", "#10b981"),
            hover_color=("#25875c", "#059669"),
            command=self.transfer_copy
        )
        self.copy_btn.pack(pady=6)

        # 3. UNDO Button
        self.undo_btn = ctk.CTkButton(
            hub_center,
            text="↩️ UNDO\nLast Move",
            width=135,
            height=44,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#d97706", "#f59e0b"),
            hover_color=("#b45309", "#d97706"),
            command=self.quick_undo
        )
        self.undo_btn.pack(pady=6)

        # Divider
        ctk.CTkFrame(hub_center, height=2, fg_color=("gray80", "gray25")).pack(fill="x", pady=12)

        # Conflict resolution options
        ctk.CTkLabel(
            hub_center,
            text="If file exists:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray"
        ).pack()

        self.conflict_var = ctk.StringVar(value=self.config_mgr.get("conflict_mode", "rename"))
        conflict_menu = ctk.CTkOptionMenu(
            hub_center,
            values=["rename", "overwrite", "skip"],
            variable=self.conflict_var,
            width=135,
            height=28,
            command=self.on_conflict_mode_changed
        )
        conflict_menu.pack(pady=(4, 10))

        # Auto refresh checkbox
        self.auto_refresh_var = ctk.BooleanVar(value=self.config_mgr.get("auto_refresh", True))
        auto_chk = ctk.CTkCheckBox(
            hub_center,
            text="Auto refresh",
            font=ctk.CTkFont(size=11),
            variable=self.auto_refresh_var,
            command=lambda: self.config_mgr.set("auto_refresh", self.auto_refresh_var.get())
        )
        auto_chk.pack(pady=4)

    def create_destination_pane(self, parent):
        dest_frame = ctk.CTkFrame(parent, corner_radius=10)
        dest_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        # Header of destination pane
        dest_header = ctk.CTkFrame(dest_frame, fg_color="transparent")
        dest_header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            dest_header,
            text="Destination Preview & Drop Zone",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left")

        # Refresh button
        ctk.CTkButton(
            dest_header,
            text="🔄 Refresh",
            width=75,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
            text_color=("black", "white"),
            command=self.refresh_dest
        ).pack(side="right")

        # Drop target banner
        drop_banner = ctk.CTkFrame(dest_frame, fg_color=("#e0f2fe", "#1e3a5f"), corner_radius=6)
        drop_banner.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            drop_banner,
            text="📥 Drag & drop files directly here to transfer immediately!",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0369a1", "#7dd3fc")
        ).pack(pady=6)

        # Treeview for destination preview
        dest_tree_container = tk.Frame(dest_frame, bg="#1e1e1e" if self.current_theme == "dark" else "#ffffff")
        dest_tree_container.pack(fill="both", expand=True, padx=10, pady=4)

        columns = ("name", "size", "date")
        self.dest_tree = ttk.Treeview(
            dest_tree_container,
            columns=columns,
            show="headings",
            style="Custom.Treeview"
        )

        self.dest_tree.heading("name", text="File Name")
        self.dest_tree.heading("size", text="Size")
        self.dest_tree.heading("date", text="Date Modified")

        self.dest_tree.column("name", width=220, anchor="w")
        self.dest_tree.column("size", width=75, anchor="e")
        self.dest_tree.column("date", width=120, anchor="center")

        dest_scroll = ttk.Scrollbar(dest_tree_container, orient="vertical", command=self.dest_tree.yview)
        self.dest_tree.configure(yscrollcommand=dest_scroll.set)

        self.dest_tree.pack(side="left", fill="both", expand=True)
        dest_scroll.pack(side="right", fill="y")

        self.dest_tree.bind("<Double-1>", lambda e: self.on_dest_item_double_click())

        # Drop event on destination tree & banner
        self.dest_tree.drop_target_register(DND_FILES)
        self.dest_tree.dnd_bind("<<Drop>>", self.on_destination_drop)

        drop_banner.drop_target_register(DND_FILES)
        drop_banner.dnd_bind("<<Drop>>", self.on_destination_drop)

        # Bottom info bar of destination pane
        dest_bottom = ctk.CTkFrame(dest_frame, fg_color="transparent")
        dest_bottom.pack(fill="x", padx=10, pady=(4, 8))

        self.dest_summary_label = ctk.CTkLabel(
            dest_bottom,
            text="0 items",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.dest_summary_label.pack(side="left")

        self.dest_disk_label = ctk.CTkLabel(
            dest_bottom,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.dest_disk_label.pack(side="right")

    def create_status_bar(self):
        status_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray17"), corner_radius=0, height=36)
        status_frame.pack(fill="x", side="bottom")

        # Left status text
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Ready. Select files on the left and click 'MOVE' or drag & drop files.",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=16, pady=6)

        # Right progress bar
        self.progress_bar = ctk.CTkProgressBar(
            status_frame,
            width=220,
            height=12,
            mode="determinate"
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right", padx=16, pady=6)

    # ================= UI Actions & Event Handlers =================

    def toggle_theme(self):
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.current_theme = new_theme
        ctk.set_appearance_mode(new_theme.capitalize())
        self.config_mgr.set("theme", new_theme)
        self.theme_btn.configure(text="☀️ Light Mode" if new_theme == "dark" else "🌙 Dark Mode")
        self.update_tree_theme()

    def browse_source(self):
        folder = filedialog.askdirectory(initialdir=self.source_dir, title="Select Source Folder")
        if folder:
            self.set_source_dir(folder)

    def browse_dest(self):
        folder = filedialog.askdirectory(initialdir=self.dest_dir, title="Select Destination Folder")
        if folder:
            self.set_dest_dir(folder)

    def set_source_dir(self, path: str):
        if not os.path.exists(path):
            messagebox.showerror("Folder Not Found", f"Folder does not exist:\n{path}")
            return
        self.source_dir = os.path.normpath(path)
        self.src_entry.delete(0, "end")
        self.src_entry.insert(0, self.source_dir)
        self.config_mgr.set("source_folder", self.source_dir)
        self.refresh_source()

    def set_dest_dir(self, path: str):
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create folder:\n{e}")
                return
        self.dest_dir = os.path.normpath(path)
        self.dest_entry.delete(0, "end")
        self.dest_entry.insert(0, self.dest_dir)
        self.config_mgr.set("destination_folder", self.dest_dir)
        self.refresh_dest()

    def on_source_path_entered(self):
        path = self.src_entry.get().strip()
        if os.path.exists(path):
            self.set_source_dir(path)
        else:
            messagebox.showwarning("Invalid Path", f"Path does not exist:\n{path}")

    def on_dest_path_entered(self):
        path = self.dest_entry.get().strip()
        if os.path.exists(path):
            self.set_dest_dir(path)
        else:
            messagebox.showwarning("Invalid Path", f"Path does not exist:\n{path}")

    def swap_folders(self):
        old_src = self.source_dir
        old_dst = self.dest_dir
        self.set_source_dir(old_dst)
        self.set_dest_dir(old_src)
        self.set_status(f"Swapped folders! Source is now: {os.path.basename(self.source_dir)}")

    def save_current_dest_as_favorite(self):
        folder_name = os.path.basename(self.dest_dir) or self.dest_dir
        self.config_mgr.add_favorite(folder_name, self.dest_dir)
        self.render_dest_favorites()
        self.set_status(f"Added '{folder_name}' to Destination Favorites! ⭐")

    def open_in_explorer(self, folder_path: str):
        if os.path.exists(folder_path):
            try:
                os.startfile(folder_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open explorer:\n{e}")
        else:
            messagebox.showwarning("Warning", f"Folder does not exist:\n{folder_path}")

    def select_category(self, category: str):
        self.current_category = category
        for cat, btn in self.cat_buttons.items():
            if cat == category:
                btn.configure(
                    fg_color=("#1f6aa5", "#2563eb"),
                    text_color="white"
                )
            else:
                btn.configure(
                    fg_color=("gray85", "gray25"),
                    text_color=("black", "white")
                )
        self.populate_source_tree()

    def on_search_changed(self):
        self.search_query = self.search_entry.get().strip().lower()
        self.populate_source_tree()

    def on_conflict_mode_changed(self, mode: str):
        self.config_mgr.set("conflict_mode", mode)

    def set_status(self, text: str):
        self.status_label.configure(text=text)

    # ================= Refreshing & Scanning =================

    def refresh_source(self):
        self.source_items = []
        if not os.path.isdir(self.source_dir):
            return

        try:
            with os.scandir(self.source_dir) as entries:
                for entry in entries:
                    try:
                        stat = entry.stat()
                        is_dir = entry.is_dir()
                        size = stat.st_size if not is_dir else 0
                        mtime = stat.st_mtime
                        ext = os.path.splitext(entry.name)[1].lower() if not is_dir else "Folder"

                        self.source_items.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": is_dir,
                            "size": size,
                            "size_str": "—" if is_dir else format_size(size),
                            "ext": ext,
                            "mtime": mtime,
                            "mtime_str": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                        })
                    except (PermissionError, FileNotFoundError):
                        continue
        except Exception as e:
            self.set_status(f"Error reading source folder: {e}")

        self.populate_source_tree()

    def populate_source_tree(self):
        # Clear current tree
        for item in self.src_tree.get_children():
            self.src_tree.delete(item)

        allowed_exts = FILE_CATEGORIES.get(self.current_category, set())
        filtered = []

        for it in self.source_items:
            # Search filter
            if self.search_query and self.search_query not in it["name"].lower():
                continue

            # Category filter
            if self.current_category != "All":
                if it["is_dir"]:
                    continue
                if it["ext"] not in allowed_exts:
                    continue

            filtered.append(it)

        # Sort items
        def sort_key(it):
            if self.sort_column == "Name":
                return (not it["is_dir"], it["name"].lower())
            elif self.sort_column == "Size":
                return (not it["is_dir"], it["size"])
            elif self.sort_column == "Type":
                return (not it["is_dir"], it["ext"])
            elif self.sort_column == "Date":
                return (not it["is_dir"], it["mtime"])
            return it["name"]

        filtered.sort(key=sort_key, reverse=self.sort_reverse)

        total_bytes = 0
        for it in filtered:
            icon = "📁 " if it["is_dir"] else "📄 "
            type_str = "Folder" if it["is_dir"] else (it["ext"].upper().lstrip(".") or "File")
            chk = "☑" if it["path"] in self.checked_items else "☐"
            self.src_tree.insert(
                "",
                "end",
                iid=it["path"],
                values=(chk, f"{icon}{it['name']}", it["size_str"], type_str, it["mtime_str"])
            )
            total_bytes += it["size"]

        self.src_summary_label.configure(
            text=f"{len(filtered)} items shown ({format_size(total_bytes)})"
        )
        self.update_selection_count()

    def sort_tree(self, col_name: str):
        if self.sort_column == col_name:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col_name
            self.sort_reverse = False
        self.populate_source_tree()

    def refresh_dest(self):
        for item in self.dest_tree.get_children():
            self.dest_tree.delete(item)

        if not os.path.isdir(self.dest_dir):
            return

        count = 0
        try:
            with os.scandir(self.dest_dir) as entries:
                items = []
                for entry in entries:
                    try:
                        stat = entry.stat()
                        is_dir = entry.is_dir()
                        size = stat.st_size if not is_dir else 0
                        mtime = stat.st_mtime
                        items.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": is_dir,
                            "size_str": "—" if is_dir else format_size(size),
                            "mtime_str": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                            "mtime": mtime
                        })
                    except (PermissionError, FileNotFoundError):
                        continue

                items.sort(key=lambda x: (not x["is_dir"], x["mtime"]), reverse=True)
                count = len(items)
                for it in items:
                    icon = "📁 " if it["is_dir"] else "📄 "
                    self.dest_tree.insert(
                        "",
                        "end",
                        iid=it["path"],
                        values=(f"{icon}{it['name']}", it["size_str"], it["mtime_str"])
                    )
        except Exception as e:
            self.set_status(f"Error reading destination folder: {e}")

        self.dest_summary_label.configure(text=f"{count} items in destination")

        # Disk space
        try:
            usage = shutil.disk_usage(self.dest_dir)
            free_gb = usage.free / (1024 ** 3)
            self.dest_disk_label.configure(text=f"Drive free: {free_gb:.1f} GB")
        except Exception:
            self.dest_disk_label.configure(text="")

    # ================= Selection Helpers (Select One or More Files) =================

    def on_tree_click(self, event):
        item = self.src_tree.identify_row(event.y)
        col = self.src_tree.identify_column(event.x)
        if not item:
            return

        # If user clicks specifically on the checkmark column (#1)
        if col == "#1":
            self.toggle_item_check(item)
            return "break"
        else:
            # If user clicked without Ctrl or Shift, also toggle check for ease on trackpads
            if not (event.state & 0x0004 or event.state & 0x0001):  # No Ctrl and No Shift
                self.toggle_item_check(item)
                if item in self.checked_items:
                    self.src_tree.selection_add(item)
                else:
                    self.src_tree.selection_remove(item)

    def toggle_focused_item_check(self):
        focused = self.src_tree.focus()
        if focused:
            self.toggle_item_check(focused)

    def toggle_item_check(self, path: str):
        if path in self.checked_items:
            self.checked_items.remove(path)
            new_val = "☐"
            if path in self.src_tree.selection():
                self.src_tree.selection_remove(path)
        else:
            self.checked_items.add(path)
            new_val = "☑"
            self.src_tree.selection_add(path)

        if self.src_tree.exists(path):
            current_vals = list(self.src_tree.item(path, "values"))
            if current_vals:
                current_vals[0] = new_val
                self.src_tree.item(path, values=current_vals)

        self.update_selection_count()

    def toggle_all_checks(self):
        visible_items = self.src_tree.get_children()
        if not visible_items:
            return
        all_checked = all(it in self.checked_items for it in visible_items)
        if all_checked:
            self.clear_source_selection()
        else:
            self.select_all_source()

    def select_all_source(self):
        for item in self.src_tree.get_children():
            self.checked_items.add(item)
            current_vals = list(self.src_tree.item(item, "values"))
            if current_vals:
                current_vals[0] = "☑"
                self.src_tree.item(item, values=current_vals)
            self.src_tree.selection_add(item)
        self.update_selection_count()

    def clear_source_selection(self):
        self.checked_items.clear()
        for item in self.src_tree.get_children():
            current_vals = list(self.src_tree.item(item, "values"))
            if current_vals:
                current_vals[0] = "☐"
                self.src_tree.item(item, values=current_vals)
        self.src_tree.selection_remove(self.src_tree.selection())
        self.update_selection_count()

    def invert_source_selection(self):
        for item in self.src_tree.get_children():
            if item in self.checked_items:
                self.checked_items.remove(item)
                new_val = "☐"
                self.src_tree.selection_remove(item)
            else:
                self.checked_items.add(item)
                new_val = "☑"
                self.src_tree.selection_add(item)
            current_vals = list(self.src_tree.item(item, "values"))
            if current_vals:
                current_vals[0] = new_val
                self.src_tree.item(item, values=current_vals)
        self.update_selection_count()

    def open_multi_file_picker(self):
        """Allows picking one or multiple files directly using native Windows File Picker."""
        picked = filedialog.askopenfilenames(
            initialdir=self.source_dir,
            title="Select One or More Files to Transfer"
        )
        if not picked:
            return

        first_dir = os.path.dirname(picked[0])
        if os.path.normpath(first_dir) != os.path.normpath(self.source_dir):
            self.set_source_dir(first_dir)

        # Check all picked files
        for f in picked:
            norm_path = os.path.normpath(f)
            self.checked_items.add(norm_path)
            if self.src_tree.exists(norm_path):
                current_vals = list(self.src_tree.item(norm_path, "values"))
                if current_vals:
                    current_vals[0] = "☑"
                    self.src_tree.item(norm_path, values=current_vals)
                self.src_tree.selection_add(norm_path)

        self.update_selection_count()
        self.set_status(f"Selected {len(picked)} file(s) via file picker. Click 'MOVE' to transfer!")

    def select_by_type_dialog(self):
        """Pop up a menu to select all files of a specific extension with 1 click."""
        exts = sorted(list({os.path.splitext(it["name"])[1].lower() for it in self.source_items if not it["is_dir"] and os.path.splitext(it["name"])[1]}))
        if not exts:
            messagebox.showinfo("No Extensions", "No files with extensions found in the current folder.")
            return

        menu = tk.Menu(self, tearoff=0)
        for ext in exts:
            count = sum(1 for it in self.source_items if not it["is_dir"] and os.path.splitext(it["name"])[1].lower() == ext)
            label = f"Select all {ext} files ({count})"
            menu.add_command(label=label, command=lambda e=ext: self.select_files_by_extension(e))

        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        menu.tk_popup(x, y)

    def select_files_by_extension(self, target_ext: str):
        target_ext = target_ext.lower()
        count = 0
        for item in self.src_tree.get_children():
            if os.path.splitext(item)[1].lower() == target_ext:
                self.checked_items.add(item)
                current_vals = list(self.src_tree.item(item, "values"))
                if current_vals:
                    current_vals[0] = "☑"
                    self.src_tree.item(item, values=current_vals)
                self.src_tree.selection_add(item)
                count += 1
        self.update_selection_count()
        self.set_status(f"Checked {count} '{target_ext}' files!")

    def get_selected_items(self) -> list:
        """Returns list of all checked or selected file paths."""
        combined = set(self.checked_items)
        combined.update(self.src_tree.selection())
        return [p for p in combined if os.path.exists(p)]

    def update_selection_count(self):
        combined = set(self.checked_items)
        combined.update(self.src_tree.selection())
        count = len(combined)

        if count == 0:
            self.sel_count_label.configure(text="0 selected")
            return

        total_bytes = 0
        for path in combined:
            if os.path.isfile(path):
                try:
                    total_bytes += os.path.getsize(path)
                except Exception:
                    pass

        self.sel_count_label.configure(
            text=f"☑ {count} selected ({format_size(total_bytes)})"
        )

    # ================= Double Click & Context Menus =================

    def on_source_item_double_click(self):
        selected = self.src_tree.selection()
        if not selected:
            return
        path = selected[0]
        if os.path.isdir(path):
            self.set_source_dir(path)
        else:
            try:
                os.startfile(path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file:\n{e}")

    def on_dest_item_double_click(self):
        selected = self.dest_tree.selection()
        if not selected:
            return
        path = selected[0]
        if os.path.isdir(path):
            self.set_dest_dir(path)
        else:
            try:
                os.startfile(path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file:\n{e}")

    def show_source_context_menu(self, event):
        item = self.src_tree.identify_row(event.y)
        if item:
            if item not in self.src_tree.selection():
                self.src_tree.selection_set(item)
            self.update_selection_count()

            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="➡️ Move to Destination", command=self.transfer_move)
            menu.add_command(label="📋 Copy to Destination", command=self.transfer_copy)
            menu.add_separator()
            menu.add_command(label="Open File", command=self.on_source_item_double_click)
            menu.add_command(label="Show in Explorer", command=lambda: self.show_item_in_explorer(item))
            menu.tk_popup(event.x_root, event.y_root)

    def show_item_in_explorer(self, file_path: str):
        if os.path.exists(file_path):
            os.system(f'explorer /select,"{os.path.normpath(file_path)}"')

    # ================= Drag & Drop Handlers =================

    def on_source_drop(self, event):
        paths = self.tk.splitlist(event.data)
        if not paths:
            return

        first = paths[0]
        if os.path.isdir(first) and len(paths) == 1:
            # Set source folder to dropped folder
            self.set_source_dir(first)
            self.set_status(f"Loaded source folder: {first}")
        else:
            # Files dropped on source pane
            parent_dir = os.path.dirname(first)
            if parent_dir and os.path.exists(parent_dir):
                self.set_source_dir(parent_dir)
                # Select the dropped items
                self.after(200, lambda: self.select_specific_paths(paths))
            self.set_status(f"Loaded {len(paths)} dropped item(s) in Source.")

    def on_destination_drop(self, event):
        paths = self.tk.splitlist(event.data)
        if not paths:
            return

        # Direct transfer of dropped files into destination folder!
        confirm = messagebox.askyesno(
            "Transfer Dropped Files",
            f"Transfer {len(paths)} item(s) directly to:\n{self.dest_dir}\n\nClick Yes to Move, or No to Cancel."
        )
        if confirm:
            self.run_transfer_thread(list(paths), action="move")

    def select_specific_paths(self, paths):
        for p in paths:
            norm = os.path.normpath(p)
            for item in self.src_tree.get_children():
                if os.path.normpath(item) == norm:
                    self.src_tree.selection_add(item)
        self.update_selection_count()

    # ================= Transfer Operations (Move, Copy, Undo) =================

    def transfer_move(self):
        selected = self.get_selected_items()
        if not selected:
            messagebox.showinfo(
                "No Files Selected",
                "Please select one or more files to move.\n\n"
                "💡 Options to select files:\n"
                "• Click any row or checkbox to check/uncheck files\n"
                "• Click '📑 Pick Files...' to choose files via Windows dialog\n"
                "• Click '☑ All' to select all files\n"
                "• Click '🎯 By Type...' to select by extension (e.g. .pdf, .jpg)"
            )
            return

        if os.path.normpath(self.source_dir) == os.path.normpath(self.dest_dir):
            messagebox.showwarning("Same Folder", "Source and Destination folders are the same! Please pick a different destination.")
            return

        self.run_transfer_thread(selected, action="move")

    def transfer_copy(self):
        selected = self.get_selected_items()
        if not selected:
            messagebox.showinfo(
                "No Files Selected",
                "Please select one or more files to copy.\n\n"
                "💡 Click any file's checkbox or use '📑 Pick Files...' to choose."
            )
            return

        if os.path.normpath(self.source_dir) == os.path.normpath(self.dest_dir):
            messagebox.showwarning("Same Folder", "Source and Destination folders are the same!")
            return

        self.run_transfer_thread(selected, action="copy")

    def run_transfer_thread(self, items: list, action: str):
        if self.is_transferring:
            messagebox.showwarning("Busy", "A transfer is already in progress. Please wait.")
            return

        self.is_transferring = True
        self.set_buttons_state("disabled")
        self.progress_bar.set(0)
        self.set_status(f"Starting {action} of {len(items)} item(s)...")

        conflict = self.conflict_var.get()

        def worker():
            def progress(current, total, item_name, percent):
                self.after(0, lambda: self.update_progress(percent, current, total, item_name))

            result = self.engine.execute_transfer(
                items,
                self.dest_dir,
                action=action,
                conflict_mode=conflict,
                progress_callback=progress
            )

            # Record history entry in config
            history_dict = result.to_history_dict()
            self.config_mgr.add_history_entry(history_dict)

            # Complete callback on main thread
            self.after(0, lambda: self.on_transfer_complete(result, action))

        threading.Thread(target=worker, daemon=True).start()

    def update_progress(self, percent: float, current: int, total: int, item_name: str):
        self.progress_bar.set(percent / 100.0)
        self.set_status(f"Transferring ({current}/{total}): {item_name}")

    def on_transfer_complete(self, result, action: str):
        self.is_transferring = False
        self.set_buttons_state("normal")
        self.progress_bar.set(1.0)

        # Remove successfully moved files from checked set
        for src_path, _ in result.transferred_items:
            self.checked_items.discard(src_path)

        # Build notification message
        msg_parts = []
        if result.success_count > 0:
            msg_parts.append(f"Successfully {action}d {result.success_count} item(s) ({format_size(result.total_bytes)})")
        if result.skipped_count > 0:
            msg_parts.append(f"{result.skipped_count} skipped")
        if result.fail_count > 0:
            msg_parts.append(f"{result.fail_count} failed")

        final_msg = " | ".join(msg_parts) if msg_parts else "Transfer complete."
        self.set_status(final_msg)

        if result.fail_count > 0:
            err_details = "\n".join([f"• {os.path.basename(p)}: {err}" for p, err in result.failed_items[:5]])
            messagebox.showwarning("Transfer Warnings", f"Some files could not be transferred:\n\n{err_details}")

        # Refresh folders
        if self.auto_refresh_var.get():
            self.refresh_source()
            self.refresh_dest()

    def quick_undo(self):
        if not self.engine.undo_stack:
            messagebox.showinfo("Undo", "No previous move operation available to undo.")
            return

        last = self.engine.undo_stack[-1]
        items_count = len(last.get("items", []))

        confirm = messagebox.askyesno(
            "Undo Transfer",
            f"Move {items_count} item(s) back to their original source folders?\n\nClick Yes to restore."
        )
        if not confirm:
            return

        restored, failed, errors = self.engine.undo()
        last["undone"] = True
        self.config_mgr.save()

        if restored > 0:
            self.set_status(f"↩️ Successfully restored {restored} item(s) back to original folders!")
            if self.auto_refresh_var.get():
                self.refresh_source()
                self.refresh_dest()
        if failed > 0:
            messagebox.showwarning("Undo Warning", f"{failed} item(s) could not be restored:\n" + "\n".join(errors[:4]))

    def open_history_dialog(self):
        history = self.config_mgr.get("history", [])
        HistoryDialog(self, history, on_undo_callback=self.handle_history_undo)

    def handle_history_undo(self, entry: dict):
        restored, failed, errors = self.engine.undo(entry)
        self.config_mgr.save()
        if restored > 0:
            self.set_status(f"↩️ Restored {restored} files from history log!")
            if self.auto_refresh_var.get():
                self.refresh_source()
                self.refresh_dest()
        if failed > 0:
            messagebox.showwarning("Undo Notice", f"Some files could not be restored:\n" + "\n".join(errors[:3]))

    def set_buttons_state(self, state: str):
        self.move_btn.configure(state=state)
        self.copy_btn.configure(state=state)
        self.undo_btn.configure(state=state)


def main():
    app = FileFlowApp()
    app.mainloop()

if __name__ == "__main__":
    main()
