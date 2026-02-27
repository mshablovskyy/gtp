"""Duplicates tab — SHA-256 exact duplicate scanning and review."""

import threading
from pathlib import Path

import customtkinter as ctk
from send2trash import send2trash

import duplicate_detector
from ui.theme import (
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    GROUPS_PER_PAGE,
    PAD_INNER,
    PAD_OUTER,
    THUMBNAIL_SIZE_SMALL,
)
from ui.widgets import FolderPicker, GroupCard


def _fmt_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


class DuplicatesTab(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._groups: list[duplicate_detector.DuplicateGroup] = []
        self._page = 0
        self._group_cards: list[GroupCard] = []

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)

        row = 0

        # Top bar: folder picker + scan button
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(PAD_OUTER, PAD_INNER))
        top.grid_columnconfigure(0, weight=1)

        self.folder_picker = FolderPicker(top, label_text="Scan Folder:")
        self.folder_picker.grid(row=0, column=0, sticky="ew", padx=(0, PAD_INNER))

        self.scan_btn = ctk.CTkButton(top, text="Scan for Duplicates", width=160, command=self._start_scan)
        self.scan_btn.grid(row=0, column=1)
        row += 1

        # Progress
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(0, 2))
        self.progress_bar.set(0)
        row += 1

        self.status_label = ctk.CTkLabel(self, text="", font=FONT_SMALL, anchor="w")
        self.status_label.grid(row=row, column=0, sticky="w", padx=PAD_OUTER, pady=(0, PAD_INNER))
        row += 1

        # Results scroll area
        self.results_frame = ctk.CTkScrollableFrame(self)
        self.results_frame.grid(row=row, column=0, sticky="nsew", padx=PAD_OUTER, pady=(0, PAD_INNER))
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(row, weight=1)
        row += 1

        # Bottom actions
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(0, PAD_OUTER))

        self.trash_btn = ctk.CTkButton(
            bottom, text="Move Marked to Trash", width=180,
            fg_color="red", hover_color="darkred", command=self._trash_marked
        )
        self.trash_btn.pack(side="left", padx=(0, PAD_INNER))

        self.load_more_btn = ctk.CTkButton(
            bottom, text="Load More...", width=120, command=self._load_more_groups
        )
        self.load_more_btn.pack(side="left")
        self.load_more_btn.configure(state="disabled")

        self.next_btn = ctk.CTkButton(
            bottom, text="Next: Similar Photos →", width=180,
            command=lambda: self.app.tabview.set("Similar Photos"),
        )
        self.next_btn.pack(side="right")

    def show_results(self, groups: list[duplicate_detector.DuplicateGroup]):
        """Accept pre-computed results from the pipeline (no scan needed)."""
        self._clear_results()
        self._on_scan_complete(groups)

    def _start_scan(self):
        folder = self.folder_picker.get()
        if not folder:
            self.status_label.configure(text="Please select a folder to scan.")
            return

        self._cancel_event.clear()
        self.scan_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self._clear_results()
        self.app.set_status("Scanning for duplicates...")

        self._worker = threading.Thread(target=self._scan, args=(folder,), daemon=True)
        self._worker.start()

    def _scan(self, folder: str):
        try:
            groups = duplicate_detector.find_exact_duplicates(
                folder,
                on_progress=self._on_progress,
                cancel_flag=lambda: self._cancel_event.is_set(),
            )
            self.after(0, self._on_scan_complete, groups)
        except Exception as e:
            self.after(0, self._on_scan_error, str(e))

    def _on_progress(self, current: int, total: int, msg: str):
        self.after(0, self._update_progress, current, total, msg)

    def _update_progress(self, current: int, total: int, msg: str):
        if total > 0:
            self.progress_bar.set(current / total)
        self.status_label.configure(text=msg)

    def _on_scan_complete(self, groups: list[duplicate_detector.DuplicateGroup]):
        self._groups = groups
        self._page = 0
        self.scan_btn.configure(state="normal")
        self.progress_bar.set(1.0)

        total_files = sum(len(g.paths) for g in groups)
        reclaimable = sum(g.file_size * (len(g.paths) - 1) for g in groups)

        self.status_label.configure(
            text=f"Found {len(groups)} duplicate groups ({total_files} files, {_fmt_size(reclaimable)} reclaimable)"
        )
        self.app.set_status(f"Found {len(groups)} duplicate groups")
        self._load_more_groups()

    def _on_scan_error(self, error_msg: str):
        self.scan_btn.configure(state="normal")
        self.status_label.configure(text=f"Error: {error_msg}")

    def _clear_results(self):
        for card in self._group_cards:
            card.destroy()
        self._group_cards.clear()

    def _load_more_groups(self):
        start = self._page * GROUPS_PER_PAGE
        end = min(start + GROUPS_PER_PAGE, len(self._groups))

        for i in range(start, end):
            g = self._groups[i]
            header = (
                f"Group {i + 1}: {len(g.paths)} files, "
                f"{_fmt_size(g.file_size)} each  |  SHA-256: {g.sha256[:12]}..."
            )
            card = GroupCard(
                self.results_frame,
                header_text=header,
                file_paths=g.paths,
                thumb_size=THUMBNAIL_SIZE_SMALL,
            )
            card.pack(fill="x", padx=2, pady=(0, PAD_INNER))
            self._group_cards.append(card)

        self._page += 1
        has_more = end < len(self._groups)
        self.load_more_btn.configure(state="normal" if has_more else "disabled")

    def _trash_marked(self):
        files_to_delete: list[Path] = []
        for card in self._group_cards:
            to_del = card.get_files_to_delete()
            to_keep = card.get_files_to_keep()
            # Safety: at least one file must be kept per group
            if to_keep or not to_del:
                files_to_delete.extend(to_del)
            else:
                # Keep the first file, trash the rest
                files_to_delete.extend(to_del[1:])

        if not files_to_delete:
            self.status_label.configure(text="No files marked for deletion.")
            return

        # Confirmation dialog
        dialog = ctk.CTkInputDialog(
            text=f"Move {len(files_to_delete)} files to trash?\nType 'yes' to confirm.",
            title="Confirm Deletion",
        )
        if dialog.get_input() != "yes":
            return

        deleted = 0
        for fpath in files_to_delete:
            try:
                send2trash(str(fpath))
                deleted += 1
            except Exception:
                pass

        self.status_label.configure(text=f"Moved {deleted} files to trash.")
        self.app.set_status(f"Moved {deleted} duplicate files to trash")
