"""
Tests for video converter module.
"""

import unittest
import tempfile
import sys
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import conditionally to handle missing FFmpeg
try:
    from src.core.video_converter import (
        VideoConverter,
        VideoInfo,
        ConversionProgress,
        RESOLUTION_PRESETS,
        FFmpegNotFoundError,
        VideoConversionError,
    )
    VIDEO_CONVERTER_AVAILABLE = True
except ImportError:
    VIDEO_CONVERTER_AVAILABLE = False


@unittest.skipUnless(VIDEO_CONVERTER_AVAILABLE, "Video converter module not available")
class TestVideoConverterModule(unittest.TestCase):
    """Tests for VideoConverter module structure."""
    
    def test_resolution_presets_exist(self):
        """Test that resolution presets are defined."""
        self.assertIsInstance(RESOLUTION_PRESETS, dict)
        self.assertIn("seo_optimal", RESOLUTION_PRESETS)
        self.assertIn("high_quality", RESOLUTION_PRESETS)
        self.assertIn("fast_loading", RESOLUTION_PRESETS)
        self.assertIn("original", RESOLUTION_PRESETS)
    
    def test_resolution_preset_structure(self):
        """Test that each preset has required fields."""
        required_fields = ["name_ua", "name_en", "resolution", "crf", "description_ua", "description_en"]
        
        for preset_name, preset in RESOLUTION_PRESETS.items():
            for field in required_fields:
                self.assertIn(field, preset, f"Preset {preset_name} missing field {field}")
    
    def test_seo_optimal_preset_values(self):
        """Test SEO optimal preset has correct values."""
        preset = RESOLUTION_PRESETS["seo_optimal"]
        self.assertEqual(preset["resolution"], (1280, 720))
        self.assertEqual(preset["crf"], 23)
    
    def test_high_quality_preset_values(self):
        """Test high quality preset has correct values."""
        preset = RESOLUTION_PRESETS["high_quality"]
        self.assertEqual(preset["resolution"], (1920, 1080))
        self.assertEqual(preset["crf"], 20)
    
    def test_fast_loading_preset_values(self):
        """Test fast loading preset has correct values."""
        preset = RESOLUTION_PRESETS["fast_loading"]
        self.assertEqual(preset["resolution"], (854, 480))
        self.assertEqual(preset["crf"], 28)


@unittest.skipUnless(VIDEO_CONVERTER_AVAILABLE, "Video converter module not available")
class TestVideoInfo(unittest.TestCase):
    """Tests for VideoInfo dataclass."""
    
    def test_video_info_creation(self):
        """Test creating VideoInfo instance."""
        info = VideoInfo(
            filename="test.mp4",
            format="mp4",
            codec="h264",
            width=1920,
            height=1080,
            duration=60.0,
            fps=30.0,
            bitrate=5000000,
            size_bytes=37500000,
            has_audio=True,
            audio_codec="aac"
        )
        
        self.assertEqual(info.filename, "test.mp4")
        self.assertEqual(info.width, 1920)
        self.assertEqual(info.height, 1080)
        self.assertEqual(info.duration, 60.0)
        self.assertTrue(info.has_audio)


@unittest.skipUnless(VIDEO_CONVERTER_AVAILABLE, "Video converter module not available")
class TestConversionProgress(unittest.TestCase):
    """Tests for ConversionProgress dataclass."""
    
    def test_progress_creation(self):
        """Test creating ConversionProgress instance."""
        progress = ConversionProgress(
            current_time=30.0,
            total_duration=60.0,
            percent=50.0,
            speed=2.0,
            eta_seconds=15.0
        )
        
        self.assertEqual(progress.current_time, 30.0)
        self.assertEqual(progress.percent, 50.0)
        self.assertEqual(progress.speed, 2.0)


@unittest.skipUnless(VIDEO_CONVERTER_AVAILABLE, "Video converter module not available")
class TestVideoConverterInit(unittest.TestCase):
    """Tests for VideoConverter initialization (mocked FFmpeg)."""
    
    @patch('src.core.video_converter.shutil.which')
    def test_ffmpeg_not_found_raises(self, mock_which):
        """Test that missing FFmpeg raises FFmpegNotFoundError."""
        mock_which.return_value = None
        
        with self.assertRaises(FFmpegNotFoundError):
            VideoConverter()
    
    @patch('src.core.video_converter.shutil.which')
    def test_is_ffmpeg_available_false(self, mock_which):
        """Test is_ffmpeg_available returns False when FFmpeg missing."""
        mock_which.return_value = None
        self.assertFalse(VideoConverter.is_ffmpeg_available())
    
    @patch('src.core.video_converter.shutil.which')
    def test_is_ffmpeg_available_true(self, mock_which):
        """Test is_ffmpeg_available returns True when FFmpeg present."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        self.assertTrue(VideoConverter.is_ffmpeg_available())
    
    @patch('src.core.video_converter.shutil.which')
    def test_converter_initialization(self, mock_which):
        """Test converter initializes with correct settings."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        converter = VideoConverter(
            output_format="webm",
            codec="vp9",
            crf=25,
            preset="slow",
            max_resolution=(1280, 720)
        )
        
        self.assertEqual(converter.output_format, "webm")
        self.assertEqual(converter.codec, "vp9")
        self.assertEqual(converter.crf, 25)
        self.assertEqual(converter.preset, "slow")
        self.assertEqual(converter.max_resolution, (1280, 720))
    
    @patch('src.core.video_converter.shutil.which')
    def test_default_codec_selection(self, mock_which):
        """Test default codec is selected based on format."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        # MP4 should default to h264
        mp4_converter = VideoConverter(output_format="mp4")
        self.assertEqual(mp4_converter.codec, "h264")
        
        # WebM should default to vp9
        webm_converter = VideoConverter(output_format="webm")
        self.assertEqual(webm_converter.codec, "vp9")
    
    @patch('src.core.video_converter.shutil.which')
    def test_crf_clamping(self, mock_which):
        """Test that CRF is clamped to valid range."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        converter = VideoConverter(crf=100)
        self.assertEqual(converter.crf, 51)
        
        converter = VideoConverter(crf=-10)
        self.assertEqual(converter.crf, 0)


@unittest.skipUnless(VIDEO_CONVERTER_AVAILABLE, "Video converter module not available")
class TestVideoConverterFromPreset(unittest.TestCase):
    """Tests for VideoConverter.from_preset factory method."""
    
    @patch('src.core.video_converter.shutil.which')
    def test_from_preset_seo_optimal(self, mock_which):
        """Test creating converter from SEO optimal preset."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        converter = VideoConverter.from_preset("seo_optimal")
        
        self.assertEqual(converter.max_resolution, (1280, 720))
        self.assertEqual(converter.crf, 23)
    
    @patch('src.core.video_converter.shutil.which')
    def test_from_preset_high_quality(self, mock_which):
        """Test creating converter from high quality preset."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        converter = VideoConverter.from_preset("high_quality")
        
        self.assertEqual(converter.max_resolution, (1920, 1080))
        self.assertEqual(converter.crf, 20)
    
    @patch('src.core.video_converter.shutil.which')
    def test_from_preset_invalid_raises(self, mock_which):
        """Test that invalid preset name raises ValueError."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        with self.assertRaises(ValueError):
            VideoConverter.from_preset("invalid_preset")
    
    @patch('src.core.video_converter.shutil.which')
    def test_from_preset_with_format(self, mock_which):
        """Test creating converter from preset with custom format."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        converter = VideoConverter.from_preset("seo_optimal", output_format="webm")
        
        self.assertEqual(converter.output_format, "webm")
        self.assertEqual(converter.codec, "vp9")  # Default for webm


@unittest.skipUnless(VIDEO_CONVERTER_AVAILABLE, "Video converter module not available")
class TestVideoConverterSupportedFormats(unittest.TestCase):
    """Tests for supported input/output formats."""
    
    def test_supported_input_formats(self):
        """Test that common video formats are supported for input."""
        expected_formats = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
        self.assertTrue(expected_formats.issubset(VideoConverter.SUPPORTED_INPUT))
    
    def test_supported_output_formats(self):
        """Test that MP4 and WebM are supported for output."""
        self.assertIn('mp4', VideoConverter.SUPPORTED_OUTPUT)
        self.assertIn('webm', VideoConverter.SUPPORTED_OUTPUT)


@unittest.skipUnless(VIDEO_CONVERTER_AVAILABLE, "Video converter module not available")
class TestVideoConverterEstimateSize(unittest.TestCase):
    """Tests for output size estimation."""
    
    @patch('src.core.video_converter.shutil.which')
    @patch.object(VideoConverter, 'get_video_info')
    def test_estimate_output_size(self, mock_get_info, mock_which):
        """Test output size estimation."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        
        mock_get_info.return_value = VideoInfo(
            filename="test.mp4",
            format="mp4",
            codec="h264",
            width=1920,
            height=1080,
            duration=60.0,
            fps=30.0,
            bitrate=5000000,
            size_bytes=37500000,
            has_audio=True
        )
        
        converter = VideoConverter()
        estimated = converter.estimate_output_size(Path("test.mp4"), "seo_optimal")
        
        # Should return a positive integer
        self.assertIsInstance(estimated, int)
        self.assertGreater(estimated, 0)


@unittest.skipUnless(
    VIDEO_CONVERTER_AVAILABLE and shutil.which("ffmpeg") is not None,
    "FFmpeg not available for integration tests"
)
class TestVideoConverterIntegration(unittest.TestCase):
    """Integration tests that require actual FFmpeg."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.converter = VideoConverter(output_format="mp4", crf=28)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_ffmpeg_path(self):
        """Test getting FFmpeg path."""
        path = VideoConverter.get_ffmpeg_path()
        self.assertIsNotNone(path)
        self.assertTrue(Path(path).exists())


if __name__ == "__main__":
    unittest.main()

