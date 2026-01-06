"""
Main application window for WoodWay Image & Video Converter.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Literal
import threading
import json
import re
from PIL import Image, ImageTk

# Drag and drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from src.core import ImageConverter, SEOFileRenamer, MetadataHandler, WordPressExporter, ExportSettings
from src.core.renamer import ProductAttributes, SEOMetadata
from src.ai import GeminiClient
from src.ai.gemini_client import GeminiConfig, create_client_from_env

# Video converter support
try:
    from src.core import VideoConverter, VideoInfo, VIDEO_RESOLUTION_PRESETS, FFmpegNotFoundError
    FFMPEG_AVAILABLE = VideoConverter.is_ffmpeg_available()
except ImportError:
    FFMPEG_AVAILABLE = False
    VIDEO_RESOLUTION_PRESETS = {}

# File type constants
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv', '.ogv'}
MediaType = Literal["image", "video"]


# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MediaItem:
    """Represents a single image or video in the processing queue."""
    def __init__(self, path: Path, index: int = 0):
        self.path = path
        self.index = index
        self.thumbnail: Optional[ctk.CTkImage] = None
        self.metadata: Optional[SEOMetadata] = None
        self.video_metadata: Optional[Dict[str, Any]] = None  # Video-specific metadata
        self.processed = False
        self.output_path: Optional[Path] = None
        self.card_frame: Optional[ctk.CTkFrame] = None  # Reference to UI card
        
        # Determine media type
        suffix = path.suffix.lower()
        if suffix in VIDEO_EXTENSIONS:
            self.media_type: MediaType = "video"
        else:
            self.media_type: MediaType = "image"
        
        # Video-specific info (populated on demand)
        self.video_info: Optional[VideoInfo] = None
        self.thumbnail_path: Optional[Path] = None  # Extracted video thumbnail


# Backward compatibility alias
ImageItem = MediaItem


class WoodWayConverterApp(ctk.CTk, TkinterDnD.DnDWrapper if DND_AVAILABLE else object):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize drag-and-drop if available
        if DND_AVAILABLE:
            self.TkdndVersion = TkinterDnD._require(self)
        
        self.title("WoodWay — Конвертер зображень, відео та SEO інструмент")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # Set window icon
        self._set_window_icon()
        
        # Initialize components
        self.converter = ImageConverter(output_format="webp", quality=85)
        self.renamer = SEOFileRenamer()
        self.gemini_client: Optional[GeminiClient] = create_client_from_env()
        
        # Video converter (may be None if FFmpeg not available)
        self.video_converter: Optional[VideoConverter] = None
        if FFMPEG_AVAILABLE:
            try:
                self.video_converter = VideoConverter(output_format="mp4", crf=23)
            except FFmpegNotFoundError:
                pass
        
        # State
        self.images: List[MediaItem] = []  # Now holds both images and videos
        self.selected_image: Optional[MediaItem] = None
        self.previous_selected: Optional[MediaItem] = None  # Track previous selection
        self.current_attributes = ProductAttributes()
        self.use_ai = ctk.BooleanVar(value=False)
        self.use_subfolder = ctk.BooleanVar(value=True)
        self.output_format = ctk.StringVar(value="webp")
        self.video_output_format = ctk.StringVar(value="mp4")
        self.quality = ctk.IntVar(value=85)
        self.video_quality = ctk.IntVar(value=23)  # CRF for video (lower = better)
        
        # Thumbnail cache to avoid regenerating on every refresh
        self._thumbnail_cache: Dict[Path, ctk.CTkImage] = {}
        
        # Temp directory for video thumbnails
        self._temp_thumbnails: List[Path] = []
        
        # Processing state management
        self.cancel_event = threading.Event()
        self.is_processing = False
        self.active_threads: List[threading.Thread] = []
        self.active_ffmpeg_processes: List = []  # For video conversion cancellation
        
        # Drag-and-drop reordering state
        self._drag_item: Optional[MediaItem] = None
        self._drag_start_y: int = 0
        self._drag_target_index: Optional[int] = None
        self._drag_indicator: Optional[ctk.CTkFrame] = None
        
        # Build UI
        self._create_layout()
        self._create_toolbar()
        self._create_sidebar()
        self._create_preview_area()
        self._create_metadata_panel()
        self._create_status_bar()
        
        # Update dynamic dropdowns
        self._update_type_dropdown()
    
    def _set_window_icon(self):
        """Set the application window icon."""
        import sys
        import platform
        
        # Determine base path (different for dev vs packaged)
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe
            base_path = Path(sys._MEIPASS)
        else:
            # Running as script
            base_path = Path(__file__).parent.parent.parent
        
        # Paths to try
        icon_png = base_path / "assets" / "icon.png"
        icon_ico = base_path / "assets" / "icon.ico"
        
        # Prefer high-quality PNG for the window titlebar (it scales better)
        if icon_png.exists():
            try:
                img = Image.open(icon_png)
                photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, photo)
                self._app_icon = photo  # Prevent garbage collection
                print(f"[Icon] Loaded high-quality PNG: {icon_png}")
            except Exception as e:
                print(f"[Icon] Failed to load PNG: {e}")
        
        # Also set the taskbar icon using the ICO on Windows
        if platform.system() == 'Windows' and icon_ico.exists():
            try:
                self.iconbitmap(default=str(icon_ico))
                print(f"[Icon] Set taskbar ICO: {icon_ico}")
            except Exception as e:
                print(f"[Icon] Failed to set ICO: {e}")
    
    def _create_layout(self):
        """Create main layout containers."""
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Toolbar at top
        self.toolbar_frame = ctk.CTkFrame(self, height=50)
        self.toolbar_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        # Left sidebar for settings
        self.sidebar_frame = ctk.CTkFrame(self, width=300)
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.sidebar_frame.grid_propagate(False)
        
        # Center area for image preview
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        # Right panel for metadata
        self.metadata_frame = ctk.CTkFrame(self, width=350)
        self.metadata_frame.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)
        self.metadata_frame.grid_propagate(False)
        
        # Status bar at bottom
        self.status_frame = ctk.CTkFrame(self, height=30)
        self.status_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
    
    def _create_toolbar(self):
        """Create toolbar with main actions."""
        # Store original button colors for restoration
        self._original_button_colors = {}
        
        # Add images button
        self.btn_add = ctk.CTkButton(
            self.toolbar_frame,
            text="📁 Додати файли",
            command=self._add_media,
            width=130
        )
        self.btn_add.pack(side="left", padx=5, pady=5)
        self._original_button_colors['btn_add'] = self.btn_add.cget("fg_color")
        
        # Clear button
        self.btn_clear = ctk.CTkButton(
            self.toolbar_frame,
            text="🗑️ Очистити",
            command=self._clear_images,
            width=100,
            fg_color="gray"
        )
        self.btn_clear.pack(side="left", padx=5, pady=5)
        self._original_button_colors['btn_clear'] = "gray"
        
        # Separator
        ctk.CTkLabel(self.toolbar_frame, text="|").pack(side="left", padx=10)
        
        # Generate metadata button
        self.btn_generate = ctk.CTkButton(
            self.toolbar_frame,
            text="⚡ Згенерувати назви",
            command=self._generate_metadata,
            width=160
        )
        self.btn_generate.pack(side="left", padx=5, pady=5)
        self._original_button_colors['btn_generate'] = self.btn_generate.cget("fg_color")
        
        # Regenerate all button
        self.btn_regenerate = ctk.CTkButton(
            self.toolbar_frame,
            text="🔄 Оновити все",
            command=self._regenerate_all,
            width=120,
            fg_color=("gray70", "gray35"),
            hover_color=("gray60", "gray45")
        )
        self.btn_regenerate.pack(side="left", padx=5, pady=5)
        self._original_button_colors['btn_regenerate'] = ("gray70", "gray35")
        
        # AI toggle
        self.ai_checkbox = ctk.CTkCheckBox(
            self.toolbar_frame,
            text="Використовувати AI (Gemini)",
            variable=self.use_ai,
            onvalue=True,
            offvalue=False,
            command=self._on_ai_toggle
        )
        self.ai_checkbox.pack(side="left", padx=15, pady=5)
        
        # Model picker (always visible when AI is enabled)
        self.model_label = ctk.CTkLabel(self.toolbar_frame, text="Модель:")
        self.model_var = ctk.StringVar(value="gemini-2.5-flash")
        self.model_dropdown = ctk.CTkComboBox(
            self.toolbar_frame,
            variable=self.model_var,
            values=["gemini-2.5-flash"],
            width=200,
            state="readonly",
            command=self._on_model_change
        )
        
        # Store separator reference for positioning
        self.toolbar_separator = ctk.CTkLabel(self.toolbar_frame, text="|")
        
        # Show/hide model picker based on AI state
        if self.use_ai.get():
            self.model_label.pack(side="left", padx=(10, 5), pady=5)
            self.model_dropdown.pack(side="left", padx=5, pady=5)
            # Load available models if Gemini is available
            if self.gemini_client:
                threading.Thread(target=self._load_available_models, daemon=True).start()
        else:
            self.model_label.pack_forget()
            self.model_dropdown.pack_forget()
        
        # Separator
        self.toolbar_separator.pack(side="left", padx=10)
        
        # Process button
        self.btn_process = ctk.CTkButton(
            self.toolbar_frame,
            text="✅ Конвертувати і зберегти",
            command=self._process_media,
            width=180,
            fg_color="green"
        )
        self.btn_process.pack(side="left", padx=5, pady=5)
        self._original_button_colors['btn_process'] = "green"
        
        # Output folder button
        self.btn_output = ctk.CTkButton(
            self.toolbar_frame,
            text="📂 Папка виводу",
            command=self._select_output_folder,
            width=130
        )
        self.btn_output.pack(side="right", padx=5, pady=5)
        self._original_button_colors['btn_output'] = self.btn_output.cget("fg_color")
        
        self.output_folder: Optional[Path] = None
    
    def _create_sidebar(self):
        """Create settings sidebar with dynamic dropdowns."""
        # Create scrollable frame inside sidebar to handle overflow
        self.sidebar_scroll = ctk.CTkScrollableFrame(
            self.sidebar_frame,
            fg_color="transparent"
        )
        self.sidebar_scroll.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Title
        ctk.CTkLabel(
            self.sidebar_scroll,
            text="Налаштування продукту",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Category dropdown
        ctk.CTkLabel(self.sidebar_scroll, text="Категорія:").pack(anchor="w", padx=10)
        categories = self.renamer.get_category_options()
        cat_values = [""] + [c["name_ua"] for c in categories]
        self.category_var = ctk.StringVar(value="")
        self.category_dropdown = ctk.CTkComboBox(
            self.sidebar_scroll,
            values=cat_values,
            variable=self.category_var,
            command=self._on_category_change,
            width=260
        )
        self.category_dropdown.pack(padx=10, pady=5)
        
        # Type dropdown (dynamic)
        ctk.CTkLabel(self.sidebar_scroll, text="Тип:").pack(anchor="w", padx=10)
        self.type_var = ctk.StringVar(value="")
        self.type_dropdown = ctk.CTkComboBox(
            self.sidebar_scroll,
            values=[""],
            variable=self.type_var,
            command=self._on_type_change,
            width=260
        )
        self.type_dropdown.pack(padx=10, pady=5)
        
        # Species dropdown
        ctk.CTkLabel(self.sidebar_scroll, text="Порода дерева:").pack(anchor="w", padx=10)
        species_options = self.renamer.get_list_options("species")
        species_values = [""] + [s["ua"] for s in species_options]
        self.species_var = ctk.StringVar(value="")
        self.species_dropdown = ctk.CTkComboBox(
            self.sidebar_scroll,
            values=species_values,
            variable=self.species_var,
            command=self._on_attribute_change,
            width=260
        )
        self.species_dropdown.pack(padx=10, pady=5)
        
        # Thickness dropdown (will update based on category)
        ctk.CTkLabel(self.sidebar_scroll, text="Товщина:").pack(anchor="w", padx=10)
        self.thickness_var = ctk.StringVar(value="")
        self.thickness_dropdown = ctk.CTkComboBox(
            self.sidebar_scroll,
            values=[""],
            variable=self.thickness_var,
            command=self._on_attribute_change,
            width=260
        )
        self.thickness_dropdown.pack(padx=10, pady=5)
        
        # Grade dropdown
        ctk.CTkLabel(self.sidebar_scroll, text="Ґатунок:").pack(anchor="w", padx=10)
        self.grade_var = ctk.StringVar(value="")
        self.grade_dropdown = ctk.CTkComboBox(
            self.sidebar_scroll,
            values=[""],
            variable=self.grade_var,
            command=self._on_attribute_change,
            width=260
        )
        self.grade_dropdown.pack(padx=10, pady=5)
        
        # Separator
        ctk.CTkFrame(self.sidebar_scroll, height=2, fg_color="gray").pack(fill="x", padx=10, pady=15)
        
        # Output settings
        ctk.CTkLabel(
            self.sidebar_scroll,
            text="Налаштування виводу",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)
        
        # Format
        ctk.CTkLabel(self.sidebar_scroll, text="Формат:").pack(anchor="w", padx=10)
        self.format_dropdown = ctk.CTkComboBox(
            self.sidebar_scroll,
            values=["webp", "jpeg", "png"],
            variable=self.output_format,
            width=260,
            state="readonly"
        )
        self.format_dropdown.pack(padx=10, pady=5)
        
        # Resolution selector
        ctk.CTkLabel(self.sidebar_scroll, text="Роздільність:").pack(anchor="w", padx=10)
        from src.core.converter import RESOLUTION_PRESETS
        self._resolution_presets = RESOLUTION_PRESETS
        resolution_names = [preset["name_ua"] for preset in RESOLUTION_PRESETS.values()]
        self.resolution_var = ctk.StringVar(value=resolution_names[0])  # Default to SEO Optimal
        self.resolution_dropdown = ctk.CTkComboBox(
            self.sidebar_scroll,
            values=resolution_names,
            variable=self.resolution_var,
            command=self._on_resolution_change,
            width=260,
            state="readonly"
        )
        self.resolution_dropdown.pack(padx=10, pady=5)
        
        # Resolution description
        self.resolution_desc = ctk.CTkLabel(
            self.sidebar_scroll,
            text=RESOLUTION_PRESETS["seo_optimal"]["description_ua"],
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60"),
            wraplength=260,
            justify="left"
        )
        self.resolution_desc.pack(padx=10, pady=(0, 5), anchor="w")
        
        # Quality slider
        ctk.CTkLabel(self.sidebar_scroll, text="Якість:").pack(anchor="w", padx=10)
        self.quality_slider = ctk.CTkSlider(
            self.sidebar_scroll,
            from_=1,
            to=100,
            variable=self.quality,
            width=260
        )
        self.quality_slider.pack(padx=10, pady=5)
        self.quality_label = ctk.CTkLabel(self.sidebar_scroll, text="85%")
        self.quality_label.pack()
        self.quality.trace_add("write", lambda *_: self.quality_label.configure(text=f"{self.quality.get()}%"))
        
        # Subfolder checkbox
        self.subfolder_checkbox = ctk.CTkCheckBox(
            self.sidebar_scroll,
            text='Зберігати в підпапку "seo-images"',
            variable=self.use_subfolder,
            onvalue=True,
            offvalue=False
        )
        self.subfolder_checkbox.pack(padx=10, pady=10, anchor="w")
        
        # Video settings section (only if FFmpeg available)
        self._create_video_settings()
    
    def _create_video_settings(self):
        """Create video-specific settings section in sidebar."""
        if not FFMPEG_AVAILABLE:
            # Show warning if FFmpeg not available
            warning_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color=("orange", "#aa5500"))
            warning_frame.pack(fill="x", padx=10, pady=10)
            ctk.CTkLabel(
                warning_frame,
                text="⚠️ FFmpeg не знайдено",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="white"
            ).pack(padx=10, pady=5)
            ctk.CTkLabel(
                warning_frame,
                text="Відео конвертація недоступна.\nВстановіть FFmpeg для підтримки відео.",
                font=ctk.CTkFont(size=10),
                text_color="white",
                wraplength=240
            ).pack(padx=10, pady=(0, 5))
            return
        
        # Separator
        ctk.CTkFrame(self.sidebar_scroll, height=2, fg_color="gray").pack(fill="x", padx=10, pady=15)
        
        # Video settings header
        ctk.CTkLabel(
            self.sidebar_scroll,
            text="🎬 Налаштування відео",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)
        
        # Video format dropdown
        ctk.CTkLabel(self.sidebar_scroll, text="Формат відео:").pack(anchor="w", padx=10)
        self.video_format_dropdown = ctk.CTkComboBox(
            self.sidebar_scroll,
            values=["mp4", "webm"],
            variable=self.video_output_format,
            width=260,
            state="readonly"
        )
        self.video_format_dropdown.pack(padx=10, pady=5)
        
        # Video resolution preset
        ctk.CTkLabel(self.sidebar_scroll, text="Роздільність відео:").pack(anchor="w", padx=10)
        self._video_resolution_presets = VIDEO_RESOLUTION_PRESETS
        video_resolution_names = [preset["name_ua"] for preset in VIDEO_RESOLUTION_PRESETS.values()]
        self.video_resolution_var = ctk.StringVar(value=video_resolution_names[0] if video_resolution_names else "")
        self.video_resolution_dropdown = ctk.CTkComboBox(
            self.sidebar_scroll,
            values=video_resolution_names,
            variable=self.video_resolution_var,
            command=self._on_video_resolution_change,
            width=260,
            state="readonly"
        )
        self.video_resolution_dropdown.pack(padx=10, pady=5)
        
        # Video resolution description
        default_preset = list(VIDEO_RESOLUTION_PRESETS.values())[0] if VIDEO_RESOLUTION_PRESETS else {}
        self.video_resolution_desc = ctk.CTkLabel(
            self.sidebar_scroll,
            text=default_preset.get("description_ua", ""),
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60"),
            wraplength=260,
            justify="left"
        )
        self.video_resolution_desc.pack(padx=10, pady=(0, 5), anchor="w")
        
        # Video quality slider (CRF)
        ctk.CTkLabel(self.sidebar_scroll, text="Якість (CRF, менше = краще):").pack(anchor="w", padx=10)
        self.video_quality_slider = ctk.CTkSlider(
            self.sidebar_scroll,
            from_=15,
            to=35,
            variable=self.video_quality,
            width=260
        )
        self.video_quality_slider.pack(padx=10, pady=5)
        self.video_quality_label = ctk.CTkLabel(self.sidebar_scroll, text="CRF: 23 (рекомендовано)")
        self.video_quality_label.pack()
        self.video_quality.trace_add("write", self._update_video_quality_label)
        
        # Generate both MP4 and WebM checkbox
        self.generate_dual_format_var = ctk.BooleanVar(value=False)
        self.generate_dual_format_checkbox = ctk.CTkCheckBox(
            self.sidebar_scroll,
            text='Генерувати обидва формати (MP4 + WebM)',
            variable=self.generate_dual_format_var,
            onvalue=True,
            offvalue=False
        )
        self.generate_dual_format_checkbox.pack(padx=10, pady=5, anchor="w")
        
        # Extract thumbnails checkbox
        self.extract_thumbnail_var = ctk.BooleanVar(value=True)
        self.extract_thumbnail_checkbox = ctk.CTkCheckBox(
            self.sidebar_scroll,
            text='Витягнути постер (thumbnail)',
            variable=self.extract_thumbnail_var,
            onvalue=True,
            offvalue=False
        )
        self.extract_thumbnail_checkbox.pack(padx=10, pady=5, anchor="w")
    
    def _update_video_quality_label(self, *args):
        """Update video quality label based on CRF value."""
        crf = self.video_quality.get()
        if crf <= 20:
            quality_desc = "висока якість"
        elif crf <= 25:
            quality_desc = "рекомендовано"
        else:
            quality_desc = "швидке завантаження"
        self.video_quality_label.configure(text=f"CRF: {crf} ({quality_desc})")
    
    def _on_video_resolution_change(self, value: str):
        """Handle video resolution preset change."""
        for key, preset in self._video_resolution_presets.items():
            if preset["name_ua"] == value:
                self.video_resolution_desc.configure(text=preset["description_ua"])
                # Update video converter settings
                if self.video_converter:
                    self.video_converter.max_resolution = preset.get("resolution")
                    self.video_converter.crf = preset.get("crf", 23)
                break
    
    def _get_selected_video_preset(self) -> dict:
        """Get the currently selected video resolution preset."""
        selected_name = self.video_resolution_var.get()
        for key, preset in self._video_resolution_presets.items():
            if preset["name_ua"] == selected_name:
                return preset
        # Default fallback
        return {"resolution": (1280, 720), "crf": 23, "preset": "medium"}
    
    def _create_preview_area(self):
        """Create scrollable media list view."""
        self.preview_label = ctk.CTkLabel(
            self.preview_frame,
            text="Список файлів (перетягніть зображення або відео сюди)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.preview_label.pack(pady=5)
        
        # Drop zone frame with visual feedback
        self.drop_zone = ctk.CTkFrame(
            self.preview_frame,
            fg_color=("gray85", "gray20"),
            border_width=2,
            border_color=("gray70", "gray40")
        )
        self.drop_zone.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollable frame for images inside drop zone - VERTICAL list
        self.preview_scroll = ctk.CTkScrollableFrame(
            self.drop_zone,
            orientation="vertical",
            fg_color="transparent"
        )
        self.preview_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Drop hint label (shown when empty)
        self.drop_hint = ctk.CTkLabel(
            self.drop_zone,
            text="📂 Перетягніть зображення сюди\nабо натисніть 'Додати файли'",
            font=ctk.CTkFont(size=16),
            text_color=("gray50", "gray60")
        )
        self.drop_hint.place(relx=0.5, rely=0.5, anchor="center")
        
        # Register drag-and-drop if available
        if DND_AVAILABLE:
            self._setup_drag_drop()
        
        # Will hold image card frames
        self.image_cards: List[ctk.CTkFrame] = []
    
    def _setup_drag_drop(self):
        """Setup drag and drop handlers."""
        # Register the drop zone
        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind('<<DropEnter>>', self._on_drop_enter)
        self.drop_zone.dnd_bind('<<DropLeave>>', self._on_drop_leave)
        self.drop_zone.dnd_bind('<<Drop>>', self._on_drop)
        
        # Also register the main preview frame
        self.preview_frame.drop_target_register(DND_FILES)
        self.preview_frame.dnd_bind('<<Drop>>', self._on_drop)
        
        # And the scroll area
        self.preview_scroll.drop_target_register(DND_FILES)
        self.preview_scroll.dnd_bind('<<Drop>>', self._on_drop)
    
    def _on_drop_enter(self, event):
        """Visual feedback when dragging over drop zone."""
        self.drop_zone.configure(
            border_color=("green", "#00aa00"),
            border_width=3
        )
        return event.action
    
    def _on_drop_leave(self, event):
        """Reset visual feedback when leaving drop zone."""
        self.drop_zone.configure(
            border_color=("gray70", "gray40"),
            border_width=2
        )
        return event.action
    
    def _on_drop(self, event):
        """Handle dropped files."""
        # Reset border
        self.drop_zone.configure(
            border_color=("gray70", "gray40"),
            border_width=2
        )
        
        # Parse dropped files
        # The data comes as a string with paths, possibly with {} around paths with spaces
        files_str = event.data
        
        # Parse file paths (handles paths with spaces wrapped in {})
        paths = self._parse_dropped_files(files_str)
        
        if paths:
            self._add_dropped_files(paths)
        
        return event.action
    
    def _parse_dropped_files(self, data: str) -> List[Path]:
        """Parse dropped file paths from tkdnd data string."""
        paths = []
        
        # Pattern to match paths (with or without braces)
        # Paths with spaces are wrapped in {}
        pattern = r'\{([^}]+)\}|(\S+)'
        matches = re.findall(pattern, data)
        
        for match in matches:
            path_str = match[0] if match[0] else match[1]
            path = Path(path_str)
            
            # Add image and video files
            suffix = path.suffix.lower()
            if path.exists() and (suffix in IMAGE_EXTENSIONS or suffix in VIDEO_EXTENSIONS):
                # Check if video files are supported
                if suffix in VIDEO_EXTENSIONS and not FFMPEG_AVAILABLE:
                    continue  # Skip video files if FFmpeg not available
                paths.append(path)
        
        return paths
    
    def _add_dropped_files(self, paths: List[Path]):
        """Add dropped files to the media list."""
        start_index = len(self.images)
        added = 0
        added_images = 0
        added_videos = 0
        new_items = []
        
        for path in paths:
            # Check if already added
            if not any(img.path == path for img in self.images):
                item = MediaItem(path, index=start_index + added + 1)
                self.images.append(item)
                new_items.append(item)
                added += 1
                if item.media_type == "video":
                    added_videos += 1
                else:
                    added_images += 1
        
        if added > 0:
            # Preload thumbnails in background thread
            threading.Thread(
                target=self._preload_thumbnails, 
                args=(new_items,), 
                daemon=True
            ).start()
            
            self._refresh_preview()
            
            # Create status message
            parts = []
            if added_images > 0:
                parts.append(f"{added_images} зображень")
            if added_videos > 0:
                parts.append(f"{added_videos} відео")
            self._update_status(f"Додано {', '.join(parts)}. Всього: {len(self.images)}")
    
    def _create_metadata_panel(self):
        """Create metadata display panel with language tabs."""
        ctk.CTkLabel(
            self.metadata_frame,
            text="SEO метадані",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # Filename display
        ctk.CTkLabel(self.metadata_frame, text="Назва файлу:").pack(anchor="w", padx=10)
        self.filename_entry = ctk.CTkEntry(self.metadata_frame, width=320)
        self.filename_entry.pack(padx=10, pady=5)
        
        # Copy filename button
        self.btn_copy_filename = ctk.CTkButton(
            self.metadata_frame,
            text="📋 Копіювати",
            command=lambda: self._copy_to_clipboard(self.filename_entry.get()),
            width=100
        )
        self.btn_copy_filename.pack(anchor="e", padx=10)
        
        # Language tabs
        self.lang_tabview = ctk.CTkTabview(self.metadata_frame, width=320, height=400)
        self.lang_tabview.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.lang_tabview.add("🇺🇦 UA")
        self.lang_tabview.add("🇬🇧 EN")
        self.lang_tabview.add("🇷🇺 RU")
        
        # Create fields for each language
        self.lang_fields: Dict[str, Dict[str, ctk.CTkTextbox]] = {}
        for lang, tab_name in [("ua", "🇺🇦 UA"), ("en", "🇬🇧 EN"), ("ru", "🇷🇺 RU")]:
            tab = self.lang_tabview.tab(tab_name)
            self.lang_fields[lang] = {}
            
            # Alt text
            ctk.CTkLabel(tab, text="Alt текст:").pack(anchor="w", padx=5)
            alt_box = ctk.CTkTextbox(tab, height=60, width=300)
            alt_box.pack(padx=5, pady=2)
            self.lang_fields[lang]["alt_text"] = alt_box
            
            # Title
            ctk.CTkLabel(tab, text="Заголовок:").pack(anchor="w", padx=5)
            title_box = ctk.CTkTextbox(tab, height=40, width=300)
            title_box.pack(padx=5, pady=2)
            self.lang_fields[lang]["title"] = title_box
            
            # Description
            ctk.CTkLabel(tab, text="Опис:").pack(anchor="w", padx=5)
            desc_box = ctk.CTkTextbox(tab, height=80, width=300)
            desc_box.pack(padx=5, pady=2)
            self.lang_fields[lang]["description"] = desc_box
            
            # Tags field (for videos)
            ctk.CTkLabel(tab, text="Теги:").pack(anchor="w", padx=5)
            tags_box = ctk.CTkTextbox(tab, height=50, width=300)
            tags_box.pack(padx=5, pady=2)
            self.lang_fields[lang]["tags"] = tags_box
            
            # Copy all button
            ctk.CTkButton(
                tab,
                text=f"📋 Копіювати все ({lang.upper()})",
                command=lambda l=lang: self._copy_language_metadata(l),
                width=180
            ).pack(pady=10)
    
    def _create_status_bar(self):
        """Create status bar."""
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Готово. Додайте зображення для початку роботи.",
            anchor="w"
        )
        self.status_label.pack(side="left", padx=10)
        
        # Cancel button (hidden by default)
        self.btn_cancel = ctk.CTkButton(
            self.status_frame,
            text="Скасувати",
            command=self._cancel_processing,
            width=100,
            fg_color="red",
            hover_color="darkred"
        )
        self.btn_cancel.pack(side="right", padx=5)
        self.btn_cancel.pack_forget()  # Hide initially
        
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=200)
        self.progress_bar.pack(side="right", padx=10)
        self.progress_bar.set(0)
    
    def _set_buttons_enabled(self, enabled: bool):
        """Enable or disable all action buttons."""
        state = "normal" if enabled else "disabled"
        disabled_color = ("gray70", "gray35")
        
        if enabled:
            # Restore original colors
            self.btn_add.configure(state=state, fg_color=self._original_button_colors.get('btn_add'))
            self.btn_clear.configure(state=state, fg_color=self._original_button_colors.get('btn_clear'))
            self.btn_generate.configure(state=state, fg_color=self._original_button_colors.get('btn_generate'))
            self.btn_regenerate.configure(state=state, fg_color=self._original_button_colors.get('btn_regenerate'))
            self.btn_process.configure(state=state, fg_color=self._original_button_colors.get('btn_process'))
            self.btn_output.configure(state=state, fg_color=self._original_button_colors.get('btn_output'))
            self.ai_checkbox.configure(state=state)
            # Model dropdown should be readonly if AI is enabled, disabled otherwise
            if self.use_ai.get():
                self.model_dropdown.configure(state="readonly")
            else:
                self.model_dropdown.configure(state="disabled")
        else:
            # Disable and grey out
            self.btn_add.configure(state=state, fg_color=disabled_color)
            self.btn_clear.configure(state=state, fg_color=disabled_color)
            self.btn_generate.configure(state=state, fg_color=disabled_color)
            self.btn_regenerate.configure(state=state, fg_color=disabled_color)
            self.btn_process.configure(state=state, fg_color=disabled_color)
            self.btn_output.configure(state=state, fg_color=disabled_color)
            self.ai_checkbox.configure(state=state)
            self.model_dropdown.configure(state="disabled")
    
    def _cancel_processing(self):
        """Cancel ongoing processing operations."""
        self.cancel_event.set()
        self._update_status("Скасування обробки...")
        
        # Terminate FFmpeg processes if any
        for process in self.active_ffmpeg_processes:
            try:
                if process and process.poll() is None:  # Still running
                    process.terminate()
            except Exception:
                pass
        self.active_ffmpeg_processes.clear()
        
        # Reset state after a short delay to allow threads to check cancel event
        self.after(500, self._reset_processing_state)
    
    def _reset_processing_state(self):
        """Reset processing state and restore UI."""
        self.is_processing = False
        self.cancel_event.clear()
        self.btn_cancel.pack_forget()
        self._set_buttons_enabled(True)
        self.progress_bar.set(0)
        self._update_status("Обробку скасовано.")
    
    def _start_processing(self):
        """Set up UI for processing start."""
        self.is_processing = True
        self.cancel_event.clear()
        self.btn_cancel.pack(side="right", padx=5)
        self._set_buttons_enabled(False)
        self.progress_bar.set(0)
    
    def _end_processing(self):
        """Reset UI after processing completes."""
        self.is_processing = False
        self.btn_cancel.pack_forget()
        self._set_buttons_enabled(True)
        self.cancel_event.clear()
    
    # Event handlers
    def _on_category_change(self, value: str):
        """Handle category selection change."""
        self.current_attributes.category = value
        self._update_type_dropdown()
        self._update_property_dropdowns()
    
    def _on_type_change(self, value: str):
        """Handle type selection change."""
        self.current_attributes.product_type = value
        self._on_attribute_change(value)
    
    def _on_attribute_change(self, value: str = ""):
        """Handle any attribute change."""
        self.current_attributes.species = self.species_var.get()
        self.current_attributes.thickness = self.thickness_var.get()
        self.current_attributes.grade = self.grade_var.get()
    
    def _on_resolution_change(self, value: str):
        """Handle resolution preset change and update description."""
        # Find the preset key by matching name_ua
        for key, preset in self._resolution_presets.items():
            if preset["name_ua"] == value:
                self.resolution_desc.configure(text=preset["description_ua"])
                # Update converter's max_resolution
                self.converter.max_resolution = preset["resolution"]
                break
    
    def _get_selected_resolution(self) -> Optional[Tuple[int, int]]:
        """Get the currently selected resolution preset."""
        selected_name = self.resolution_var.get()
        for key, preset in self._resolution_presets.items():
            if preset["name_ua"] == selected_name:
                return preset["resolution"]
        return (1200, 1200)  # Default fallback
    
    def _on_ai_toggle(self):
        """Handle AI checkbox toggle - show/hide model picker."""
        if self.use_ai.get():
            # Show model picker before separator
            self.model_label.pack(side="left", padx=(10, 5), pady=5, before=self.toolbar_separator)
            self.model_dropdown.pack(side="left", padx=5, pady=5, before=self.toolbar_separator)
            # Load models if not loaded yet
            if self.gemini_client and len(self.model_dropdown.cget("values")) == 1:
                threading.Thread(target=self._load_available_models, daemon=True).start()
        else:
            # Hide model picker
            self.model_label.pack_forget()
            self.model_dropdown.pack_forget()
    
    def _load_available_models(self):
        """Load available Gemini models in background."""
        if not self.gemini_client:
            return
        
        try:
            models = self.gemini_client.list_available_models()
            # Update UI on main thread
            self.after(0, lambda: self.model_dropdown.configure(values=models))
            self.after(0, lambda: self._update_status(f"Завантажено {len(models)} моделей Gemini"))
        except Exception as e:
            self.after(0, lambda: self._update_status(f"Помилка завантаження моделей: {e}"))
    
    def _on_model_change(self, value: str):
        """Handle model selection change."""
        if self.gemini_client:
            self.gemini_client.config.model = value
            self._update_status(f"Обрано модель: {value}")
    
    def _update_type_dropdown(self):
        """Update type dropdown based on selected category."""
        category_name = self.category_var.get()
        
        # Find category key
        cat_key = ""
        for cat in self.renamer.get_category_options():
            if cat["name_ua"] == category_name:
                cat_key = cat["key"]
                break
        
        if cat_key:
            types = self.renamer.get_types_for_category(cat_key)
            type_values = [""] + [t["name_ua"] for t in types]
        else:
            type_values = [""]
        
        self.type_dropdown.configure(values=type_values)
        self.type_var.set("")
    
    def _update_property_dropdowns(self):
        """Update property dropdowns based on category."""
        category_name = self.category_var.get()
        
        # Find category key
        cat_key = ""
        for cat in self.renamer.get_category_options():
            if cat["name_ua"] == category_name:
                cat_key = cat["key"]
                break
        
        properties = self.renamer.get_properties_for_category(cat_key) if cat_key else []
        
        # Update thickness dropdown
        if any(p.startswith("thickness") for p in properties):
            thickness_list = next((p for p in properties if p.startswith("thickness")), "thickness")
            thickness_opts = self.renamer.get_list_options(thickness_list)
            self.thickness_dropdown.configure(values=[""] + [t["ua"] for t in thickness_opts])
        else:
            self.thickness_dropdown.configure(values=[""])
        self.thickness_var.set("")
        
        # Update grade dropdown
        if any(p.startswith("grade") for p in properties):
            grade_list = next((p for p in properties if p.startswith("grade")), "grade")
            grade_opts = self.renamer.get_list_options(grade_list)
            self.grade_dropdown.configure(values=[""] + [g["ua"] for g in grade_opts])
        else:
            self.grade_dropdown.configure(values=[""])
        self.grade_var.set("")
    
    # Actions
    def _add_media(self):
        """Open file dialog to add images and videos."""
        # Build filetypes based on available features
        image_exts = " ".join(f"*{ext}" for ext in IMAGE_EXTENSIONS)
        video_exts = " ".join(f"*{ext}" for ext in VIDEO_EXTENSIONS) if FFMPEG_AVAILABLE else ""
        
        filetypes = [("Зображення", image_exts)]
        if FFMPEG_AVAILABLE:
            filetypes.insert(0, ("Зображення та відео", f"{image_exts} {video_exts}"))
            filetypes.append(("Відео", video_exts))
        filetypes.append(("Усі файли", "*.*"))
        
        paths = filedialog.askopenfilenames(filetypes=filetypes)
        
        if paths:
            start_index = len(self.images)
            new_items = []
            added_images = 0
            added_videos = 0
            
            for i, path in enumerate(paths):
                path = Path(path)
                suffix = path.suffix.lower()
                
                # Skip videos if FFmpeg not available
                if suffix in VIDEO_EXTENSIONS and not FFMPEG_AVAILABLE:
                    continue
                    
                item = MediaItem(path, index=start_index + i + 1)
                self.images.append(item)
                new_items.append(item)
                
                if item.media_type == "video":
                    added_videos += 1
                else:
                    added_images += 1
            
            # Preload thumbnails in background thread
            threading.Thread(
                target=self._preload_thumbnails, 
                args=(new_items,), 
                daemon=True
            ).start()
            
            self._refresh_preview()
            
            # Create status message
            parts = []
            if added_images > 0:
                parts.append(f"{added_images} зображень")
            if added_videos > 0:
                parts.append(f"{added_videos} відео")
            self._update_status(f"Додано {', '.join(parts)}. Всього: {len(self.images)}")
    
    # Backward compatibility alias
    _add_images = _add_media
    
    def _preload_thumbnails(self, items: List[MediaItem]):
        """Preload thumbnails in background to speed up UI."""
        import tempfile
        
        for item in items:
            if item.path not in self._thumbnail_cache:
                try:
                    if item.media_type == "video" and self.video_converter:
                        # Extract video thumbnail
                        temp_dir = Path(tempfile.gettempdir()) / "ww-converter-thumbs"
                        temp_dir.mkdir(exist_ok=True)
                        thumb_path = temp_dir / f"{item.path.stem}-thumb.webp"
                        
                        # Extract thumbnail at 1 second mark
                        self.video_converter.extract_thumbnail(
                            item.path,
                            output_path=thumb_path,
                            time_offset=1.0,
                            size=(180, 140)
                        )
                        item.thumbnail_path = thumb_path
                        self._temp_thumbnails.append(thumb_path)
                        
                        # Load the extracted thumbnail
                        with Image.open(thumb_path) as img:
                            img.thumbnail((90, 70), Image.Resampling.LANCZOS)
                            # Use CTkImage for proper HighDPI scaling
                            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(90, 70))
                            self._thumbnail_cache[item.path] = photo
                        
                        # Also get video info
                        try:
                            item.video_info = self.video_converter.get_video_info(item.path)
                        except Exception:
                            pass
                    else:
                        # Image thumbnail - use CTkImage for proper HighDPI scaling
                        thumb = self.converter.get_thumbnail(item.path, size=(90, 70))
                        photo = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(90, 70))
                        self._thumbnail_cache[item.path] = photo
                except Exception as e:
                    print(f"Thumbnail error for {item.path}: {e}")
                    pass  # Silently skip failed thumbnails
    
    def _clear_images(self):
        """Clear all images."""
        self.images.clear()
        self.selected_image = None
        self.previous_selected = None
        self._thumbnail_cache.clear()  # Clear cached thumbnails
        self._refresh_preview()
        self._clear_metadata_display()
        self._update_status("Усі зображення видалено.")
    
    def _refresh_preview(self):
        """Refresh the image preview grid."""
        # Clear existing cards
        for card in self.image_cards:
            card.destroy()
        self.image_cards.clear()
        
        # Show/hide drop hint based on whether there are images
        if self.images:
            self.drop_hint.place_forget()
        else:
            self.drop_hint.place(relx=0.5, rely=0.5, anchor="center")
        
        # Create new cards
        for item in self.images:
            card = self._create_image_card(item)
            self.image_cards.append(card)
    
    def _create_image_card(self, item: MediaItem) -> ctk.CTkFrame:
        """Create a horizontal media list item with details."""
        # Determine if this item is selected
        is_selected = self.selected_image == item
        is_video = item.media_type == "video"
        
        # Card styling based on selection and media type
        if is_selected:
            border_color = ("#00aa00", "#00dd00")
        elif is_video:
            border_color = ("#0088cc", "#00aaff")  # Blue accent for videos
        else:
            border_color = ("gray60", "gray40")
        border_width = 3 if is_selected else 1
        fg_color = ("gray90", "gray25") if is_selected else ("gray85", "gray20")
        
        card = ctk.CTkFrame(
            self.preview_scroll,
            height=90,
            border_width=border_width,
            border_color=border_color,
            fg_color=fg_color
        )
        card.pack(fill="x", padx=5, pady=3)
        card.pack_propagate(False)
        
        # Store reference on item
        item.card_frame = card
        
        # Left accent bar for selected items
        if is_selected:
            accent = ctk.CTkFrame(card, width=4, fg_color=("#00aa00", "#00dd00"))
            accent.pack(side="left", fill="y")
        elif is_video:
            accent = ctk.CTkFrame(card, width=4, fg_color=("#0088cc", "#00aaff"))
            accent.pack(side="left", fill="y")
        
        # Thumbnail on left
        thumb_frame = ctk.CTkFrame(card, width=100, height=80, fg_color="transparent")
        thumb_frame.pack(side="left", padx=5, pady=5)
        thumb_frame.pack_propagate(False)
        
        try:
            # Use cached thumbnail if available
            if item.path in self._thumbnail_cache:
                photo = self._thumbnail_cache[item.path]
            elif item.media_type == "image":
                # Use CTkImage for proper HighDPI scaling
                thumb = self.converter.get_thumbnail(item.path, size=(90, 70))
                photo = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(90, 70))
                self._thumbnail_cache[item.path] = photo
            else:
                # Video without cached thumbnail - show placeholder
                photo = None
            
            if photo:
                item.thumbnail = photo
                img_label = ctk.CTkLabel(thumb_frame, image=photo, text="")
                img_label.pack(expand=True)
                
                # Add video badge overlay
                if is_video:
                    video_badge = ctk.CTkLabel(
                        thumb_frame,
                        text="🎬",
                        font=ctk.CTkFont(size=16),
                        fg_color=("black", "black"),
                        corner_radius=4,
                        width=25,
                        height=25
                    )
                    video_badge.place(relx=0.05, rely=0.05)
            else:
                # Placeholder for video without thumbnail
                ctk.CTkLabel(thumb_frame, text="🎬", font=ctk.CTkFont(size=24)).pack(expand=True)
        except Exception:
            placeholder = "🎬" if is_video else "[!]"
            ctk.CTkLabel(thumb_frame, text=placeholder, font=ctk.CTkFont(size=14)).pack(expand=True)
        
        # Info section in middle
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Top row: index + original filename + media type badge
        top_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        top_row.pack(fill="x")
        
        ctk.CTkLabel(
            top_row,
            text=f"#{item.index:02d}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#00aa00", "#00dd00") if is_selected else ("gray30", "gray70")
        ).pack(side="left")
        
        # Media type badge
        if is_video:
            ctk.CTkLabel(
                top_row,
                text=" [ВІДЕО]",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=("#0088cc", "#00aaff")
            ).pack(side="left")
        
        orig_name = item.path.name[:30] + "..." if len(item.path.name) > 30 else item.path.name
        ctk.CTkLabel(
            top_row,
            text=f"  {orig_name}",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60")
        ).pack(side="left")
        
        # Show video info if available
        if is_video and item.video_info:
            duration_mins = int(item.video_info.duration // 60)
            duration_secs = int(item.video_info.duration % 60)
            duration_str = f"{duration_mins}:{duration_secs:02d}"
            resolution_str = f"{item.video_info.width}x{item.video_info.height}"
            ctk.CTkLabel(
                top_row,
                text=f"  ({duration_str}, {resolution_str})",
                font=ctk.CTkFont(size=10),
                text_color=("gray50", "gray55")
            ).pack(side="left")
        
        # Middle row: new filename (if generated)
        if item.metadata:
            new_name = item.metadata.filename
            if len(new_name) > 50:
                new_name = new_name[:50] + "..."
            ctk.CTkLabel(
                info_frame,
                text=f"→ {new_name}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#00aa00", "#00dd00"),
                anchor="w"
            ).pack(fill="x")
            
            # Alt text preview
            alt_preview = item.metadata.ua.get("alt_text", "")[:60]
            if len(item.metadata.ua.get("alt_text", "")) > 60:
                alt_preview += "..."
            ctk.CTkLabel(
                info_frame,
                text=f"Alt: {alt_preview}",
                font=ctk.CTkFont(size=10),
                text_color=("gray50", "gray55"),
                anchor="w"
            ).pack(fill="x")
        else:
            ctk.CTkLabel(
                info_frame,
                text="⚠ Метадані не згенеровано",
                font=ctk.CTkFont(size=11),
                text_color=("orange", "#ffaa00"),
                anchor="w"
            ).pack(fill="x")
        
        # Right side: Rerun button
        btn_frame = ctk.CTkFrame(card, fg_color="transparent", width=100)
        btn_frame.pack(side="right", padx=10, pady=5)
        btn_frame.pack_propagate(False)
        
        rerun_btn = ctk.CTkButton(
            btn_frame,
            text="🔄",
            width=40,
            height=30,
            command=lambda it=item: self._regenerate_single(it),
            fg_color=("gray70", "gray35"),
            hover_color=("gray60", "gray45")
        )
        rerun_btn.pack(pady=5)
        ctk.CTkLabel(btn_frame, text="Оновити", font=ctk.CTkFont(size=9)).pack()
        
        # Click to select and drag to reorder - bind to card and all children
        def bind_interactions(widget, item=item):
            # Click handler - selects and starts drag
            def on_click(e, it=item):
                self._select_image(it)
                self._on_card_drag_start(e, it)
            
            widget.bind("<Button-1>", on_click)
            widget.bind("<B1-Motion>", lambda e, it=item: self._on_card_drag_motion(e, it))
            widget.bind("<ButtonRelease-1>", lambda e, it=item: self._on_card_drag_end(e, it))
            
            # Set cursor to indicate draggable
            widget.configure(cursor="hand2") if hasattr(widget, 'configure') else None
            
            for child in widget.winfo_children():
                bind_interactions(child, item)
        
        bind_interactions(card, item)
        
        return card
    
    def _select_image(self, item: ImageItem):
        """Select an image and display its metadata."""
        # Skip if same item
        if self.selected_image == item:
            return
        
        # Store previous and update current
        self.previous_selected = self.selected_image
        self.selected_image = item
        
        # Update only the affected cards (fast, no full refresh)
        self._update_card_selection()
        
        # Display metadata
        self._display_metadata(item)
    
    def _update_card_selection(self):
        """Update only the selection styling of affected cards (fast)."""
        # Deselect previous card
        if self.previous_selected and hasattr(self.previous_selected, 'card_frame') and self.previous_selected.card_frame:
            self._style_card_unselected(self.previous_selected.card_frame)
        
        # Select new card
        if self.selected_image and hasattr(self.selected_image, 'card_frame') and self.selected_image.card_frame:
            self._style_card_selected(self.selected_image.card_frame)
    
    def _style_card_selected(self, card: ctk.CTkFrame):
        """Apply selected styling to a card."""
        card.configure(
            border_color=("#00aa00", "#00dd00"),
            border_width=3,
            fg_color=("gray90", "gray25")
        )
    
    def _style_card_unselected(self, card: ctk.CTkFrame):
        """Apply unselected styling to a card."""
        card.configure(
            border_color=("gray60", "gray40"),
            border_width=1,
            fg_color=("gray85", "gray20")
        )
    
    # --- Drag-and-drop reordering methods ---
    
    def _on_card_drag_start(self, event, item: MediaItem):
        """Start dragging a card to reorder."""
        if self.is_processing:
            return  # Don't allow drag during processing
        
        self._drag_item = item
        self._drag_start_y = event.y_root
        
        # Change cursor to indicate dragging
        if item.card_frame:
            item.card_frame.configure(cursor="fleur")
            # Highlight the dragged card
            item.card_frame.configure(
                border_color=("#ffaa00", "#ffcc00"),
                border_width=3
            )
    
    def _on_card_drag_motion(self, event, item: MediaItem):
        """Handle drag motion - show drop indicator."""
        if not self._drag_item or self.is_processing:
            return
        
        # Find the card under the cursor
        target_index = self._get_drop_target_index(event.y_root)
        
        if target_index is not None and target_index != self._drag_target_index:
            self._drag_target_index = target_index
            self._update_drop_indicator(target_index)
    
    def _on_card_drag_end(self, event, item: MediaItem):
        """Complete the drag operation and reorder items."""
        if not self._drag_item or self.is_processing:
            self._cleanup_drag_state()
            return
        
        # Get the original and target indices
        original_index = self.images.index(self._drag_item)
        target_index = self._drag_target_index
        
        # Reset cursor and styling
        if self._drag_item.card_frame:
            self._drag_item.card_frame.configure(cursor="hand2")
        
        # Remove drop indicator
        self._remove_drop_indicator()
        
        # Perform the reorder if valid
        if target_index is not None and target_index != original_index:
            # Remove from original position and insert at target
            dragged = self.images.pop(original_index)
            
            # Adjust target index if needed (when moving down)
            if target_index > original_index:
                target_index -= 1
            
            self.images.insert(target_index, dragged)
            
            # Renumber all items and refresh the list
            self._renumber_items()
            self._refresh_preview()
            
            # Update status
            self._update_status(f"Файл #{original_index + 1} переміщено на позицію #{target_index + 1}")
        else:
            # Just refresh to reset styling
            self._refresh_preview()
        
        self._cleanup_drag_state()
    
    def _get_drop_target_index(self, y_root: int) -> Optional[int]:
        """Determine which position the item would be dropped at."""
        if not self.image_cards:
            return None
        
        for i, card in enumerate(self.image_cards):
            try:
                # Get card's position on screen
                card_y = card.winfo_rooty()
                card_height = card.winfo_height()
                card_center = card_y + card_height // 2
                
                # If cursor is above the center of this card, drop before it
                if y_root < card_center:
                    return i
            except Exception:
                pass
        
        # If below all cards, drop at the end
        return len(self.image_cards)
    
    def _update_drop_indicator(self, target_index: int):
        """Show visual indicator where the item will be dropped."""
        # Remove existing indicator
        self._remove_drop_indicator()
        
        # Create a thin horizontal line as drop indicator
        self._drag_indicator = ctk.CTkFrame(
            self.preview_scroll,
            height=4,
            fg_color=("#ffaa00", "#ffcc00")
        )
        
        # Position the indicator
        if target_index < len(self.image_cards):
            # Insert before the target card
            target_card = self.image_cards[target_index]
            self._drag_indicator.pack(before=target_card, fill="x", padx=10, pady=2)
        else:
            # Insert at the end
            self._drag_indicator.pack(fill="x", padx=10, pady=2)
    
    def _remove_drop_indicator(self):
        """Remove the drop position indicator."""
        if self._drag_indicator:
            self._drag_indicator.destroy()
            self._drag_indicator = None
    
    def _cleanup_drag_state(self):
        """Reset all drag-related state."""
        self._drag_item = None
        self._drag_start_y = 0
        self._drag_target_index = None
        self._remove_drop_indicator()
    
    def _renumber_items(self):
        """Update indices of all items after reordering."""
        for i, item in enumerate(self.images):
            item.index = i + 1
    
    # --- End drag-and-drop methods ---
    
    def _display_metadata(self, item: ImageItem):
        """Display metadata for selected image or video."""
        if item.metadata:
            # Filename
            self.filename_entry.delete(0, "end")
            self.filename_entry.insert(0, item.metadata.filename)
            
            # Check if this is a video with video-specific metadata
            is_video = item.media_type == "video" and item.video_metadata
            
            # Language fields
            for lang in ["ua", "en", "ru"]:
                if is_video:
                    # Use video-specific metadata structure
                    video_lang_data = item.video_metadata.get(lang, {})
                    # Handle video_tags - may be a string or list
                    video_tags = video_lang_data.get("video_tags", "")
                    if isinstance(video_tags, list):
                        video_tags = ", ".join(video_tags)
                    # Map video fields to display fields
                    field_mapping = {
                        "alt_text": video_lang_data.get("thumbnail_alt_text", ""),
                        "title": video_lang_data.get("video_title", ""),
                        "description": video_lang_data.get("video_description", ""),
                        "tags": video_tags
                    }
                else:
                    # Use standard image metadata structure
                    lang_data = getattr(item.metadata, lang, {})
                    field_mapping = {
                        "alt_text": lang_data.get("alt_text", ""),
                        "title": lang_data.get("title", ""),
                        "description": lang_data.get("description", ""),
                        "tags": lang_data.get("tags", "")
                    }
                
                # Update all fields including tags
                for field in ["alt_text", "title", "description", "tags"]:
                    textbox = self.lang_fields[lang][field]
                    textbox.delete("1.0", "end")
                    textbox.insert("1.0", field_mapping.get(field, ""))
        else:
            self._clear_metadata_display()
    
    def _clear_metadata_display(self):
        """Clear all metadata fields."""
        self.filename_entry.delete(0, "end")
        for lang in ["ua", "en", "ru"]:
            for field in ["alt_text", "title", "description", "tags"]:
                self.lang_fields[lang][field].delete("1.0", "end")
    
    def _generate_metadata(self):
        """Generate metadata for all images (only those without metadata)."""
        if not self.images:
            messagebox.showwarning("Немає зображень", "Спочатку додайте зображення.")
            return
        
        if self.is_processing:
            messagebox.showwarning("Обробка в процесі", "Зачекайте завершення поточної обробки.")
            return
        
        self._start_processing()
        self._update_status("Генерація метаданих...")
        
        # Run in thread to avoid blocking UI
        thread = threading.Thread(target=self._generate_metadata_thread)
        self.active_threads.append(thread)
        thread.start()
    
    def _regenerate_all(self):
        """Force regenerate metadata for ALL images."""
        if not self.images:
            messagebox.showwarning("Немає зображень", "Спочатку додайте зображення.")
            return
        
        if self.is_processing:
            messagebox.showwarning("Обробка в процесі", "Зачекайте завершення поточної обробки.")
            return
        
        # Clear existing metadata
        for item in self.images:
            item.metadata = None
        
        self._start_processing()
        self._update_status("Оновлення метаданих...")
        
        thread = threading.Thread(target=self._generate_metadata_thread)
        self.active_threads.append(thread)
        thread.start()
    
    def _regenerate_single(self, item: ImageItem):
        """Regenerate metadata for a single image."""
        if self.is_processing:
            messagebox.showwarning("Обробка в процесі", "Зачекайте завершення поточної обробки.")
            return
        
        self._update_status(f"Оновлення #{item.index}...")
        
        def regenerate():
            # Check for cancellation
            if self.cancel_event.is_set():
                self.after(0, lambda: self._update_status("Оновлення скасовано."))
                return
            
            use_ai = self.use_ai.get() and self.gemini_client is not None
            
            try:
                # Determine extension based on media type
                if item.media_type == "video":
                    extension = self.video_output_format.get()
                else:
                    extension = self.output_format.get()
                
                # ALWAYS generate filename algorithmically
                base_metadata = self.renamer.generate_basic_metadata(
                    self.current_attributes,
                    index=item.index,
                    extension=extension
                )
                
                if use_ai:
                    if item.media_type == "video":
                        # Use video-specific AI metadata generation
                        ai_result = self._generate_video_ai_metadata(item)
                        # Map video metadata structure to SEOMetadata structure
                        def map_video_to_seo(video_lang_data: Dict[str, Any], base_lang_data: Dict[str, str]) -> Dict[str, str]:
                            """Convert video metadata format to SEOMetadata format."""
                            return {
                                "alt_text": video_lang_data.get("thumbnail_alt_text", base_lang_data.get("alt_text", "")),
                                "title": video_lang_data.get("video_title", base_lang_data.get("title", "")),
                                "description": video_lang_data.get("video_description", base_lang_data.get("description", ""))
                            }
                        
                        item.metadata = SEOMetadata(
                            filename=base_metadata.filename,
                            ua=map_video_to_seo(ai_result.get("ua", {}), base_metadata.ua),
                            en=map_video_to_seo(ai_result.get("en", {}), base_metadata.en),
                            ru=map_video_to_seo(ai_result.get("ru", {}), base_metadata.ru)
                        )
                        # Store full video-specific metadata (including tags)
                        item.video_metadata = ai_result
                    else:
                        # Use Gemini for image descriptions/alt text/titles
                        ai_result = self.gemini_client.generate_seo_metadata(
                            image_path=item.path,
                            category=self.current_attributes.category,
                            product_type=self.current_attributes.product_type,
                            species=self.current_attributes.species,
                            thickness=self.current_attributes.thickness,
                            grade=self.current_attributes.grade,
                        )
                        # Combine: algorithmic filename + AI descriptions
                        item.metadata = SEOMetadata(
                            filename=base_metadata.filename,
                            ua=ai_result.get("ua", base_metadata.ua),
                            en=ai_result.get("en", base_metadata.en),
                            ru=ai_result.get("ru", base_metadata.ru)
                        )
                else:
                    item.metadata = base_metadata
                    
            except Exception:
                item.metadata = self.renamer.generate_basic_metadata(
                    self.current_attributes,
                    index=item.index,
                    extension=self.output_format.get()
                )
            
            self.after(0, self._refresh_preview)
            self.after(0, lambda: self._display_metadata(item))
            self.after(0, lambda: self._update_status(f"Оновлено #{item.index}"))
        
        thread = threading.Thread(target=regenerate)
        thread.start()
    
    def _generate_metadata_thread(self):
        """Background thread for metadata generation."""
        total = len(self.images)
        use_ai = self.use_ai.get() and self.gemini_client is not None
        
        for i, item in enumerate(self.images):
            # Check for cancellation
            if self.cancel_event.is_set():
                self.after(0, self._reset_processing_state)
                self.after(0, lambda: self._update_status("Генерацію метаданих скасовано."))
                return
            try:
                # Determine extension based on media type
                if item.media_type == "video":
                    extension = self.video_output_format.get()
                else:
                    extension = self.output_format.get()
                
                # ALWAYS generate filename algorithmically first
                base_metadata = self.renamer.generate_basic_metadata(
                    self.current_attributes,
                    index=item.index,
                    extension=extension
                )
                
                if use_ai:
                    if item.media_type == "video":
                        # Use video-specific AI metadata generation
                        ai_result = self._generate_video_ai_metadata(item)
                    else:
                        # Use Gemini for image descriptions/alt text/titles
                        ai_result = self.gemini_client.generate_seo_metadata(
                            image_path=item.path,
                            category=self.current_attributes.category,
                            product_type=self.current_attributes.product_type,
                            species=self.current_attributes.species,
                            thickness=self.current_attributes.thickness,
                            grade=self.current_attributes.grade,
                        )
                    
                    # Combine: algorithmic filename + AI descriptions
                    if item.media_type == "video":
                        # Map video metadata structure to SEOMetadata structure
                        def map_video_to_seo(video_lang_data: Dict[str, Any], base_lang_data: Dict[str, str]) -> Dict[str, str]:
                            """Convert video metadata format to SEOMetadata format."""
                            return {
                                "alt_text": video_lang_data.get("thumbnail_alt_text", base_lang_data.get("alt_text", "")),
                                "title": video_lang_data.get("video_title", base_lang_data.get("title", "")),
                                "description": video_lang_data.get("video_description", base_lang_data.get("description", ""))
                            }
                        
                        item.metadata = SEOMetadata(
                            filename=base_metadata.filename,
                            ua=map_video_to_seo(ai_result.get("ua", {}), base_metadata.ua),
                            en=map_video_to_seo(ai_result.get("en", {}), base_metadata.en),
                            ru=map_video_to_seo(ai_result.get("ru", {}), base_metadata.ru)
                        )
                        # Store full video-specific metadata (including tags)
                        item.video_metadata = ai_result
                    else:
                        # Images use standard structure
                        # Merge AI results with base metadata, ensuring all fields are present
                        def merge_metadata(ai_lang_data: Dict[str, Any], base_lang_data: Dict[str, str]) -> Dict[str, str]:
                            """Merge AI metadata with base metadata, ensuring tags are included."""
                            merged = base_lang_data.copy()
                            # Update with AI data if present
                            if isinstance(ai_lang_data, dict):
                                for field in ["alt_text", "title", "description", "tags"]:
                                    if field in ai_lang_data and ai_lang_data[field]:
                                        merged[field] = ai_lang_data[field]
                            # Ensure tags exist (use base if AI didn't provide)
                            if "tags" not in merged or not merged.get("tags"):
                                merged["tags"] = base_lang_data.get("tags", "")
                            return merged
                        
                        item.metadata = SEOMetadata(
                            filename=base_metadata.filename,
                            ua=merge_metadata(ai_result.get("ua", {}), base_metadata.ua),
                            en=merge_metadata(ai_result.get("en", {}), base_metadata.en),
                            ru=merge_metadata(ai_result.get("ru", {}), base_metadata.ru)
                        )
                else:
                    # Use fully algorithmic generation
                    item.metadata = base_metadata
                    
            except Exception as e:
                # Fallback to fully algorithmic
                extension = self.video_output_format.get() if item.media_type == "video" else self.output_format.get()
                item.metadata = self.renamer.generate_basic_metadata(
                    self.current_attributes,
                    index=item.index,
                    extension=extension
                )
            
            # Update progress
            progress = (i + 1) / total
            self.after(0, lambda p=progress: self.progress_bar.set(p))
        
        # Check for cancellation before finalizing
        if self.cancel_event.is_set():
            self.after(0, self._reset_processing_state)
            self.after(0, lambda: self._update_status("Генерацію метаданих скасовано."))
            return
        
        # Count by type for status message
        images_count = sum(1 for img in self.images if img.media_type == "image")
        videos_count = sum(1 for img in self.images if img.media_type == "video")
        
        parts = []
        if images_count > 0:
            parts.append(f"{images_count} зображень")
        if videos_count > 0:
            parts.append(f"{videos_count} відео")
        status_msg = f"Згенеровано метадані для {', '.join(parts)}."
        
        # Refresh UI and reset state
        self.after(0, self._refresh_preview)
        self.after(0, lambda: self._update_status(status_msg))
        self.after(0, self._end_processing)
    
    def _generate_video_ai_metadata(self, item: MediaItem) -> Dict[str, Any]:
        """Generate AI metadata for a video using its thumbnail."""
        if not self.gemini_client:
            return {}
        
        # Use extracted thumbnail if available
        thumbnail_path = item.thumbnail_path
        video_duration = item.video_info.duration if item.video_info else 0.0
        
        return self.gemini_client.generate_video_seo_metadata(
            video_path=item.path,  # Pass full video for comprehensive analysis
            thumbnail_path=thumbnail_path,
            video_duration=video_duration,
            category=self.current_attributes.category,
            product_type=self.current_attributes.product_type,
            species=self.current_attributes.species,
            thickness=self.current_attributes.thickness,
            grade=self.current_attributes.grade,
            video_type="product showcase",  # Default video type in English
        )
    
    def _process_media(self):
        """Convert and save all images and videos."""
        if not self.images:
            messagebox.showwarning("Немає файлів", "Спочатку додайте зображення або відео.")
            return
        
        if self.is_processing:
            messagebox.showwarning("Обробка в процесі", "Зачекайте завершення поточної обробки.")
            return
        
        # Check if metadata is generated - don't auto-generate to avoid double Gemini calls
        if not all(img.metadata for img in self.images):
            messagebox.showwarning(
                "Метадані відсутні",
                "Спочатку згенеруйте назви (кнопка 'Згенерувати назви')"
            )
            return
        
        if not self.output_folder and not self.use_subfolder.get():
            self._select_output_folder()
            if not self.output_folder:
                return
        
        self._start_processing()
        self._update_status("Обробка файлів...")
        
        thread = threading.Thread(target=self._process_media_thread)
        self.active_threads.append(thread)
        thread.start()
    
    # Backward compatibility alias
    _process_images = _process_media
    
    def _process_media_thread(self):
        """Background thread for image and video processing."""
        total = len(self.images)
        
        # Check for cancellation at start
        if self.cancel_event.is_set():
            self.after(0, self._reset_processing_state)
            return
        
        # Update image converter settings
        self.converter.output_format = self.output_format.get()
        self.converter.quality = self.quality.get()
        self.converter.max_resolution = self._get_selected_resolution()
        
        # Update video converter settings if available
        if self.video_converter:
            video_preset = self._get_selected_video_preset()
            self.video_converter.output_format = self.video_output_format.get()
            self.video_converter.crf = self.video_quality.get()
            self.video_converter.max_resolution = video_preset.get("resolution")
            self.video_converter.preset = video_preset.get("preset", "medium")
        
        # Determine output folder
        if self.use_subfolder.get() and self.images:
            # Use source folder + seo-media subfolder
            source_folder = self.images[0].path.parent
            actual_output_folder = source_folder / "seo-media"
            actual_output_folder.mkdir(exist_ok=True)
        else:
            actual_output_folder = self.output_folder
        
        # Store for JSON export
        self._last_output_folder = actual_output_folder
        
        processed_images = 0
        processed_videos = 0
        failed_items = []
        
        for i, item in enumerate(self.images):
            # Check for cancellation before each item
            if self.cancel_event.is_set():
                self.after(0, self._reset_processing_state)
                self.after(0, lambda: self._update_status("Обробку скасовано."))
                return
            try:
                # Update progress more frequently
                progress = (i + 1) / total
                current_idx = i + 1
                self.after(0, lambda p=progress: self.progress_bar.set(p))
                self.after(0, lambda idx=current_idx, tot=total: 
                    self._update_status(f"Обробка файлу {idx}/{tot}..."))
                
                if item.media_type == "video":
                    # Process video
                    self._process_single_video(item, actual_output_folder)
                    processed_videos += 1
                else:
                    # Process image
                    self._process_single_image(item, actual_output_folder)
                    processed_images += 1
                
                item.processed = True
                
            except Exception as e:
                error_msg = str(e)
                failed_items.append({
                    "item": item,
                    "error": error_msg
                })
                print(f"Error processing {item.path}: {error_msg}")
                # Update status for failed item
                self.after(0, lambda idx=item.index, err=error_msg[:50]: 
                    self._update_status(f"❌ Помилка обробки файлу #{idx}: {err}..."))
        
        # Check for cancellation before finalizing
        if self.cancel_event.is_set():
            self.after(0, self._reset_processing_state)
            self.after(0, lambda: self._update_status("Обробку скасовано."))
            return
        
        # Export JSON
        try:
            self._export_json(actual_output_folder)
        except Exception as e:
            print(f"Error exporting JSON: {e}")
            self.after(0, lambda: self._update_status(f"⚠️ Помилка експорту JSON: {e}"))
        
        # Create comprehensive status message
        success_count = processed_images + processed_videos
        failed_count = len(failed_items)
        
        parts = []
        if processed_images > 0:
            parts.append(f"{processed_images} зображень")
        if processed_videos > 0:
            parts.append(f"{processed_videos} відео")
        
        if failed_count == 0:
            # All successful
            status_msg = f"✅ Успішно збережено {', '.join(parts)} до {actual_output_folder}"
            self.after(0, lambda: self._update_status(status_msg))
            self.after(0, lambda: messagebox.showinfo(
                "Готово",
                f"Оброблено {success_count} файлів успішно!\n\n"
                f"Збережено до:\n{actual_output_folder}"
            ))
        else:
            # Some failed
            status_msg = f"⚠️ Оброблено {success_count} з {total} файлів. Помилок: {failed_count}"
            self.after(0, lambda: self._update_status(status_msg))
            
            # Show detailed error dialog
            error_details = "\n".join([
                f"#{item['item'].index}: {item['item'].path.name}\n  {item['error'][:100]}"
                for item in failed_items[:5]  # Show first 5 errors
            ])
            if len(failed_items) > 5:
                error_details += f"\n\n... та ще {len(failed_items) - 5} помилок"
            
            self.after(0, lambda: messagebox.showwarning(
                "Обробка завершена з помилками",
                f"Успішно оброблено: {success_count} файлів\n"
                f"Помилок: {failed_count}\n\n"
                f"Деталі помилок:\n{error_details}\n\n"
                f"Збережено до:\n{actual_output_folder}"
            ))
        
        # Reset processing state
        self.after(0, self._end_processing)
    
    # Backward compatibility alias
    _process_images_thread = _process_media_thread
    
    def _process_single_image(self, item: MediaItem, output_folder: Path):
        """Process a single image file."""
        if item.metadata:
            output_path = output_folder / item.metadata.filename
        else:
            output_path = output_folder / f"image-{item.index:03d}.{self.output_format.get()}"
        
        # Store output path on item for JSON export
        item.output_path = output_path
        
        # Convert image
        self.converter.convert_image(item.path, output_path)
        
        # Write metadata
        if item.metadata:
            MetadataHandler.write_seo_metadata(
                output_path,
                output_path,
                filename=item.metadata.filename,
                ua=item.metadata.ua,
                en=item.metadata.en,
                ru=item.metadata.ru,
            )
    
    def _process_single_video(self, item: MediaItem, output_folder: Path):
        """Process a single video file."""
        if not self.video_converter:
            raise RuntimeError("Video converter not available")
        
        # Determine output filename
        if item.metadata:
            base_name = Path(item.metadata.filename).stem
        else:
            base_name = f"video-{item.index:03d}"
        
        # Check if dual format generation is enabled
        generate_dual = hasattr(self, 'generate_dual_format_var') and self.generate_dual_format_var.get()
        
        # Determine which formats to generate
        if generate_dual:
            # Generate both MP4 (H.264) and WebM (VP9)
            formats_to_generate = [
                ("mp4", "h264"),
                ("webm", "vp9")
            ]
        else:
            # Generate only the selected format
            video_ext = self.video_output_format.get()
            codec_map = {
                "mp4": "h264",
                "webm": "vp9"
            }
            formats_to_generate = [(video_ext, codec_map.get(video_ext, "h264"))]
        
        output_paths = []
        total_formats = len(formats_to_generate)
        current_format_index = [0]  # Use list to allow modification in nested function
        
        # Convert video with progress callback
        def progress_callback(progress, format_name=""):
            # Check for cancellation
            if self.cancel_event.is_set():
                raise RuntimeError("Конвертацію скасовано користувачем")
            
            format_label = f" ({format_name})" if format_name else ""
            # Calculate overall progress across all formats
            format_progress = progress.percent / 100.0
            overall_progress = (current_format_index[0] + format_progress) / total_formats
            
            # Update status with video conversion progress
            self.after(0, lambda p=progress, fmt=format_label: self._update_status(
                f"Конвертація відео #{item.index}{fmt}: {p.percent:.0f}% "
                f"(швидкість: {p.speed:.1f}x, залишилось: {int(p.eta_seconds)}с)"
            ))
            # Update progress bar with overall progress
            self.after(0, lambda op=overall_progress: self.progress_bar.set(op))
        
        try:
            # Update status before starting
            format_list = " + ".join([fmt.upper() for fmt, _ in formats_to_generate])
            self.after(0, lambda: self._update_status(f"Початок конвертації відео #{item.index} ({format_list}): {item.path.name}"))
            
            for format_idx, (format_ext, codec) in enumerate(formats_to_generate):
                # Check for cancellation before each format
                if self.cancel_event.is_set():
                    raise RuntimeError("Конвертацію скасовано користувачем")
                
                current_format_index[0] = format_idx
                output_path = output_folder / f"{base_name}.{format_ext}"
                output_paths.append(output_path)
                
                # Create a new converter instance with the appropriate codec and format
                from src.core.video_converter import VideoConverter
                converter = VideoConverter(
                    output_format=format_ext,
                    codec=codec,
                    crf=self.video_quality.get(),
                    max_resolution=self.video_converter.max_resolution,
                    preserve_aspect_ratio=self.video_converter.preserve_aspect_ratio,
                    include_audio=self.video_converter.include_audio,
                    audio_bitrate=self.video_converter.audio_bitrate,
                    preset=self.video_converter.preset
                )
                
                # Convert video with format-specific callback
                def format_progress_callback(p):
                    progress_callback(p, format_ext.upper())
                
                converter.convert_video(
                    item.path,
                    output_path,
                    progress_callback=format_progress_callback
                )
                
                # Mark this format as complete
                current_format_index[0] = format_idx + 1
                
                # Verify output file exists and has content
                if not output_path.exists():
                    raise RuntimeError(f"Файл не було створено: {output_path}")
                
                file_size = output_path.stat().st_size
                if file_size == 0:
                    raise RuntimeError(f"Створено порожній файл (0 байт): {output_path}")
                
                # Convert bytes to MB for display
                size_mb = file_size / (1024 * 1024)
                self.after(0, lambda fmt=format_ext.upper(), sz=size_mb: self._update_status(
                    f"Відео #{item.index} ({fmt}) успішно конвертовано ({sz:.2f} MB)"
                ))
            
            # Store primary output path on item for JSON export (use first format)
            item.output_path = output_paths[0]
            
            # Update final status
            total_size = sum(p.stat().st_size for p in output_paths) / (1024 * 1024)
            format_summary = " + ".join([f"{p.suffix[1:].upper()}" for p in output_paths])
            self.after(0, lambda: self._update_status(
                f"Відео #{item.index} успішно конвертовано ({format_summary}, {total_size:.2f} MB)"
            ))
            
        except Exception as e:
            error_msg = str(e)
            # Provide user-friendly error message
            if "FFmpeg" in error_msg or "ffmpeg" in error_msg.lower():
                user_msg = f"Помилка конвертації відео #{item.index}:\n{error_msg}\n\nПеревірте встановлення FFmpeg та підтримку кодека."
            else:
                user_msg = f"Помилка обробки відео #{item.index}:\n{error_msg}"
            
            # Show error in status and log
            self.after(0, lambda: self._update_status(f"❌ Помилка відео #{item.index}"))
            print(f"Video conversion error for {item.path}: {error_msg}")
            
            # Re-raise to be caught by _process_media_thread
            raise RuntimeError(user_msg) from e
        
        # Extract poster/thumbnail if enabled (only once, from first output)
        if hasattr(self, 'extract_thumbnail_var') and self.extract_thumbnail_var.get():
            poster_path = output_folder / f"{base_name}-poster.webp"
            try:
                self.after(0, lambda: self._update_status(f"Витягнення постеру для відео #{item.index}..."))
                
                self.video_converter.extract_thumbnail(
                    item.path,
                    output_path=poster_path,
                    time_offset=1.0,
                    size=(1200, 1200)  # SEO optimal size
                )
                
                # Verify poster was created
                if poster_path.exists() and poster_path.stat().st_size > 0:
                    # Write metadata to poster image
                    if item.metadata:
                        MetadataHandler.write_seo_metadata(
                            poster_path,
                            poster_path,
                            filename=poster_path.name,
                            ua=item.metadata.ua,
                            en=item.metadata.en,
                            ru=item.metadata.ru,
                        )
                    self.after(0, lambda: self._update_status(f"Постер створено для відео #{item.index}"))
                else:
                    self.after(0, lambda: self._update_status(f"⚠️ Не вдалося створити постер для відео #{item.index}"))
                    
            except Exception as e:
                error_msg = f"Помилка витягнення постеру: {str(e)}"
                self.after(0, lambda: self._update_status(f"⚠️ {error_msg}"))
                print(f"Error extracting poster for {item.path}: {e}")
    
    def _select_output_folder(self):
        """Select output folder."""
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder = Path(folder)
            self._update_status(f"Папка виводу: {self.output_folder}")
    
    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        self.clipboard_clear()
        self.clipboard_append(text)
        self._update_status("Скопійовано до буфера обміну!")
    
    def _copy_language_metadata(self, lang: str):
        """Copy all metadata for a language."""
        parts = []
        for field in ["alt_text", "title", "description", "tags"]:
            value = self.lang_fields[lang][field].get("1.0", "end").strip()
            if value:  # Only include non-empty fields
                parts.append(f"{field}: {value}")
        
        text = "\n".join(parts)
        self._copy_to_clipboard(text)
    
    def _update_status(self, message: str):
        """Update status bar message."""
        self.status_label.configure(text=message)
    
    def _export_json(self, output_folder: Path):
        """Export all image metadata to JSON file for WordPress import."""
        if not self.images or not any(img.metadata for img in self.images):
            return
        
        settings = ExportSettings(
            category=self.current_attributes.category,
            product_type=self.current_attributes.product_type,
            species=self.current_attributes.species,
            thickness=self.current_attributes.thickness,
            grade=self.current_attributes.grade,
            output_format=self.output_format.get(),
            quality=self.quality.get(),
        )
        
        try:
            json_path = WordPressExporter.export_to_json(
                images=self.images,
                output_folder=output_folder,
                settings=settings,
                filename="export.json"
            )
            print(f"JSON exported to: {json_path}")
        except Exception as e:
            print(f"Error exporting JSON: {e}")


def run_app():
    """Run the application."""
    app = WoodWayConverterApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()

