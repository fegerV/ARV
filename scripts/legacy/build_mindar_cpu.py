#!/usr/bin/env python3
"""
Скрипт: клонирование mind-ar-js, применение патча CPU для мобильных, сборка.

Патч добавляет в _startAR() переключение TensorFlow.js на бэкенд CPU до
addImageTargets/dummyRun, чтобы на мобильных не зависать на компиляции WebGL.

Требования: git, Node.js, npm. Результат сборки — в deps/mind-ar-js/dist/.
Текущий vite.config.prod.js собирает ES-модули; для подстановки в static/js
нужен либо IIFE-сборка (изменить конфиг), либо загрузка viewer через type="module".
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/hiukim/mind-ar-js.git"
BASE_DIR = Path(__file__).resolve().parent.parent
DEPS_DIR = BASE_DIR / "deps"
MINDAR_DIR = DEPS_DIR / "mind-ar-js"
THREE_JS_PATH = MINDAR_DIR / "src" / "image-target" / "three.js"
STATIC_JS = BASE_DIR / "static" / "js"

# Вставить после this.resize(); и перед const { dimensions: imageTargetDimensions }
PATCH_AFTER = "this.resize();"
PATCH_BEFORE = "const { dimensions: imageTargetDimensions } = await this.controller.addImageTargets"
PATCH_BLOCK = """
    const isMobile = /Mobile|Android|iP(hone|od)/.test(navigator.userAgent);
    if (isMobile) {
      try {
        await tf.setBackend('cpu');
        await tf.ready();
      } catch (e) { console.warn('MindAR TF CPU fallback:', e); }
    }

    """


def run(cmd: list[str], cwd: Path | None = None, shell: bool = False) -> None:
    """Run command; on failure raise and exit."""
    r = subprocess.run(
        " ".join(cmd) if shell else cmd,
        cwd=cwd or BASE_DIR,
        shell=shell,
    )
    if r.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(r.returncode)


def main() -> int:
    DEPS_DIR.mkdir(parents=True, exist_ok=True)

    if not MINDAR_DIR.exists():
        print("Cloning mind-ar-js...")
        run(["git", "clone", "--depth", "1", REPO_URL, str(MINDAR_DIR)])
    else:
        print("deps/mind-ar-js already exists; skipping clone.")

    if not THREE_JS_PATH.exists():
        print(f"File not found: {THREE_JS_PATH}", file=sys.stderr)
        return 1

    text = THREE_JS_PATH.read_text(encoding="utf-8")
    if PATCH_BLOCK.strip() in text:
        print("Patch already applied.")
    else:
        if PATCH_AFTER not in text or PATCH_BEFORE not in text:
            print("Could not find patch anchor (this.resize(); / addImageTargets).", file=sys.stderr)
            return 1
        pattern = re.escape(PATCH_AFTER) + r"\s*"
        replacement = PATCH_AFTER + "\n" + PATCH_BLOCK
        new_text, n = re.subn(pattern, replacement, text, count=1)
        if n != 1:
            print("Patch replacement failed.", file=sys.stderr)
            return 1
        THREE_JS_PATH.write_text(new_text, encoding="utf-8")
        print("Patch applied to src/image-target/three.js")

    pkg_path = MINDAR_DIR / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    deps = pkg.get("dependencies", {})
    if "canvas" in deps:
        pkg.setdefault("optionalDependencies", {})["canvas"] = deps.pop("canvas")
        pkg_path.write_text(json.dumps(pkg, indent=2), encoding="utf-8")
        print("Canvas moved to optionalDependencies (not needed for browser build).")

    print("Running npm install...")
    run(["npm", "install"], cwd=MINDAR_DIR, shell=True)
    print("Running npm run build...")
    run(["npm", "run", "build"], cwd=MINDAR_DIR, shell=True)

    dist = MINDAR_DIR / "dist"
    if not dist.exists():
        print("dist/ not found after build.", file=sys.stderr)
        return 1

    iife_image = dist / "mindar-image.iife.js"
    iife_three = dist / "mindar-image-three.iife.js"
    if not iife_image.exists() or not iife_three.exists():
        print("IIFE files not found. Check vite.config.prod.js imageIifeConfig.", file=sys.stderr)
        return 1

    STATIC_JS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(iife_image, STATIC_JS / "mindar-image.prod.js")
    shutil.copy2(iife_three, STATIC_JS / "mindar-image-three.prod.js")
    print(f"Copied IIFE build to {STATIC_JS / 'mindar-image.prod.js'} and mindar-image-three.prod.js")

    for f in dist.iterdir():
        if f.is_file():
            print(f"  {f.relative_to(MINDAR_DIR)}")
    print(f"\nBuild output: {dist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
