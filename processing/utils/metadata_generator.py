from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


class MetadataGeneratorError(Exception):
    pass


def escape_xml_text(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def generate_opf(media, output_path: str) -> str:
    package = ET.Element("package")
    package.set("version", "2.0")
    package.set("xmlns", "http://www.idpf.org/2007/opf")
    
    metadata = ET.SubElement(package, "metadata")
    metadata.set("xmlns:dc", "http://purl.org/dc/elements/1.1/")
    metadata.set("xmlns:opf", "http://www.idpf.org/2007/opf")
    
    title_elem = ET.SubElement(metadata, "{http://purl.org/dc/elements/1.1/}title")
    title_elem.text = media.title
    
    if media.language:
        language_elem = ET.SubElement(
            metadata, "{http://purl.org/dc/elements/1.1/}language"
        )
        language_elem.text = media.language
    
    if hasattr(media, "isbn") and media.isbn:
        identifier_elem = ET.SubElement(
            metadata, "{http://purl.org/dc/elements/1.1/}identifier"
        )
        identifier_elem.set(
            "{http://www.idpf.org/2007/opf}scheme", "ISBN"
        )
        identifier_elem.text = media.isbn
    elif hasattr(media, "isbn13") and media.isbn13:
        identifier_elem = ET.SubElement(
            metadata, "{http://purl.org/dc/elements/1.1/}identifier"
        )
        identifier_elem.set(
            "{http://www.idpf.org/2007/opf}scheme", "ISBN"
        )
        identifier_elem.text = media.isbn13
    
    if media.authors:
        for author in media.authors:
            creator_elem = ET.SubElement(
                metadata, "{http://purl.org/dc/elements/1.1/}creator"
            )
            creator_elem.set("{http://www.idpf.org/2007/opf}role", "aut")
            
            if ", " in author:
                parts = author.split(", ", 1)
                creator_elem.set(
                    "{http://www.idpf.org/2007/opf}file-as", author
                )
                creator_elem.text = f"{parts[1]} {parts[0]}"
            else:
                creator_elem.text = author
    
    if media.description:
        description_elem = ET.SubElement(
            metadata, "{http://purl.org/dc/elements/1.1/}description"
        )
        description_elem.text = escape_xml_text(media.description)
    
    if media.publication_date:
        date_elem = ET.SubElement(
            metadata, "{http://purl.org/dc/elements/1.1/}date"
        )
        if isinstance(media.publication_date, date):
            date_elem.text = media.publication_date.isoformat()
        else:
            date_elem.text = str(media.publication_date)
    
    if media.publisher:
        publisher_elem = ET.SubElement(
            metadata, "{http://purl.org/dc/elements/1.1/}publisher"
        )
        publisher_elem.text = media.publisher
    
    if media.genres:
        for genre in media.genres:
            subject_elem = ET.SubElement(
                metadata, "{http://purl.org/dc/elements/1.1/}subject"
            )
            subject_elem.text = genre
    
    guide = ET.SubElement(package, "guide")
    if media.cover_path:
        cover_filename = Path(media.cover_path).name
        reference_elem = ET.SubElement(guide, "reference")
        reference_elem.set("href", cover_filename)
        reference_elem.set("type", "cover")
        reference_elem.set("title", "Cover")
    
    tree = ET.ElementTree(package)
    try:
        ET.indent(tree, space="    ")
    except AttributeError:
        pass
    
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tree.write(
        output_path,
        encoding="UTF-8",
        xml_declaration=True,
    )
    
    logger.info(f"Generated OPF file: {output_path}")
    return output_path
