from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
FRONTEND_PUBLIC = ROOT / "frontend" / "public"
OFFICIAL_GUIDE_DIR = FRONTEND_PUBLIC / "official-guide"
CATEGORY_DIR = FRONTEND_PUBLIC / "categories"
DATA_DIR = ROOT / "frontend" / "src" / "data"

PRIMARY_DOC = RESOURCE_DIR / "FZU_Campus_Architecture.docx - 福州大学校园建筑Word文档.docx"

PRIMARY_TITLES = [
    "Fuzhou University Main Gate",
    "Fuzhou University Library",
    "Jinjiang Building",
    "Fuyou Pavilion",
    "Honghui Sports and Culture Complex",
    "FZU Campus Lake View",
]

OFFICIAL_GUIDE_PLAN = [
    {
        "id": "main-gate",
        "name": "Fuzhou University Main Gate",
        "image_source": RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "gate_2.jpg",
        "image_name": "main-gate.jpg",
        "image_alt": "The stone monument and entry landscape at Fuzhou University Main Gate.",
        "atmosphere": "A ceremonial threshold where the university introduces itself through stone, sky, and mountain distance.",
    },
    {
        "id": "library",
        "name": "Fuzhou University Library",
        "image_source": RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "library_night.jpg",
        "image_name": "library.jpg",
        "image_alt": "The Fuzhou University Library reflected in the water at dusk.",
        "atmosphere": "Formal, reflective, and quietly luminous, the library frames study as both architecture and ritual.",
    },
    {
        "id": "jinjiang-building",
        "name": "Jinjiang Building",
        "image_source": RESOURCE_DIR / "background2.jpeg",
        "image_name": "jinjiang-building.jpg",
        "image_alt": "Jinjiang Building rising above trees and water under a clear sky.",
        "atmosphere": "A vertical landmark that gives the campus skyline a crisp contemporary silhouette.",
    },
    {
        "id": "fuyou-pavilion",
        "name": "Fuyou Pavilion",
        "image_source": RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "fuyou_day.jpg",
        "image_name": "fuyou-pavilion.jpg",
        "image_alt": "Fuyou Pavilion surrounded by lotus leaves in daylight.",
        "atmosphere": "The pavilion softens the campus rhythm with water, lotus textures, and a traditional roofline.",
    },
    {
        "id": "honghui-complex",
        "name": "Honghui Sports and Culture Complex",
        "image_source": RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "building_5.jpg",
        "image_name": "honghui-complex.jpg",
        "image_alt": "The geometric facade of the Honghui Sports and Culture Complex.",
        "atmosphere": "Angular and public-facing, the complex brings ceremony, performance, and movement into one volume.",
    },
    {
        "id": "campus-lake-view",
        "name": "FZU Campus Lake View",
        "image_source": RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "campus_lake1.jpg",
        "image_name": "campus-lake-view.jpg",
        "image_alt": "Campus architecture reflected across the still surface of the lake.",
        "atmosphere": "Calm water and mirrored forms let the campus read as a single, composed landscape.",
    },
]

HERO_SOURCE = RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "library_night.jpg"
HOME_HERO_SOURCE = RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "campus_lake1.jpg"

CATEGORY_IMAGE_SOURCES = {
    "campus-landmark.jpg": RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "gate_2.jpg",
    "study-space.jpg": RESOURCE_DIR / "background.jpeg",
    "student-life.jpg": RESOURCE_DIR / "background2.jpeg",
    "sports-and-leisure.jpg": RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "building_5.jpg",
    "digital-memory.jpg": RESOURCE_DIR / "FZU_Images_Collection.zip - 福州大学图片合集压缩包" / "fzu_images" / "campus_fountain.jpg",
}

FOOD_VIDEO_SOURCE = RESOURCE_DIR / "Food_ Diary.mp4"


def extract_docx_lines(path: Path) -> list[str]:
    with ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
    import re

    texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", document_xml)
    lines: list[str] = []
    previous: str | None = None
    for text in texts:
        value = text.strip()
        if not value or value == previous:
            continue
        previous = value
        lines.append(value)
    return lines


def parse_primary_descriptions(lines: list[str]) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    stop_markers = set(PRIMARY_TITLES) | {"About Fuzhou University"}
    for title in PRIMARY_TITLES:
        try:
            start_index = lines.index(title)
        except ValueError as exc:
            raise RuntimeError(f"Could not find {title!r} in {PRIMARY_DOC.name}") from exc

        fragments: list[str] = []
        for value in lines[start_index + 1 :]:
            if value in stop_markers:
                break
            if value.startswith(tuple(f"{index}." for index in range(1, 10))):
                continue
            fragments.append(value)
        description = " ".join(fragments).strip()
        description = description.replace("m²", "square-meter")
        description = description.replace("m虏", "square-meter")
        descriptions[title] = description
    return descriptions


def ensure_directories() -> None:
    OFFICIAL_GUIDE_DIR.mkdir(parents=True, exist_ok=True)
    CATEGORY_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def extract_video_frame(source: Path, destination: Path, capture_seconds: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(capture_seconds),
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(destination),
        ],
        check=True,
        capture_output=True,
    )


def build_official_guide() -> None:
    ensure_directories()
    primary_lines = extract_docx_lines(PRIMARY_DOC)
    primary_descriptions = parse_primary_descriptions(primary_lines)

    copy_file(HERO_SOURCE, OFFICIAL_GUIDE_DIR / "hero-library-night.jpg")
    copy_file(HOME_HERO_SOURCE, CATEGORY_DIR / "home-hero.jpg")

    for image_name, source in CATEGORY_IMAGE_SOURCES.items():
        copy_file(source, CATEGORY_DIR / image_name)
    extract_video_frame(FOOD_VIDEO_SOURCE, CATEGORY_DIR / "food-and-cafe.jpg", capture_seconds=40)

    items = []
    for sort_order, item in enumerate(OFFICIAL_GUIDE_PLAN, start=1):
        copy_file(item["image_source"], OFFICIAL_GUIDE_DIR / item["image_name"])
        items.append(
            {
                "id": item["id"],
                "name": item["name"],
                "description": primary_descriptions[item["name"]],
                "atmosphere": item["atmosphere"],
                "imageUrl": f"/official-guide/{item['image_name']}",
                "imageAlt": item["image_alt"],
                "sortOrder": sort_order,
            }
        )

    output = {
        "hero": {
            "title": "Official FZU Introduction",
            "subtitle": "A photography-led introduction to campus architecture, study spaces, and waterside landmarks.",
            "imageUrl": "/official-guide/hero-library-night.jpg",
            "imageAlt": "The Fuzhou University Library reflected in the campus water at dusk.",
        },
        "items": items,
        "sourceDocs": [
            PRIMARY_DOC.name,
            "照片（图书馆，卧龙桥，旋转楼梯，东门）.docx",
        ],
    }

    with open(DATA_DIR / "officialGuide.json", "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build_official_guide()
    print("Built official guide assets and data.")
