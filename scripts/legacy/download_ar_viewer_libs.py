#!/usr/bin/env python3
"""
Скачивает Three.js и MindAR в static/js для AR viewer.
После запуска просмотр AR работает без CDN (удобно при туннеле/мобильном).
"""
from pathlib import Path
import urllib.request
import sys

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "static" / "js"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# MindAR 1.1.4 — глобальные (UMD) сборки, работают с <script> без type=module.
# 1.2.5 — только ESM, при обычном <script> не выполняются.
LIBS = [
    ("https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.min.js", "three.min.js"),
    ("https://cdn.jsdelivr.net/npm/mind-ar@1.1.4/dist/mindar-image.prod.js", "mindar-image.prod.js"),
    ("https://cdn.jsdelivr.net/npm/mind-ar@1.1.4/dist/mindar-image-three.prod.js", "mindar-image-three.prod.js"),
]


def main() -> int:
    for url, name in LIBS:
        path = OUT_DIR / name
        print(f"Downloading {name} ...", end=" ", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                path.write_bytes(r.read())
            print("OK")
        except Exception as e:
            print(f"FAIL: {e}")
            return 1
    print(f"Done. Files in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
