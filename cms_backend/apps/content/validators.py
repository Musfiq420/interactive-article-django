import re
from pathlib import Path

from django.core.exceptions import ValidationError


YOUTUBE_URL_RE = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]{11}([&?].*)?$"
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def validate_youtube_url(value: str) -> None:
    if value and not YOUTUBE_URL_RE.match(value):
        raise ValidationError("Enter a valid YouTube watch or share URL.")


def validate_file_extension(value, allowed_extensions: set[str], label: str) -> None:
    if not value:
        return
    suffix = Path(value.name).suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(ext.lstrip(".") for ext in allowed_extensions))
        raise ValidationError(f"{label} must use one of: {allowed}.")


def validate_interactive_payload(interactive_type: str, attrs: dict) -> None:
    requirements = {
        "image": ("image",),
        "audio": ("audio",),
        "video": ("video",),
        "youtube": ("youtube_url",),
        "text": ("description",),
    }
    allowed_fields = {
        "image": {"image", "description", "metadata"},
        "audio": {"audio", "description", "metadata"},
        "video": {"video", "description", "metadata"},
        "youtube": {"youtube_url", "description", "metadata"},
        "text": {"description", "metadata"},
    }

    if interactive_type not in requirements:
        raise ValidationError({"type": "Unsupported interactive type."})

    missing = [field for field in requirements[interactive_type] if not attrs.get(field)]
    if missing:
        raise ValidationError(
            {missing[0]: f"This field is required when type is '{interactive_type}'."}
        )

    invalid_fields = []
    media_fields = {"image", "audio", "video", "youtube_url"}
    for field in media_fields:
        if attrs.get(field) and field not in allowed_fields[interactive_type]:
            invalid_fields.append(field)

    if interactive_type != "text" and attrs.get("description") is None:
        attrs["description"] = ""

    if invalid_fields:
        errors = {
            field: f"This field is not allowed when type is '{interactive_type}'."
            for field in invalid_fields
        }
        raise ValidationError(errors)
