#!/usr/bin/env python3
"""
Скрипт для очистки тестовых файлов
"""

import os
import sys
from pathlib import Path

def cleanup_test_files():
    """Удаление тестовых файлов"""
    test_files = [
        "test_image.jpg",
        "test_thumbnail_system.py",
        "test_thumbnail_generation.py",
        "THUMBNAIL_IMPLEMENTATION_ISSUES.md",
        "THUMBNAIL_SYSTEM_DOCUMENTATION.md",
        "cleanup_test_files.py"
    ]
    
    removed_count = 0
    error_count = 0
    
    print("Очистка тестовых файлов...")
    
    for file_name in test_files:
        file_path = Path(file_name)
        if file_path.exists():
            try:
                if file_path.is_file():
                    file_path.unlink()
                    print(f"✓ Удален файл: {file_name}")
                    removed_count += 1
                elif file_path.is_dir():
                    import shutil
                    shutil.rmtree(file_path)
                    print(f"✓ Удалена директория: {file_name}")
                    removed_count += 1
            except Exception as e:
                print(f"✗ Ошибка при удалении {file_name}: {e}")
                error_count += 1
        else:
            print(f"- Файл не найден: {file_name}")
    
    # Очистка директории thumbnails
    thumbnails_dir = Path("storage/content/thumbnails")
    if thumbnails_dir.exists() and thumbnails_dir.is_dir():
        try:
            for file_path in thumbnails_dir.iterdir():
                if file_path.is_file() and "test" in file_path.name.lower():
                    file_path.unlink()
                    print(f"✓ Удален тестовый файл превью: {file_path.name}")
                    removed_count += 1
        except Exception as e:
            print(f"✗ Ошибка при очистке директории thumbnails: {e}")
            error_count += 1
    else:
        print("- Директория thumbnails не найдена или недоступна")
    
    print(f"\nРезультаты очистки:")
    print(f"  Удалено файлов: {removed_count}")
    print(f"  Ошибок: {error_count}")
    
    return error_count == 0

if __name__ == "__main__":
    success = cleanup_test_files()
    sys.exit(0 if success else 1)