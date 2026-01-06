"""
JSON exporter for WordPress-compatible image metadata.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ExportSettings:
    """Export settings/attributes used for generation."""
    category: str = ""
    product_type: str = ""
    species: str = ""
    thickness: str = ""
    grade: str = ""
    output_format: str = "webp"
    quality: int = 85


class WordPressExporter:
    """
    Exports image metadata in WordPress Media Library compatible format.
    """
    
    @staticmethod
    def export_to_json(
        images: List[Any],  # List of ImageItem
        output_folder: Path,
        settings: ExportSettings,
        filename: str = "export.json"
    ) -> Path:
        """
        Export all image metadata to a JSON file.
        
        Args:
            images: List of ImageItem objects with metadata
            output_folder: Folder to save JSON file
            settings: Export settings used
            filename: Output filename
            
        Returns:
            Path to the created JSON file
        """
        export_data = {
            "export_date": datetime.now().isoformat(),
            "generator": "WoodWay Image Converter v1.0",
            "total_images": len(images),
            "settings": {
                "category": settings.category,
                "type": settings.product_type,
                "species": settings.species,
                "thickness": settings.thickness,
                "grade": settings.grade,
                "output_format": settings.output_format,
                "quality": settings.quality,
            },
            "images": []
        }
        
        for item in images:
            if not item.metadata:
                continue
            
            image_data = {
                "index": item.index,
                "original_filename": item.path.name,
                "new_filename": item.metadata.filename,
                "source_path": str(item.path.absolute()),
                "output_path": str(item.output_path.absolute()) if item.output_path else "",
                "metadata": {
                    "ua": {
                        "alt_text": item.metadata.ua.get("alt_text", ""),
                        "title": item.metadata.ua.get("title", ""),
                        "description": item.metadata.ua.get("description", ""),
                    },
                    "en": {
                        "alt_text": item.metadata.en.get("alt_text", ""),
                        "title": item.metadata.en.get("title", ""),
                        "description": item.metadata.en.get("description", ""),
                    },
                    "ru": {
                        "alt_text": item.metadata.ru.get("alt_text", ""),
                        "title": item.metadata.ru.get("title", ""),
                        "description": item.metadata.ru.get("description", ""),
                    },
                },
                "wp_attachment": {
                    # WordPress attachment meta fields
                    "_wp_attachment_image_alt": item.metadata.ua.get("alt_text", ""),
                    "post_title": item.metadata.ua.get("title", "").replace(" | WoodWay Expert", ""),
                    "post_excerpt": item.metadata.ua.get("description", ""),
                    "post_content": "",
                    # Additional multilingual fields for WPML/Polylang
                    "_alt_text_ua": item.metadata.ua.get("alt_text", ""),
                    "_alt_text_en": item.metadata.en.get("alt_text", ""),
                    "_alt_text_ru": item.metadata.ru.get("alt_text", ""),
                    "_title_ua": item.metadata.ua.get("title", ""),
                    "_title_en": item.metadata.en.get("title", ""),
                    "_title_ru": item.metadata.ru.get("title", ""),
                    "_description_ua": item.metadata.ua.get("description", ""),
                    "_description_en": item.metadata.en.get("description", ""),
                    "_description_ru": item.metadata.ru.get("description", ""),
                },
            }
            
            export_data["images"].append(image_data)
        
        # Write JSON file
        output_path = output_folder / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    @staticmethod
    def export_csv(
        images: List[Any],
        output_folder: Path,
        filename: str = "export.csv"
    ) -> Path:
        """
        Export image metadata to CSV for spreadsheet import.
        
        Args:
            images: List of ImageItem objects
            output_folder: Output folder
            filename: Output filename
            
        Returns:
            Path to created CSV file
        """
        import csv
        
        output_path = output_folder / filename
        
        headers = [
            "index",
            "original_filename",
            "new_filename",
            "alt_text_ua",
            "alt_text_en",
            "alt_text_ru",
            "title_ua",
            "title_en",
            "title_ru",
            "description_ua",
            "description_en",
            "description_ru",
        ]
        
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for item in images:
                if not item.metadata:
                    continue
                
                row = [
                    item.index,
                    item.path.name,
                    item.metadata.filename,
                    item.metadata.ua.get("alt_text", ""),
                    item.metadata.en.get("alt_text", ""),
                    item.metadata.ru.get("alt_text", ""),
                    item.metadata.ua.get("title", ""),
                    item.metadata.en.get("title", ""),
                    item.metadata.ru.get("title", ""),
                    item.metadata.ua.get("description", ""),
                    item.metadata.en.get("description", ""),
                    item.metadata.ru.get("description", ""),
                ]
                writer.writerow(row)
        
        return output_path

