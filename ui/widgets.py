"""Reusable UI widgets: FolderPicker, ThumbnailImage, GroupCard."""

import os
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

from ui.theme import (
    FONT_BODY,
    FONT_SMALL,
    PAD_INNER,
    THUMBNAIL_SIZE_SMALL,
)

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


class FolderPicker(ctk.CTkFrame):
    """A row with a label, readonly entry, and Browse button."""

    def __init__(self, parent, label_text="Folder:", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(1, weight=1)

        self.label = ctk.CTkLabel(self, text=label_text, font=FONT_BODY, width=120, anchor="w")
        self.label.grid(row=0, column=0, padx=(0, PAD_INNER))

        self.entry_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var, font=FONT_BODY)
        self.entry.grid(row=0, column=1, sticky="ew", padx=(0, PAD_INNER))

        self.browse_btn = ctk.CTkButton(self, text="Browse...", width=90, command=self._browse)
        self.browse_btn.grid(row=0, column=2)

    def _browse(self):
        try:
            folder = filedialog.askdirectory(
                title="Select Folder",
                parent=self.winfo_toplevel(),
            )
        except Exception:
            folder = filedialog.askdirectory()
        if folder:
            self._set_entry(folder)

    def _set_entry(self, value: str):
        self.entry.delete(0, "end")
        self.entry.insert(0, value)

    def get(self) -> str:
        return self.entry.get()

    def set(self, path: str):
        self._set_entry(path)


def _make_placeholder(size: tuple[int, int], text: str = "?") -> Image.Image:
    """Create a gray placeholder image with centered text."""
    img = Image.new("RGB", size, color=(80, 80, 80))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("segoeui.ttf", size[0] // 3)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size[0] - tw) // 2, (size[1] - th) // 2), text, fill=(200, 200, 200), font=font)
    return img


def load_thumbnail(path: Path, size: tuple[int, int] = THUMBNAIL_SIZE_SMALL) -> Image.Image:
    """Load and resize an image, returning a placeholder on failure."""
    try:
        img = Image.open(path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        return img.convert("RGB")
    except Exception:
        return _make_placeholder(size)


class ThumbnailCard(ctk.CTkFrame):
    """
    A single file thumbnail with:
    - Image preview
    - Filename label
    - Subfolder path label
    - Keep/Delete toggle
    - Optional distance/info label
    """

    def __init__(
        self,
        parent,
        file_path: Path,
        thumb_size: tuple[int, int] = THUMBNAIL_SIZE_SMALL,
        info_text: str = "",
        default_delete: bool = False,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.file_path = file_path
        self._marked_for_deletion = default_delete

        # Thumbnail image
        pil_img = load_thumbnail(file_path, thumb_size)
        self._ctk_image = ctk.CTkImage(light_image=pil_img, size=thumb_size)
        self.image_label = ctk.CTkLabel(self, image=self._ctk_image, text="")
        self.image_label.pack(padx=PAD_INNER, pady=(PAD_INNER, 2))

        # Filename
        name = file_path.name
        if len(name) > 20:
            name = name[:17] + "..."
        self.name_label = ctk.CTkLabel(self, text=name, font=FONT_SMALL)
        self.name_label.pack()

        # Subfolder
        folder = file_path.parent.name
        self.folder_label = ctk.CTkLabel(self, text=folder, font=FONT_SMALL, text_color="gray")
        self.folder_label.pack()

        # Info text (e.g., distance)
        if info_text:
            self.info_label = ctk.CTkLabel(self, text=info_text, font=FONT_SMALL, text_color="gray")
            self.info_label.pack()

        # Keep/Delete toggle
        if default_delete:
            btn_text, btn_fg, btn_hover = "Delete", "red", "darkred"
        else:
            btn_text, btn_fg, btn_hover = "Keep", "green", "darkgreen"

        self.toggle_btn = ctk.CTkButton(
            self,
            text=btn_text,
            width=70,
            height=26,
            fg_color=btn_fg,
            hover_color=btn_hover,
            command=self._toggle,
        )
        self.toggle_btn.pack(pady=(4, PAD_INNER))

    def _toggle(self):
        self._marked_for_deletion = not self._marked_for_deletion
        if self._marked_for_deletion:
            self.toggle_btn.configure(text="Delete", fg_color="red", hover_color="darkred")
        else:
            self.toggle_btn.configure(text="Keep", fg_color="green", hover_color="darkgreen")

    @property
    def marked_for_deletion(self) -> bool:
        return self._marked_for_deletion


class GroupCard(ctk.CTkFrame):
    """
    A card showing one duplicate/similar group:
    - Header with group info
    - Horizontal scrollable row of ThumbnailCards
    """

    def __init__(
        self,
        parent,
        header_text: str,
        file_paths: list[Path],
        thumb_size: tuple[int, int] = THUMBNAIL_SIZE_SMALL,
        info_texts: list[str] | None = None,
        auto_mark_duplicates: bool = True,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        if info_texts is None:
            info_texts = [""] * len(file_paths)

        has_info = any(info_texts)
        extra = 30 if has_info else 0

        # Header
        self.header = ctk.CTkLabel(self, text=header_text, font=FONT_BODY, anchor="w")
        self.header.grid(row=0, column=0, sticky="w", padx=PAD_INNER, pady=(PAD_INNER, 2))

        # Thumbnails row (horizontal scroll)
        self.thumbs_frame = ctk.CTkScrollableFrame(
            self, orientation="horizontal", height=thumb_size[1] + 110 + extra
        )
        self.thumbs_frame.grid(row=1, column=0, sticky="ew", padx=PAD_INNER, pady=(0, PAD_INNER))

        self.thumbnail_cards: list[ThumbnailCard] = []
        for i, (fpath, info) in enumerate(zip(file_paths, info_texts)):
            # First item defaults to Keep, rest default to Delete
            mark_delete = auto_mark_duplicates and i > 0
            card = ThumbnailCard(
                self.thumbs_frame, fpath, thumb_size=thumb_size,
                info_text=info, default_delete=mark_delete,
            )
            card.pack(side="left", padx=4, pady=2)
            self.thumbnail_cards.append(card)

    def get_files_to_delete(self) -> list[Path]:
        return [c.file_path for c in self.thumbnail_cards if c.marked_for_deletion]

    def get_files_to_keep(self) -> list[Path]:
        return [c.file_path for c in self.thumbnail_cards if not c.marked_for_deletion]
