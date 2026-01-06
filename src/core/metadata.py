"""
Image metadata (EXIF/XMP) handling module.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json

import piexif
from PIL import Image


class MetadataHandler:
    """
    Handles reading and writing image metadata (EXIF).
    """
    
    @staticmethod
    def read_metadata(image_path: Path) -> Dict[str, Any]:
        """
        Read EXIF metadata from an image.
        
        Args:
            image_path: Path to the image
            
        Returns:
            Dictionary of metadata
        """
        image_path = Path(image_path)
        metadata = {}
        
        try:
            with Image.open(image_path) as img:
                if hasattr(img, '_getexif') and img._getexif():
                    exif_dict = piexif.load(img.info.get('exif', b''))
                    
                    # Extract relevant fields
                    if '0th' in exif_dict:
                        zeroth = exif_dict['0th']
                        if piexif.ImageIFD.ImageDescription in zeroth:
                            desc = zeroth[piexif.ImageIFD.ImageDescription]
                            metadata['description'] = desc.decode('utf-8') if isinstance(desc, bytes) else desc
                        if piexif.ImageIFD.XPTitle in zeroth:
                            title = zeroth[piexif.ImageIFD.XPTitle]
                            metadata['title'] = title.decode('utf-16le').rstrip('\x00') if isinstance(title, bytes) else title
                        if piexif.ImageIFD.XPComment in zeroth:
                            comment = zeroth[piexif.ImageIFD.XPComment]
                            metadata['comment'] = comment.decode('utf-16le').rstrip('\x00') if isinstance(comment, bytes) else comment
                        if piexif.ImageIFD.XPKeywords in zeroth:
                            keywords = zeroth[piexif.ImageIFD.XPKeywords]
                            metadata['keywords'] = keywords.decode('utf-16le').rstrip('\x00') if isinstance(keywords, bytes) else keywords
        except Exception:
            pass  # Return empty metadata if reading fails
        
        return metadata
    
    @staticmethod
    def write_metadata(
        image_path: Path,
        output_path: Optional[Path] = None,
        description: Optional[str] = None,
        title: Optional[str] = None,
        keywords: Optional[str] = None,
        comment: Optional[str] = None,
        custom_data: Optional[Dict[str, str]] = None,
    ) -> Path:
        """
        Write EXIF metadata to an image.
        
        Args:
            image_path: Source image path
            output_path: Destination path (optional, overwrites if not provided)
            description: Image description (alt text)
            title: Image title
            keywords: Keywords/tags
            comment: Additional comment
            custom_data: Custom JSON data to store in UserComment
            
        Returns:
            Path to the output image
        """
        image_path = Path(image_path)
        output_path = Path(output_path) if output_path else image_path
        
        with Image.open(image_path) as img:
            # Try to load existing EXIF or create new
            try:
                if 'exif' in img.info:
                    exif_dict = piexif.load(img.info['exif'])
                else:
                    exif_dict = {'0th': {}, '1st': {}, 'Exif': {}, 'GPS': {}, 'Interop': {}}
            except Exception:
                exif_dict = {'0th': {}, '1st': {}, 'Exif': {}, 'GPS': {}, 'Interop': {}}
            
            # Set metadata fields
            if description:
                exif_dict['0th'][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
            
            if title:
                # XPTitle uses UTF-16LE encoding
                exif_dict['0th'][piexif.ImageIFD.XPTitle] = title.encode('utf-16le')
            
            if keywords:
                exif_dict['0th'][piexif.ImageIFD.XPKeywords] = keywords.encode('utf-16le')
            
            if comment:
                exif_dict['0th'][piexif.ImageIFD.XPComment] = comment.encode('utf-16le')
            
            if custom_data:
                # Store custom data as JSON in UserComment
                json_str = json.dumps(custom_data, ensure_ascii=False)
                user_comment = b'UNICODE\x00' + json_str.encode('utf-8')
                exif_dict['Exif'][piexif.ExifIFD.UserComment] = user_comment
            
            # Add software tag
            exif_dict['0th'][piexif.ImageIFD.Software] = b'WoodWay Image Converter'
            
            # Convert to bytes
            exif_bytes = piexif.dump(exif_dict)
            
            # Save image with new EXIF
            # Need to handle format-specific saving
            img_format = img.format or 'JPEG'
            
            if img_format.upper() in ('JPEG', 'JPG'):
                img.save(output_path, 'JPEG', exif=exif_bytes, quality=95)
            elif img_format.upper() == 'PNG':
                # PNG doesn't support EXIF natively, save without
                img.save(output_path, 'PNG')
            elif img_format.upper() == 'WEBP':
                # WebP has limited EXIF support
                img.save(output_path, 'WEBP', exif=exif_bytes, quality=95)
            else:
                img.save(output_path, exif=exif_bytes)
        
        return output_path
    
    @staticmethod
    def write_seo_metadata(
        image_path: Path,
        output_path: Optional[Path] = None,
        filename: str = "",
        ua: Optional[Dict[str, str]] = None,
        en: Optional[Dict[str, str]] = None,
        ru: Optional[Dict[str, str]] = None,
    ) -> Path:
        """
        Write multi-language SEO metadata to an image.
        Uses primary language (UA) for standard fields and stores all languages in UserComment.
        
        Args:
            image_path: Source image path
            output_path: Destination path
            filename: New filename (for reference)
            ua: Ukrainian metadata
            en: English metadata
            ru: Russian metadata
            
        Returns:
            Path to the output image
        """
        ua = ua or {}
        en = en or {}
        ru = ru or {}
        
        # Use Ukrainian as primary for standard fields
        description = ua.get('alt_text', '') or en.get('alt_text', '')
        title = ua.get('title', '') or en.get('title', '')
        
        # Store all languages in custom data
        custom_data = {
            'filename': filename,
            'ua': ua,
            'en': en,
            'ru': ru,
        }
        
        return MetadataHandler.write_metadata(
            image_path=image_path,
            output_path=output_path,
            description=description,
            title=title,
            custom_data=custom_data,
        )
    
    @staticmethod
    def copy_metadata(source_path: Path, dest_path: Path) -> bool:
        """
        Copy EXIF metadata from one image to another.
        
        Args:
            source_path: Source image with metadata
            dest_path: Destination image to receive metadata
            
        Returns:
            True if successful
        """
        try:
            source_exif = piexif.load(str(source_path))
            piexif.insert(piexif.dump(source_exif), str(dest_path))
            return True
        except Exception:
            return False

