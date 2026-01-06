"""
Image conversion module for WebP, JPEG, PNG with quality and resize options.
"""

from pathlib import Path
from typing import Optional, Tuple, Literal, Dict
from PIL import Image
import io


ImageFormat = Literal["webp", "jpeg", "png"]

# SEO-optimized resolution presets for 2026
# Based on Core Web Vitals and common viewport sizes
RESOLUTION_PRESETS: Dict[str, Dict] = {
    "seo_optimal": {
        "name_ua": "🏆 SEO Оптимальний (рекомендовано)",
        "name_en": "SEO Optimal (recommended)",
        "resolution": (1200, 1200),
        "description_ua": "Ідеальний баланс якості та швидкості. Оптимізовано для Google Core Web Vitals, соцмереж та мобільних пристроїв.",
        "description_en": "Perfect balance of quality and speed. Optimized for Core Web Vitals, social sharing, and mobile.",
    },
    "high_quality": {
        "name_ua": "📷 Висока якість",
        "name_en": "High Quality",
        "resolution": (1920, 1920),
        "description_ua": "Для детальних зображень продуктів. Більший розмір файлу.",
        "description_en": "For detailed product images. Larger file size.",
    },
    "social_media": {
        "name_ua": "📱 Соцмережі",
        "name_en": "Social Media",
        "resolution": (1080, 1080),
        "description_ua": "Оптимізовано для Instagram, Facebook, Pinterest.",
        "description_en": "Optimized for Instagram, Facebook, Pinterest.",
    },
    "thumbnail": {
        "name_ua": "🖼️ Мініатюра",
        "name_en": "Thumbnail",
        "resolution": (600, 600),
        "description_ua": "Для галерей та списків товарів. Швидке завантаження.",
        "description_en": "For galleries and product lists. Fast loading.",
    },
    "original": {
        "name_ua": "📐 Оригінал (без зміни)",
        "name_en": "Original (no resize)",
        "resolution": None,
        "description_ua": "Зберегти оригінальний розмір. Може вплинути на швидкість сайту.",
        "description_en": "Keep original size. May affect site speed.",
    },
}


class ImageConverter:
    """
    Handles image conversion with configurable quality and resolution.
    """
    
    SUPPORTED_INPUT = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'}
    SUPPORTED_OUTPUT = {'webp', 'jpeg', 'png'}
    
    def __init__(
        self,
        output_format: ImageFormat = "webp",
        quality: int = 85,
        max_resolution: Optional[Tuple[int, int]] = None,
        preserve_aspect_ratio: bool = True
    ):
        """
        Initialize the converter.
        
        Args:
            output_format: Target format (webp, jpeg, png)
            quality: Compression quality (1-100)
            max_resolution: Optional max dimensions (width, height)
            preserve_aspect_ratio: Keep aspect ratio when resizing
        """
        self.output_format = output_format
        self.quality = max(1, min(100, quality))
        self.max_resolution = max_resolution
        self.preserve_aspect_ratio = preserve_aspect_ratio
    
    def convert_image(
        self,
        input_path: Path,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Convert a single image.
        
        Args:
            input_path: Source image path
            output_path: Destination path (optional, auto-generated if not provided)
            
        Returns:
            Path to the converted image
        """
        input_path = Path(input_path)
        
        if input_path.suffix.lower() not in self.SUPPORTED_INPUT:
            raise ValueError(f"Unsupported input format: {input_path.suffix}")
        
        # Open and process image
        with Image.open(input_path) as img:
            # Convert to RGB if necessary (for JPEG/WebP)
            if img.mode in ('RGBA', 'LA', 'P'):
                if self.output_format == 'jpeg':
                    # JPEG doesn't support transparency - add white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif self.output_format == 'webp':
                    # WebP supports RGBA
                    if img.mode == 'P':
                        img = img.convert('RGBA')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if needed
            if self.max_resolution:
                img = self._resize_image(img)
            
            # Generate output path
            if output_path is None:
                output_path = input_path.with_suffix(f'.{self.output_format}')
            else:
                output_path = Path(output_path)
            
            # Save with appropriate settings
            save_kwargs = self._get_save_kwargs()
            img.save(output_path, **save_kwargs)
            
        return output_path
    
    def convert_to_bytes(self, input_path: Path) -> bytes:
        """
        Convert image and return as bytes (for preview/in-memory operations).
        
        Args:
            input_path: Source image path
            
        Returns:
            Converted image as bytes
        """
        input_path = Path(input_path)
        
        with Image.open(input_path) as img:
            # Same processing as convert_image
            if img.mode in ('RGBA', 'LA', 'P'):
                if self.output_format == 'jpeg':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif self.output_format == 'webp':
                    if img.mode == 'P':
                        img = img.convert('RGBA')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            if self.max_resolution:
                img = self._resize_image(img)
            
            buffer = io.BytesIO()
            save_kwargs = self._get_save_kwargs()
            img.save(buffer, **save_kwargs)
            return buffer.getvalue()
    
    def get_thumbnail(
        self,
        input_path: Path,
        size: Tuple[int, int] = (200, 200)
    ) -> Image.Image:
        """
        Generate a thumbnail for preview.
        
        Args:
            input_path: Source image path
            size: Thumbnail dimensions
            
        Returns:
            PIL Image thumbnail
        """
        with Image.open(input_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            # Convert to RGB for consistency
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            return img.copy()
    
    def _resize_image(self, img: Image.Image) -> Image.Image:
        """Resize image while optionally preserving aspect ratio."""
        if not self.max_resolution:
            return img
        
        max_w, max_h = self.max_resolution
        orig_w, orig_h = img.size
        
        if orig_w <= max_w and orig_h <= max_h:
            return img
        
        if self.preserve_aspect_ratio:
            ratio = min(max_w / orig_w, max_h / orig_h)
            new_size = (int(orig_w * ratio), int(orig_h * ratio))
        else:
            new_size = (max_w, max_h)
        
        return img.resize(new_size, Image.Resampling.LANCZOS)
    
    def _get_save_kwargs(self) -> dict:
        """Get format-specific save parameters."""
        if self.output_format == 'webp':
            return {
                'format': 'WEBP',
                'quality': self.quality,
                'method': 4,  # Compression method (0-6, higher = slower but better)
            }
        elif self.output_format == 'jpeg':
            return {
                'format': 'JPEG',
                'quality': self.quality,
                'optimize': True,
            }
        elif self.output_format == 'png':
            return {
                'format': 'PNG',
                'optimize': True,
            }
        else:
            raise ValueError(f"Unsupported output format: {self.output_format}")
    
    @staticmethod
    def get_image_info(path: Path) -> dict:
        """
        Get information about an image file.
        
        Args:
            path: Image file path
            
        Returns:
            Dictionary with image info (size, format, dimensions)
        """
        path = Path(path)
        with Image.open(path) as img:
            return {
                'filename': path.name,
                'format': img.format,
                'mode': img.mode,
                'width': img.width,
                'height': img.height,
                'size_bytes': path.stat().st_size,
            }

