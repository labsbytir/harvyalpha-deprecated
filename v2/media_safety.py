"""Universal local media safety scanning for collected image files."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
NSFW_CLASSES = {
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
}
_DETECTOR: Any = None


def nsfw_enabled() -> bool:
    """Scanning is on by default; set HARVY_NSFW_SCAN=false to disable it."""
    return os.environ.get("HARVY_NSFW_SCAN", "true").lower() not in {"0", "false", "no", "off"}


def get_detector() -> Tuple[Any, Optional[str]]:
    global _DETECTOR
    if _DETECTOR is not None:
        return _DETECTOR, None
    try:
        from nudenet import NudeDetector
    except ImportError:
        return None, "nudenet not installed"
    try:
        _DETECTOR = NudeDetector()
        return _DETECTOR, None
    except Exception as error:
        return None, str(error)


def scan_image_file(path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Return a fail-closed safety record for one image, without image bytes."""
    if not nsfw_enabled():
        return None
    detector, error = get_detector()
    if detector is None:
        return {"enabled": True, "available": False, "error": error,
                "flagged": True, "fail_closed": True}
    try:
        detections = detector.detect(str(path)) or []
        exposed = [item for item in detections if item.get("class") in NSFW_CLASSES]
        top = max((float(item.get("score", 0.0)) for item in exposed), default=0.0)
        return {"enabled": True, "available": True,
                "nsfw_score": round(top, 3), "flagged": bool(exposed),
                "exposed_detections": len(exposed),
                "total_detections": len(detections)}
    except Exception as error:
        return {"enabled": True, "available": False, "error": str(error),
                "flagged": True, "fail_closed": True}


def scan_media_tree(root: Union[str, Path]) -> Dict[str, Any]:
    """Scan every supported image below ``root`` and return path-safe records."""
    root = Path(root).resolve()
    files = sorted(path for path in root.rglob("*")
                   if path.is_file() and not path.is_symlink()
                   and path.suffix.lower() in IMAGE_SUFFIXES)
    records = []
    for path in files:
        record = scan_image_file(path)
        if record is not None:
            records.append({"path": path.relative_to(root).as_posix(), **record})
    return {"enabled": nsfw_enabled(), "scanned": len(records), "files": records}
