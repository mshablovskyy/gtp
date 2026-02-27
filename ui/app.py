"""Main application window with tabbed interface."""

import customtkinter as ctk

import gtp_core
from ui.tab_process import ProcessTab
from ui.tab_duplicates import DuplicatesTab
from ui.tab_similar import SimilarTab
from ui.tab_quality import QualityTab
from ui.theme import FONT_SMALL, PAD_OUTER


class GTPApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Google Takeout Processor")
        self.geometry("1100x750")
        self.minsize(850, 600)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # Layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=PAD_OUTER, pady=(PAD_OUTER, 2), sticky="nsew")

        self.tabview.add("Process")
        self.tabview.add("Duplicates")
        self.tabview.add("Similar Photos")
        self.tabview.add("Quality Review")

        # Shared state
        self.last_output_dir: str | None = None

        # Create tab frames
        self.process_tab = ProcessTab(self.tabview.tab("Process"), app=self)
        self.duplicates_tab = DuplicatesTab(self.tabview.tab("Duplicates"), app=self)
        self.similar_tab = SimilarTab(self.tabview.tab("Similar Photos"), app=self)
        self.quality_tab = QualityTab(self.tabview.tab("Quality Review"), app=self)

        # Status bar
        self.status_var = ctk.StringVar(value="Ready")
        self.status_bar = ctk.CTkLabel(
            self, textvariable=self.status_var, font=FONT_SMALL, anchor="w"
        )
        self.status_bar.grid(row=1, column=0, sticky="ew", padx=PAD_OUTER, pady=(0, 6))

    def set_status(self, text: str):
        self.status_var.set(text)

    def switch_to_duplicates(self):
        """Switch to Duplicates tab and pre-fill the scan folder."""
        if self.last_output_dir:
            self.duplicates_tab.folder_picker.set(self.last_output_dir)
        self.tabview.set("Duplicates")

    def switch_to_similar(self):
        """Switch to Similar Photos tab and pre-fill the scan folder."""
        if self.last_output_dir:
            self.similar_tab.folder_picker.set(self.last_output_dir)
        self.tabview.set("Similar Photos")

    def show_pipeline_results(self, result: gtp_core.PipelineResult):
        """Load pre-computed results into tabs after full pipeline run."""
        self.last_output_dir = result.processing.output_dir

        has_dupes = result.duplicates is not None and len(result.duplicates) > 0
        has_similar = result.similar is not None and len(result.similar) > 0
        has_quality = result.quality_issues is not None and len(result.quality_issues) > 0

        # Pre-fill folder pickers
        if self.last_output_dir:
            self.duplicates_tab.folder_picker.set(self.last_output_dir)
            self.similar_tab.folder_picker.set(self.last_output_dir)
            self.quality_tab.folder_picker.set(self.last_output_dir)

        # Load results into tabs
        if has_dupes:
            self.duplicates_tab.show_results(result.duplicates)
        if has_similar:
            self.similar_tab.show_results(result.similar)
        if has_quality:
            self.quality_tab.show_results(result.quality_issues)

        # Auto-switch to the first tab with results
        if has_dupes:
            self.tabview.set("Duplicates")
        elif has_similar:
            self.tabview.set("Similar Photos")
        elif has_quality:
            self.tabview.set("Quality Review")
