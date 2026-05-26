from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status


class MediaProcessingError(RuntimeError):
    pass


def extract_video_thumbnail_bytes(
    upload: UploadFile,
    *,
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
) -> bytes:
    if not upload.filename:
        raise MediaProcessingError("Video filename is missing.")

    input_path: str | None = None
    output_path: str | None = None
    upload.file.seek(0)

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload.filename).suffix or ".mp4") as input_file:
            input_path = input_file.name
            shutil.copyfileobj(upload.file, input_file)
        upload.file.seek(0)

        duration_result = subprocess.run(
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                input_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        duration = float((duration_result.stdout or "0").strip() or "0")
        capture_time = max(duration / 2, 0.1)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as output_file:
            output_path = output_file.name

        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-ss",
                f"{capture_time:.3f}",
                "-i",
                input_path,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                output_path,
            ],
            capture_output=True,
            check=True,
        )

        return Path(output_path).read_bytes()
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate a video thumbnail.",
        ) from exc
    finally:
        if input_path and os.path.exists(input_path):
            os.remove(input_path)
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
