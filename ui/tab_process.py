"""Process tab — runs full pipeline: ZIP extract, metadata merge, dedup, similarity."""

import os
import threading

import customtkinter as ctk

import gtp_core
from ui.theme import FONT_BODY, FONT_HEADING, FONT_MONO, FONT_SMALL, PAD_INNER, PAD_OUTER
from ui.widgets import FolderPicker


class ProcessTab(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None

        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)

        row = 0

        # Input folder
        self.input_picker = FolderPicker(self, label_text="Input Folder:")
        self.input_picker.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(PAD_OUTER, PAD_INNER))
        row += 1

        # Output folder
        self.output_picker = FolderPicker(self, label_text="Output Folder:")
        self.output_picker.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(0, PAD_INNER))
        row += 1

        # Suffixes
        suffix_frame = ctk.CTkFrame(self, fg_color="transparent")
        suffix_frame.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(0, PAD_INNER))
        suffix_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(suffix_frame, text="Suffixes:", font=FONT_BODY, width=120, anchor="w").grid(
            row=0, column=0, padx=(0, PAD_INNER)
        )
        self.suffix_var = ctk.StringVar(value=", -edited")
        ctk.CTkEntry(suffix_frame, textvariable=self.suffix_var, font=FONT_BODY).grid(
            row=0, column=1, sticky="ew"
        )
        ctk.CTkLabel(suffix_frame, text="(comma-separated)", font=FONT_SMALL, text_color="gray").grid(
            row=0, column=2, padx=(PAD_INNER, 0)
        )
        row += 1

        # Auto-scan checkboxes
        checks_frame = ctk.CTkFrame(self, fg_color="transparent")
        checks_frame.grid(row=row, column=0, sticky="w", padx=PAD_OUTER, pady=(0, PAD_INNER))

        self.auto_dupes_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            checks_frame, text="Auto-scan for duplicates after processing",
            variable=self.auto_dupes_var, font=FONT_BODY,
        ).pack(side="left", padx=(0, 20))

        self.auto_similar_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            checks_frame, text="Auto-scan for similar photos",
            variable=self.auto_similar_var, font=FONT_BODY,
        ).pack(side="left", padx=(0, 20))

        self.auto_quality_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            checks_frame, text="Auto-scan quality",
            variable=self.auto_quality_var, font=FONT_BODY,
        ).pack(side="left")
        row += 1

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="w", padx=PAD_OUTER, pady=(0, PAD_INNER))

        self.start_btn = ctk.CTkButton(
            btn_frame, text="Start Processing", width=160, height=36,
            font=FONT_BODY, command=self._start
        )
        self.start_btn.pack(side="left", padx=(0, PAD_INNER))

        self.cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel", width=90, height=36,
            font=FONT_BODY, fg_color="gray", state="disabled", command=self._cancel
        )
        self.cancel_btn.pack(side="left")
        row += 1

        # Progress
        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(0, PAD_INNER))
        progress_frame.grid_columnconfigure(0, weight=1)

        self.phase_label = ctk.CTkLabel(progress_frame, text="Phase: Idle", font=FONT_SMALL, anchor="w")
        self.phase_label.grid(row=0, column=0, sticky="w", padx=PAD_INNER, pady=(PAD_INNER, 2))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=PAD_INNER, pady=(0, 2))
        self.progress_bar.set(0)

        self.counter_label = ctk.CTkLabel(progress_frame, text="", font=FONT_SMALL, anchor="e")
        self.counter_label.grid(row=0, column=1, sticky="e", padx=PAD_INNER, pady=(PAD_INNER, 2))
        row += 1

        # Log output
        self.log_box = ctk.CTkTextbox(self, font=FONT_MONO, height=150, state="disabled")
        self.log_box.grid(row=row, column=0, sticky="nsew", padx=PAD_OUTER, pady=(0, PAD_INNER))
        self.grid_rowconfigure(row, weight=1)
        row += 1

        # Summary frame (hidden until processing completes)
        self.summary_frame = ctk.CTkFrame(self)
        self.summary_frame.grid(row=row, column=0, sticky="ew", padx=PAD_OUTER, pady=(0, PAD_OUTER))
        self.summary_frame.grid_columnconfigure(0, weight=1)
        self.summary_frame.grid_remove()

        self.summary_label = ctk.CTkLabel(self.summary_frame, text="", font=FONT_BODY, anchor="w", justify="left")
        self.summary_label.grid(row=0, column=0, sticky="w", padx=PAD_INNER, pady=PAD_INNER)

        summary_btns = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        summary_btns.grid(row=1, column=0, sticky="w", padx=PAD_INNER, pady=(0, PAD_INNER))

        self.open_folder_btn = ctk.CTkButton(
            summary_btns, text="Open Output Folder", width=160, command=self._open_output
        )
        self.open_folder_btn.pack(side="left", padx=(0, PAD_INNER))

        self.scan_dupes_btn = ctk.CTkButton(
            summary_btns, text="View Duplicates ->", width=160, command=self._go_to_duplicates
        )
        self.scan_dupes_btn.pack(side="left", padx=(0, PAD_INNER))

        self.scan_similar_btn = ctk.CTkButton(
            summary_btns, text="View Similar Photos ->", width=170, command=self._go_to_similar
        )
        self.scan_similar_btn.pack(side="left", padx=(0, PAD_INNER))

        self.scan_quality_btn = ctk.CTkButton(
            summary_btns, text="View Quality Issues ->", width=170, command=self._go_to_quality
        )
        self.scan_quality_btn.pack(side="left")

    def _parse_suffixes(self) -> list[str]:
        raw = self.suffix_var.get()
        return [s.strip() for s in raw.split(",") if s.strip() or s == ""]

    def _log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _start(self):
        input_path = self.input_picker.get().strip()
        if not input_path:
            self._log("ERROR: Please select an input folder.")
            return
        if not os.path.isdir(input_path):
            self._log(f"ERROR: Input folder does not exist: {input_path}")
            return

        output_path = self.output_picker.get().strip()
        if output_path and not os.path.isdir(output_path):
            try:
                os.makedirs(output_path, exist_ok=True)
                self._log(f"Created output folder: {output_path}")
            except OSError as e:
                self._log(f"ERROR: Cannot create output folder: {e}")
                return

        self._cancel_event.clear()
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.summary_frame.grid_remove()
        self.progress_bar.set(0)
        self.phase_label.configure(text="Phase: Starting...")
        self.counter_label.configure(text="")

        # Clear log
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        self.app.set_status("Running pipeline...")

        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def _cancel(self):
        self._cancel_event.set()
        self.cancel_btn.configure(state="disabled")
        self._log("Cancellation requested...")

    def _run(self):
        try:
            input_path = self.input_picker.get().strip()
            output_path = self.output_picker.get().strip() or None
            result = gtp_core.run_full_pipeline(
                path=input_path,
                suffixes=self._parse_suffixes(),
                destination=output_path,
                scan_duplicates=self.auto_dupes_var.get(),
                scan_similar=self.auto_similar_var.get(),
                scan_quality=self.auto_quality_var.get(),
                on_progress=self._on_progress,
                cancel_flag=lambda: self._cancel_event.is_set(),
            )
            self.after(0, self._on_complete, result)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.after(0, self._on_error, f"{e}\n\n{tb}")

    def _on_progress(self, info: gtp_core.ProgressInfo):
        self.after(0, self._update_progress, info)

    def _update_progress(self, info: gtp_core.ProgressInfo):
        total = max(info.total, 1)
        self.progress_bar.set(info.current / total)
        phase_labels = {
            "extracting_zips": "Extracting ZIP files",
            "scanning": "Scanning files",
            "processing": "Processing metadata",
            "copying_unprocessed": "Copying unprocessed files",
            "scanning_duplicates": "Scanning for duplicates",
            "scanning_similar": "Scanning for similar photos",
            "scanning_quality": "Scanning image quality",
            "pipeline_done": "Pipeline complete",
            "done": "Processing complete",
        }
        display_phase = phase_labels.get(info.phase, info.phase)
        self.phase_label.configure(text=f"Phase: {display_phase}")
        self.counter_label.configure(text=f"{info.current:,} / {info.total:,}" if info.total > 0 else "")
        if info.message:
            self._log(info.message)
        self.app.set_status(info.message or display_phase)

    def _on_complete(self, result: gtp_core.PipelineResult):
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(1.0)

        pr = result.processing
        self.app.last_output_dir = pr.output_dir

        # Build summary
        lines = [
            f"Processed: {len(pr.processed)} files",
            f"Unprocessed: {len(pr.unprocessed)} files, {len(pr.unprocessed_jsons)} jsons",
            f"Time: {pr.elapsed_seconds} seconds",
            f"Output: {pr.output_dir}",
        ]
        if result.duplicates is not None:
            n_groups = len(result.duplicates)
            n_files = sum(len(g.paths) for g in result.duplicates)
            lines.append(f"Duplicates: {n_groups} groups ({n_files} files)")
        if result.similar is not None:
            n_groups = len(result.similar)
            n_imgs = sum(len(g.members) for g in result.similar)
            lines.append(f"Similar: {n_groups} groups ({n_imgs} images)")
        if result.quality_issues is not None:
            n_issues = len(result.quality_issues)
            lines.append(f"Quality issues: {n_issues} flagged photos")

        summary = "\n".join(lines)
        self.summary_label.configure(text=summary)
        self.summary_frame.grid()
        self._log(f"\n=== PIPELINE COMPLETE ===\n{summary}")

        # Show activity log
        if result.activity_log:
            self._log(f"\n=== ACTIVITY LOG ===\n{result.activity_log}")

        self.app.set_status(f"Done! {len(pr.processed)} files processed in {pr.elapsed_seconds}s")

        # Push results to other tabs
        self.app.show_pipeline_results(result)

    def _on_error(self, error_msg: str):
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self._log(f"\nERROR: {error_msg}")
        self.app.set_status(f"Error: {error_msg}")

    def _open_output(self):
        if self.app.last_output_dir:
            os.startfile(self.app.last_output_dir)

    def _go_to_duplicates(self):
        self.app.tabview.set("Duplicates")

    def _go_to_similar(self):
        self.app.tabview.set("Similar Photos")

    def _go_to_quality(self):
        self.app.tabview.set("Quality Review")
