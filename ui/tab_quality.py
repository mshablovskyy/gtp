"""Quality Review tab — flags blurry, dark, screenshots, and other junk photos."""

import threading
from pathlib import Path

import customtkinter as ctk
from send2trash import send2trash

import quality_detector
from quality_detector import IssueType
from ui.theme import (
    FONT_BODY,
    FONT_SMALL,
    GROUPS_PER_PAGE,
    PAD_INNER,
    PAD_OUTER,
    THUMBNAIL_SIZE_LARGE,
)
from ui.widgets import FolderPicker, ThumbnailCard, load_thumbnail


class QualityIssueCard(ctk.CTkFrame):
    """A card for a single flagged image with preview, issue info, and keep/delete."""

    def __init__(self, parent, issue: quality_detector.QualityIssue, **kwargs):
        super().__init__(parent, **kwargs)
        self.issue = issue
        self.file_path = issue.path

        # Color-code by issue type
        type_colors = {
            IssueType.BLURRY: "#8B6914",
            IssueType.DARK: "#333333",
            IssueType.OVEREXPOSED: "#AAAAAA",
            IssueType.SCREENSHOT: "#4169E1",
            IssueType.CORRUPT: "#CC0000",
            IssueType.TINY: "#666666",
        }

        self.grid_columnconfigure(1, weight=1)

        # Thumbnail
        pil_img = load_thumbnail(issue.path, THUMBNAIL_SIZE_LARGE)
        self._ctk_image = ctk.CTkImage(light_image=pil_img, size=THUMBNAIL_SIZE_LARGE)
        img_label = ctk.CTkLabel(self, image=self._ctk_image, text="")
        img_label.grid(row=0, column=0, rowspan=3, padx=PAD_INNER, pady=PAD_INNER)

        # Issue type badge
        badge_color = type_colors.get(issue.issue, "gray")
        self.type_label = ctk.CTkLabel(
            self, text=f"  {issue.issue.value}  ", font=FONT_BODY,
            fg_color=badge_color, corner_radius=6, text_color="white",
        )
        self.type_label.grid(row=0, column=1, sticky="w", padx=PAD_INNER, pady=(PAD_INNER, 2))

        # Filename + detail
        name = issue.path.name
        if len(name) > 50:
            name = name[:47] + "..."
        self.name_label = ctk.CTkLabel(self, text=name, font=FONT_BODY, anchor="w")
        self.name_label.grid(row=1, column=1, sticky="w", padx=PAD_INNER)

        self.detail_label = ctk.CTkLabel(
            self, text=issue.detail, font=FONT_SMALL, text_color="gray", anchor="w"
        )
        self.detail_label.grid(row=2, column=1, sticky="w", padx=PAD_INNER, pady=(0, PAD_INNER))

        # Confidence
        confidence_pct = int(issue.score * 100)
        self.score_label = ctk.CTkLabel(
            self, text=f"Confidence: {confidence_pct}%", font=FONT_SMALL, anchor="e"
        )
        self.score_label.grid(row=0, column=2, padx=PAD_INNER, pady=(PAD_INNER, 2))

        # Keep/Delete toggle — default to Delete for junk
        self._marked_for_deletion = True
        self.toggle_btn = ctk.CTkButton(
            self, text="Delete", width=80, height=30,
            fg_color="red", hover_color="darkred",
            command=self._toggle,
        )
        self.toggle_btn.grid(row=1, column=2, rowspan=2, padx=PAD_INNER, pady=(0, PAD_INNER))

    def _toggle(self):
        self._marked_for_deletion = not self._marked_for_deletion
        if self._marked_for_deletion:
            self.toggle_btn.configure(text="Delete", fg_color="red", hover_color="darkred")
        else:
            self.toggle_btn.configure(text="Keep", fg_color="green", hover_color="darkgreen")

    @property
    def marked_for_deletion(self) -> bool:
        return self._marked_for_deletion


class QualityTab(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._issues: list[quality_detector.QualityIssue] = []
        self._page = 0
        self._cards: list[QualityIssueCard] = []

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)

        row = 0

        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(PAD_OUTER, PAD_INNER))
        top.grid_columnconfigure(0, weight=1)

        self.folder_picker = FolderPicker(top, label_text="Scan Folder:")
        self.folder_picker.grid(row=0, column=0, sticky="ew", padx=(0, PAD_INNER))

        self.scan_btn = ctk.CTkButton(top, text="Scan Quality", width=140, command=self._start_scan)
        self.scan_btn.grid(row=0, column=1)
        row += 1

        # Filter checkboxes
        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.grid(row=row, column=0, sticky="w", padx=PAD_OUTER, pady=(0, PAD_INNER))

        self.filter_vars = {}
        for itype in IssueType:
            var = ctk.BooleanVar(value=True)
            self.filter_vars[itype] = var
            ctk.CTkCheckBox(
                filters, text=itype.value, variable=var, font=FONT_SMALL,
                command=self._apply_filter,
            ).pack(side="left", padx=(0, 12))
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
            bottom, text="Load More...", width=120, command=self._load_more
        )
        self.load_more_btn.pack(side="left")
        self.load_more_btn.configure(state="disabled")

        self.done_btn = ctk.CTkButton(
            bottom, text="Done", width=120,
            command=lambda: self.app.tabview.set("Process"),
        )
        self.done_btn.pack(side="right")

    def show_results(self, issues: list[quality_detector.QualityIssue]):
        """Accept pre-computed results from the pipeline."""
        self._issues = issues
        self._page = 0
        self._clear_results()
        self.progress_bar.set(1.0)

        by_type = {}
        for issue in issues:
            by_type.setdefault(issue.issue.value, 0)
            by_type[issue.issue.value] += 1
        breakdown = ", ".join(f"{v} {k}" for k, v in by_type.items())

        self.status_label.configure(
            text=f"Found {len(issues)} quality issues: {breakdown}"
        )
        self.app.set_status(f"Found {len(issues)} quality issues")
        self._load_more()

    def _start_scan(self):
        folder = self.folder_picker.get()
        if not folder:
            self.status_label.configure(text="Please select a folder to scan.")
            return

        self._cancel_event.clear()
        self.scan_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self._clear_results()
        self.app.set_status("Scanning image quality...")

        self._worker = threading.Thread(target=self._scan, args=(folder,), daemon=True)
        self._worker.start()

    def _scan(self, folder: str):
        try:
            issues = quality_detector.find_quality_issues(
                folder,
                on_progress=self._on_progress,
                cancel_flag=lambda: self._cancel_event.is_set(),
            )
            self.after(0, self._on_scan_complete, issues)
        except Exception as e:
            self.after(0, self._on_scan_error, str(e))

    def _on_progress(self, current: int, total: int, msg: str):
        self.after(0, self._update_progress, current, total, msg)

    def _update_progress(self, current: int, total: int, msg: str):
        if total > 0:
            self.progress_bar.set(current / total)
        self.status_label.configure(text=msg)

    def _on_scan_complete(self, issues: list[quality_detector.QualityIssue]):
        self.scan_btn.configure(state="normal")
        self.show_results(issues)

    def _on_scan_error(self, error_msg: str):
        self.scan_btn.configure(state="normal")
        self.status_label.configure(text=f"Error: {error_msg}")

    def _clear_results(self):
        for card in self._cards:
            card.destroy()
        self._cards.clear()

    def _get_filtered_issues(self) -> list[quality_detector.QualityIssue]:
        return [i for i in self._issues if self.filter_vars.get(i.issue, ctk.BooleanVar(value=True)).get()]

    def _apply_filter(self):
        self._clear_results()
        self._page = 0
        self._load_more()

    def _load_more(self):
        filtered = self._get_filtered_issues()
        start = self._page * GROUPS_PER_PAGE
        end = min(start + GROUPS_PER_PAGE, len(filtered))

        for i in range(start, end):
            card = QualityIssueCard(self.results_frame, filtered[i])
            card.pack(fill="x", padx=2, pady=(0, PAD_INNER))
            self._cards.append(card)

        self._page += 1
        has_more = end < len(filtered)
        self.load_more_btn.configure(state="normal" if has_more else "disabled")

    def _trash_marked(self):
        files_to_delete = [c.file_path for c in self._cards if c.marked_for_deletion]

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
        self.app.set_status(f"Moved {deleted} junk photos to trash")
