"""
Video conversion module for web-optimized video output.

Supports conversion to MP4 (H.264) and WebM (VP9) with configurable quality,
resolution presets, and automatic thumbnail extraction.
"""

from pathlib import Path
from typing import Optional, Tuple, Literal, Dict, Any, Callable
from dataclasses import dataclass
import subprocess
import json
import tempfile
import shutil
import sys
import platform
import threading

# Check for ffmpeg-python availability
try:
    import ffmpeg
    FFMPEG_PYTHON_AVAILABLE = True
except ImportError:
    FFMPEG_PYTHON_AVAILABLE = False


VideoFormat = Literal["mp4", "webm"]
VideoCodec = Literal["h264", "h265", "vp9", "av1"]


@dataclass
class VideoInfo:
    """Information about a video file."""
    filename: str
    format: str
    codec: str
    width: int
    height: int
    duration: float  # seconds
    fps: float
    bitrate: int  # bits per second
    size_bytes: int
    has_audio: bool
    audio_codec: Optional[str] = None


@dataclass
class ConversionProgress:
    """Progress information during video conversion."""
    current_time: float  # seconds processed
    total_duration: float  # total duration
    percent: float  # 0-100
    speed: float  # processing speed multiplier (e.g., 2.0 = 2x realtime)
    eta_seconds: float  # estimated time remaining


# SEO-optimized resolution presets for web video (2025-2026 standards)
RESOLUTION_PRESETS: Dict[str, Dict[str, Any]] = {
    "seo_optimal": {
        "name_ua": "🎬 SEO Оптимальний (720p)",
        "name_en": "SEO Optimal (720p)",
        "resolution": (1280, 720),
        "crf": 23,
        "preset": "medium",
        "description_ua": "Ідеальний баланс якості та розміру. Рекомендовано для продуктових відео.",
        "description_en": "Perfect balance of quality and size. Recommended for product videos.",
    },
    "high_quality": {
        "name_ua": "📽️ Висока якість (1080p)",
        "name_en": "High Quality (1080p)",
        "resolution": (1920, 1080),
        "crf": 20,
        "preset": "slow",
        "description_ua": "Для презентаційних та демонстраційних відео. Більший розмір файлу.",
        "description_en": "For presentation and demo videos. Larger file size.",
    },
    "fast_loading": {
        "name_ua": "⚡ Швидке завантаження (480p)",
        "name_en": "Fast Loading (480p)",
        "resolution": (854, 480),
        "crf": 28,
        "preset": "fast",
        "description_ua": "Для попереднього перегляду та мобільних пристроїв. Мінімальний розмір.",
        "description_en": "For previews and mobile devices. Minimum size.",
    },
    "social_media": {
        "name_ua": "📱 Соцмережі (1080p квадрат)",
        "name_en": "Social Media (1080p square)",
        "resolution": (1080, 1080),
        "crf": 23,
        "preset": "medium",
        "description_ua": "Оптимізовано для Instagram, Facebook. Квадратний формат.",
        "description_en": "Optimized for Instagram, Facebook. Square format.",
    },
    "original": {
        "name_ua": "📐 Оригінал (без зміни роздільності)",
        "name_en": "Original (no resize)",
        "resolution": None,
        "crf": 23,
        "preset": "medium",
        "description_ua": "Зберегти оригінальну роздільність. Тільки оптимізація кодека.",
        "description_en": "Keep original resolution. Codec optimization only.",
    },
}


class FFmpegNotFoundError(Exception):
    """Raised when FFmpeg binary is not found on the system."""
    pass


class VideoConversionError(Exception):
    """Raised when video conversion fails."""
    pass


class VideoConverter:
    """
    Handles video conversion with configurable quality, format, and resolution.
    
    Uses FFmpeg for transcoding with web-optimized settings including:
    - H.264/H.265 for MP4
    - VP9/AV1 for WebM  
    - Automatic faststart flag for web streaming
    - CRF-based quality control
    """
    
    SUPPORTED_INPUT = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv', '.ogv'}
    SUPPORTED_OUTPUT = {'mp4', 'webm'}
    
    def __init__(
        self,
        output_format: VideoFormat = "mp4",
        codec: Optional[VideoCodec] = None,
        crf: int = 23,
        preset: str = "medium",
        max_resolution: Optional[Tuple[int, int]] = None,
        preserve_aspect_ratio: bool = True,
        include_audio: bool = True,
        audio_bitrate: str = "128k"
    ):
        """
        Initialize the video converter.
        
        Args:
            output_format: Target format (mp4, webm)
            codec: Video codec (h264, h265, vp9, av1). Auto-selected if None.
            crf: Constant Rate Factor for quality (lower = better, 18-28 typical)
            preset: Encoding preset (ultrafast, fast, medium, slow, veryslow)
            max_resolution: Optional max dimensions (width, height)
            preserve_aspect_ratio: Keep aspect ratio when resizing
            include_audio: Whether to include audio track
            audio_bitrate: Audio bitrate (e.g., "128k", "192k")
        """
        self._verify_ffmpeg()
        
        self.output_format = output_format
        self.codec = codec or self._default_codec_for_format(output_format)
        self.crf = max(0, min(51, crf))
        self.preset = preset
        self.max_resolution = max_resolution
        self.preserve_aspect_ratio = preserve_aspect_ratio
        self.include_audio = include_audio
        self.audio_bitrate = audio_bitrate
    
    @staticmethod
    def _verify_ffmpeg() -> None:
        """Verify FFmpeg is available on the system."""
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            raise FFmpegNotFoundError(
                "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.\n"
                "Download from: https://ffmpeg.org/download.html"
            )
    
    @staticmethod
    def _default_codec_for_format(fmt: VideoFormat) -> VideoCodec:
        """Get the default codec for a format."""
        return "h264" if fmt == "mp4" else "vp9"
    
    @staticmethod
    def is_ffmpeg_available() -> bool:
        """Check if FFmpeg is available on the system."""
        return shutil.which("ffmpeg") is not None
    
    @staticmethod
    def get_ffmpeg_path() -> Optional[str]:
        """Get the path to FFmpeg binary."""
        return shutil.which("ffmpeg")
    
    def convert_video(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[ConversionProgress], None]] = None
    ) -> Path:
        """
        Convert a single video file.
        
        Args:
            input_path: Source video path
            output_path: Destination path (auto-generated if not provided)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to the converted video
        """
        input_path = Path(input_path)
        
        if input_path.suffix.lower() not in self.SUPPORTED_INPUT:
            raise ValueError(f"Unsupported input format: {input_path.suffix}")
        
        # Get video info for scaling calculations
        video_info = self.get_video_info(input_path)
        
        # Generate output path
        if output_path is None:
            output_path = input_path.with_suffix(f'.{self.output_format}')
        else:
            output_path = Path(output_path)
        
        # Build FFmpeg command
        cmd = self._build_ffmpeg_command(input_path, output_path, video_info)
        
        # Run conversion
        self._run_ffmpeg(cmd, video_info.duration, progress_callback, output_path)
        
        return output_path
    
    def _build_ffmpeg_command(
        self,
        input_path: Path,
        output_path: Path,
        video_info: VideoInfo
    ) -> list:
        """Build the FFmpeg command with all options."""
        cmd = ["ffmpeg", "-y", "-i", str(input_path)]
        
        # Resolution scaling - MUST come before codec settings
        # Filters need to process the input stream before encoding
        if self.max_resolution:
            scale_filter = self._get_scale_filter(video_info)
            if scale_filter:
                cmd.extend(["-vf", scale_filter])
        
        # Video codec settings (after filters)
        if self.codec == "h264":
            cmd.extend(["-c:v", "libx264"])
            cmd.extend(["-preset", self.preset])
            cmd.extend(["-crf", str(self.crf)])
            # Web optimization - allows video to start playing before fully downloaded
            cmd.extend(["-movflags", "+faststart"])
            # Pixel format for maximum compatibility
            cmd.extend(["-pix_fmt", "yuv420p"])
        elif self.codec == "h265":
            cmd.extend(["-c:v", "libx265"])
            cmd.extend(["-preset", self.preset])
            cmd.extend(["-crf", str(self.crf)])
            cmd.extend(["-movflags", "+faststart"])
            cmd.extend(["-tag:v", "hvc1"])  # Apple compatibility
        elif self.codec == "vp9":
            cmd.extend(["-c:v", "libvpx-vp9"])
            cmd.extend(["-crf", str(self.crf)])
            cmd.extend(["-b:v", "0"])  # Use CRF mode
            cmd.extend(["-deadline", "good"])
            # VP9 needs pixel format when scaling - use yuv420p for compatibility
            cmd.extend(["-pix_fmt", "yuv420p"])
        elif self.codec == "av1":
            cmd.extend(["-c:v", "libaom-av1"])
            cmd.extend(["-crf", str(self.crf)])
            cmd.extend(["-b:v", "0"])
            cmd.extend(["-cpu-used", "4"])
            # AV1 also benefits from explicit pixel format
            cmd.extend(["-pix_fmt", "yuv420p"])
        
        # Audio settings
        if self.include_audio and video_info.has_audio:
            if self.output_format == "mp4":
                cmd.extend(["-c:a", "aac"])
            else:  # webm
                cmd.extend(["-c:a", "libopus"])
            cmd.extend(["-b:a", self.audio_bitrate])
        else:
            cmd.extend(["-an"])  # No audio
        
        cmd.append(str(output_path))
        return cmd
    
    def _get_scale_filter(self, video_info: VideoInfo) -> Optional[str]:
        """Generate FFmpeg scale filter string."""
        if not self.max_resolution:
            return None
        
        max_w, max_h = self.max_resolution
        orig_w, orig_h = video_info.width, video_info.height
        
        # Validate input dimensions
        if orig_w <= 0 or orig_h <= 0:
            return None
        if max_w <= 0 or max_h <= 0:
            return None
        
        # Check if scaling is needed
        if orig_w <= max_w and orig_h <= max_h:
            return None
        
        if self.preserve_aspect_ratio:
            # Calculate target dimensions preserving aspect ratio
            # Scale down to fit within max dimensions
            orig_aspect = orig_w / orig_h
            max_aspect = max_w / max_h
            
            if orig_aspect > max_aspect:
                # Width is the limiting factor - scale to max width
                target_w = max_w
                target_h = int(max_w / orig_aspect)
            else:
                # Height is the limiting factor - scale to max height
                target_h = max_h
                target_w = int(max_h * orig_aspect)
            
            # Ensure dimensions are even (required for many codecs)
            target_w = target_w - (target_w % 2)
            target_h = target_h - (target_h % 2)
            
            # Validate calculated dimensions
            if target_w <= 0 or target_h <= 0:
                return None
            if target_w > 10000 or target_h > 10000:
                # Sanity check - reject unreasonably large dimensions
                return None
            
            # Use simple scale filter with calculated dimensions
            return f"scale={target_w}:{target_h}"
        else:
            # Scale to exact dimensions, ensure even
            even_w = max_w - (max_w % 2)
            even_h = max_h - (max_h % 2)
            
            # Validate dimensions
            if even_w <= 0 or even_h <= 0:
                return None
            if even_w > 10000 or even_h > 10000:
                return None
            
            return f"scale={even_w}:{even_h}"
    
    def _run_ffmpeg(
        self,
        cmd: list,
        duration: float,
        progress_callback: Optional[Callable[[ConversionProgress], None]] = None,
        output_path: Optional[Path] = None
    ) -> None:
        """Run FFmpeg command with optional progress tracking."""
        # Add progress output
        cmd_with_progress = cmd.copy()
        cmd_with_progress.insert(1, "-progress")
        cmd_with_progress.insert(2, "pipe:1")
        cmd_with_progress.insert(3, "-stats_period")
        cmd_with_progress.insert(4, "0.5")
        
        # Prepare subprocess creation flags for Windows
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        process = subprocess.Popen(
            cmd_with_progress,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            creationflags=creation_flags
        )
        
        current_time = 0.0
        speed = 1.0
        stderr_lines = []
        stderr_read_complete = threading.Event()
        
        def read_stderr():
            """Read stderr in a separate thread to avoid blocking."""
            try:
                for line in process.stderr:
                    stderr_lines.append(line)
            except Exception:
                pass
            finally:
                stderr_read_complete.set()
        
        # Start reading stderr in background thread
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        try:
            # Read progress from stdout
            for line in process.stdout:
                line = line.strip()
                if line.startswith("out_time_ms="):
                    try:
                        time_ms = int(line.split("=")[1])
                        current_time = time_ms / 1_000_000
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("speed="):
                    try:
                        speed_str = line.split("=")[1].rstrip("x")
                        if speed_str and speed_str != "N/A":
                            speed = float(speed_str)
                    except (ValueError, IndexError):
                        pass
                
                if progress_callback and duration > 0:
                    percent = min(100, (current_time / duration) * 100)
                    remaining = (duration - current_time) / speed if speed > 0 else 0
                    progress = ConversionProgress(
                        current_time=current_time,
                        total_duration=duration,
                        percent=percent,
                        speed=speed,
                        eta_seconds=remaining
                    )
                    progress_callback(progress)
            
            # Wait for process to complete
            process.wait()
            
            # Wait for stderr reading to complete
            stderr_read_complete.wait(timeout=1.0)
            stderr_output = "".join(stderr_lines)
            
            if process.returncode != 0:
                # On Windows, return codes can be large unsigned integers
                # Convert to signed for better error messages
                return_code = process.returncode
                if platform.system() == "Windows" and return_code > 2147483647:
                    return_code = return_code - 4294967296  # Convert unsigned to signed
                
                error_msg = f"FFmpeg failed with code {return_code}"
                
                if stderr_output:
                    # Extract relevant error from stderr
                    error_lines = [line.strip() for line in stderr_output.strip().split('\n') if line.strip()]
                    # Look for error messages (usually contain "error", "failed", or start with capital letters)
                    error_parts = []
                    for line in reversed(error_lines[-10:]):  # Check last 10 lines
                        if any(keyword in line.lower() for keyword in ['error', 'failed', 'invalid', 'cannot', 'unable']):
                            error_parts.append(line)
                            if len(error_parts) >= 2:  # Get up to 2 error lines
                                break
                    
                    if error_parts:
                        error_msg += f": {'; '.join(reversed(error_parts))}"
                    else:
                        # Fallback: show last line if no clear error found
                        if error_lines:
                            error_msg += f": {error_lines[-1][:200]}"
                
                raise VideoConversionError(error_msg)
            
            # Verify output file exists and has content
            if output_path and output_path.exists():
                file_size = output_path.stat().st_size
                if file_size == 0:
                    raise VideoConversionError(
                        f"FFmpeg produced empty output file. "
                        f"Check FFmpeg installation and codec support. "
                        f"Stderr: {stderr_output[-500:] if stderr_output else 'No error output'}"
                    )
            elif output_path:
                raise VideoConversionError(
                    f"FFmpeg did not create output file: {output_path}. "
                    f"Stderr: {stderr_output[-500:] if stderr_output else 'No error output'}"
                )
                
        except VideoConversionError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            process.kill()
            stderr_output = "".join(stderr_lines)
            error_msg = f"Video conversion failed: {e}"
            if stderr_output:
                error_msg += f"\nFFmpeg stderr: {stderr_output[-500:]}"
            raise VideoConversionError(error_msg)
    
    def extract_thumbnail(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        time_offset: float = 1.0,
        size: Optional[Tuple[int, int]] = None
    ) -> Path:
        """
        Extract a thumbnail/poster image from the video.
        
        Args:
            input_path: Source video path
            output_path: Destination path for thumbnail (default: {input}-poster.webp)
            time_offset: Time in seconds to extract frame from
            size: Optional thumbnail size (width, height)
            
        Returns:
            Path to the extracted thumbnail
        """
        input_path = Path(input_path)
        
        if output_path is None:
            output_path = input_path.with_name(f"{input_path.stem}-poster.webp")
        else:
            output_path = Path(output_path)
        
        # Build FFmpeg command for thumbnail extraction
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(time_offset),
            "-i", str(input_path),
            "-vframes", "1",
            "-q:v", "2",  # High quality
        ]
        
        # Add scaling if size specified
        if size:
            cmd.extend(["-vf", f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=decrease"])
        
        cmd.append(str(output_path))
        
        # Prepare subprocess creation flags for Windows
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=creation_flags
        )
        
        if result.returncode != 0:
            error_msg = f"Thumbnail extraction failed: {result.stderr[-200:] if result.stderr else 'Unknown error'}"
            raise VideoConversionError(error_msg)
        
        # Verify output file exists
        if not output_path.exists():
            raise VideoConversionError(f"Thumbnail extraction did not create output file: {output_path}")
        
        file_size = output_path.stat().st_size
        if file_size == 0:
            raise VideoConversionError(f"Thumbnail extraction produced empty file: {output_path}")
        
        return output_path
    
    def extract_multiple_thumbnails(
        self,
        input_path: Path,
        output_dir: Optional[Path] = None,
        count: int = 5,
        size: Optional[Tuple[int, int]] = None
    ) -> list[Path]:
        """
        Extract multiple thumbnails evenly distributed across the video.
        
        Args:
            input_path: Source video path
            output_dir: Directory for thumbnails (default: same as input)
            count: Number of thumbnails to extract
            size: Optional thumbnail size (width, height)
            
        Returns:
            List of paths to extracted thumbnails
        """
        input_path = Path(input_path)
        
        if output_dir is None:
            output_dir = input_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get video duration
        video_info = self.get_video_info(input_path)
        duration = video_info.duration
        
        # Calculate time offsets (avoid first and last 5%)
        start_offset = duration * 0.05
        end_offset = duration * 0.95
        interval = (end_offset - start_offset) / max(1, count - 1)
        
        thumbnails = []
        for i in range(count):
            time_offset = start_offset + (interval * i)
            output_path = output_dir / f"{input_path.stem}-thumb-{i+1:02d}.webp"
            
            try:
                self.extract_thumbnail(input_path, output_path, time_offset, size)
                thumbnails.append(output_path)
            except VideoConversionError:
                continue  # Skip failed extractions
        
        return thumbnails
    
    @staticmethod
    def get_video_info(path: Path) -> VideoInfo:
        """
        Get detailed information about a video file.
        
        Args:
            path: Video file path
            
        Returns:
            VideoInfo dataclass with video metadata
        """
        path = Path(path)
        
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path)
        ]
        
        # Prepare subprocess creation flags for Windows
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=creation_flags
        )
        
        if result.returncode != 0:
            error_msg = f"Could not read video info: {result.stderr[-200:] if result.stderr else 'Unknown error'}"
            raise VideoConversionError(error_msg)
        
        data = json.loads(result.stdout)
        
        # Find video stream
        video_stream = None
        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video" and video_stream is None:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and audio_stream is None:
                audio_stream = stream
        
        if video_stream is None:
            raise VideoConversionError("No video stream found in file")
        
        format_info = data.get("format", {})
        
        # Parse FPS (can be in format "30/1" or "29.97")
        fps_str = video_stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(fps_str)
        
        return VideoInfo(
            filename=path.name,
            format=format_info.get("format_name", "unknown"),
            codec=video_stream.get("codec_name", "unknown"),
            width=int(video_stream.get("width", 0)),
            height=int(video_stream.get("height", 0)),
            duration=float(format_info.get("duration", 0)),
            fps=fps,
            bitrate=int(format_info.get("bit_rate", 0)),
            size_bytes=path.stat().st_size,
            has_audio=audio_stream is not None,
            audio_codec=audio_stream.get("codec_name") if audio_stream else None
        )
    
    def estimate_output_size(self, input_path: Path, preset_name: str = "seo_optimal") -> int:
        """
        Estimate the output file size based on preset and input video.
        
        This is a rough estimate based on target bitrate and duration.
        
        Args:
            input_path: Source video path
            preset_name: Name of the resolution preset
            
        Returns:
            Estimated size in bytes
        """
        video_info = self.get_video_info(input_path)
        preset = RESOLUTION_PRESETS.get(preset_name, RESOLUTION_PRESETS["seo_optimal"])
        
        # Estimate bitrate based on resolution and CRF
        # These are rough estimates for H.264
        crf = preset.get("crf", 23)
        resolution = preset.get("resolution")
        
        if resolution:
            target_pixels = resolution[0] * resolution[1]
        else:
            target_pixels = video_info.width * video_info.height
        
        # Base bitrate estimation (pixels * factor adjusted by CRF)
        # CRF 23 is roughly 2-4 Mbps for 1080p
        crf_factor = 2.0 ** ((23 - crf) / 6)  # Every 6 CRF = ~2x bitrate
        base_bitrate = (target_pixels / (1920 * 1080)) * 3_000_000 * crf_factor  # 3 Mbps base for 1080p
        
        # Add audio bitrate
        audio_bitrate = 128_000 if self.include_audio else 0
        
        total_bitrate = base_bitrate + audio_bitrate
        estimated_size = int((total_bitrate / 8) * video_info.duration)
        
        return estimated_size
    
    @classmethod
    def from_preset(cls, preset_name: str, output_format: VideoFormat = "mp4") -> "VideoConverter":
        """
        Create a VideoConverter from a preset name.
        
        Args:
            preset_name: Name of the preset (seo_optimal, high_quality, etc.)
            output_format: Target format
            
        Returns:
            Configured VideoConverter instance
        """
        preset = RESOLUTION_PRESETS.get(preset_name)
        if preset is None:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(RESOLUTION_PRESETS.keys())}")
        
        return cls(
            output_format=output_format,
            crf=preset.get("crf", 23),
            preset=preset.get("preset", "medium"),
            max_resolution=preset.get("resolution"),
        )

