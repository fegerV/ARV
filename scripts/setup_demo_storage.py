#!/usr/bin/env python3
"""
Create storage/Demo/demo_1..demo_5 structure.

Put marker.jpg (portrait for AR) and video.mp4 in each demo_N/ folder.
The app fetches demo content from the server — files are not bundled in APK.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORAGE_DEMO = PROJECT_ROOT / "storage" / "Demo"


def main() -> None:
    for i in range(1, 6):
        demo_dir = STORAGE_DEMO / f"demo_{i}"
        demo_dir.mkdir(parents=True, exist_ok=True)
        marker = demo_dir / "marker.jpg"
        video = demo_dir / "video.mp4"
        status = []
        if marker.exists():
            status.append("marker✓")
        else:
            status.append("marker?")
        if video.exists():
            status.append("video✓")
        else:
            status.append("video?")
        print(f"  demo_{i}/: {' '.join(status)}")

    print(f"\nDemo storage: {STORAGE_DEMO}")
    print("Add marker.jpg and video.mp4 to each demo_N/ folder.")


if __name__ == "__main__":
    main()
