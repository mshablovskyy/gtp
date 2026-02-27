"""Similar Photos tab — perceptual hash scanning and review."""

import threading
from pathlib import Path

import customtkinter as ctk
from send2trash import send2trash

import similarity_detector
from ui.theme import (
    FONT_BODY,
    FONT_SMALL,
    GROUPS_PER_PAGE,
    PAD_INNER,
    PAD_OUTER,
    THUMBNAIL_SIZE_LARGE,
)
from ui.widgets import FolderPicker, GroupCard


class SimilarTab(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._groups: list[similarity_detector.SimilarGroup] = []
        self._page = 0
        self._group_cards: list[GroupCard] = []

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)

        row = 0

        # Top bar: folder picker
        self.folder_picker = FolderPicker(self, label_text="Scan Folder:")
        self.folder_picker.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(PAD_OUTER, PAD_INNER))
        row += 1

        # Options row: threshold slider, hash selector, scan button
        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(0, PAD_INNER))

        ctk.CTkLabel(opts, text="Threshold:", font=FONT_BODY).pack(side="left", padx=(0, PAD_INNER))

        self.threshold_var = ctk.IntVar(value=8)
        self.threshold_label = ctk.CTkLabel(opts, text="8", font=FONT_BODY, width=30)
        self.threshold_label.pack(side="left")

        self.threshold_slider = ctk.CTkSlider(
            opts, from_=0, to=20, number_of_steps=20,
            variable=self.threshold_var, width=200,
            command=self._on_threshold_change,
        )
        self.threshold_slider.pack(side="left", padx=(PAD_INNER, PAD_INNER))

        ctk.CTkLabel(opts, text="Hash:", font=FONT_BODY).pack(side="left", padx=(PAD_INNER, PAD_INNER))

        self.hash_var = ctk.StringVar(value="phash")
        self.hash_menu = ctk.CTkComboBox(
            opts, values=["phash", "dhash", "average_hash", "whash"],
            variable=self.hash_var, width=130, state="readonly",
        )
        self.hash_menu.pack(side="left", padx=(0, PAD_INNER))

        self.scan_btn = ctk.CTkButton(opts, text="Find Similar", width=130, command=self._start_scan)
        self.scan_btn.pack(side="left")
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
            fg_color="red", hover_color="darkred", command=self._trash_marked,
        )
        self.trash_btn.pack(side="left", padx=(0, PAD_INNER))

        self.load_more_btn = ctk.CTkButton(
            bottom, text="Load More...", width=120, command=self._load_more_groups
        )
        self.load_more_btn.pack(side="left")
        self.load_more_btn.configure(state="disabled")

        self.next_btn = ctk.CTkButton(
            bottom, text="Next: Quality Review →", width=180,
            command=lambda: self.app.tabview.set("Quality Review"),
        )
        self.next_btn.pack(side="right")

    def show_results(self, groups: list[similarity_detector.SimilarGroup]):
        """Accept pre-computed results from the pipeline (no scan needed)."""
        self._clear_results()
        self._on_scan_complete(groups)

    def _on_threshold_change(self, value):
        self.threshold_label.configure(text=str(int(value)))

    def _start_scan(self):
        folder = self.folder_picker.get()
        if not folder:
            self.status_label.configure(text="Please select a folder to scan.")
            return

        self._cancel_event.clear()
        self.scan_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self._clear_results()
        self.app.set_status("Scanning for similar photos...")

        self._worker = threading.Thread(target=self._scan, args=(folder,), daemon=True)
        self._worker.start()

    def _scan(self, folder: str):
        try:
            groups = similarity_detector.find_similar_photos(
                folder,
                threshold=self.threshold_var.get(),
                hash_func=self.hash_var.get(),
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

    def _on_scan_complete(self, groups: list[similarity_detector.SimilarGroup]):
        self._groups = groups
        self._page = 0
        self.scan_btn.configure(state="normal")
        self.progress_bar.set(1.0)

        total_images = sum(len(g.members) for g in groups)
        self.status_label.configure(
            text=f"Found {len(groups)} groups of similar photos ({total_images} images)"
        )
        self.app.set_status(f"Found {len(groups)} similar photo groups")
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
            distances = [m.distance for m in g.members]
            min_d, max_d = min(distances), max(distances)

            header = (
                f"Group {i + 1}: {len(g.members)} similar images "
                f"(distance range: {min_d}-{max_d})"
            )
            file_paths = [m.path for m in g.members]
            info_texts = [f"dist: {m.distance}" for m in g.members]

            card = GroupCard(
                self.results_frame,
                header_text=header,
                file_paths=file_paths,
                thumb_size=THUMBNAIL_SIZE_LARGE,
                info_texts=info_texts,
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
            if to_keep or not to_del:
                files_to_delete.extend(to_del)
            else:
                files_to_delete.extend(to_del[1:])

        if not files_to_delete:
            self.status_label.configure(text="No files marked for deletion.")
            return

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
        self.app.set_status(f"Moved {deleted} similar photos to trash")
