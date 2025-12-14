import os
import shutil
from pathlib import Path

def remove_file_or_dir(path):
    """Безопасное удаление файла или директории"""
    try:
        if os.path.isfile(path) or os.path.islink(path):
            os.unlink(path)
            print(f"Удален файл: {path}")
        elif os.path.isdir(path):
            shutil.rmtree(path)
            print(f"Удалена директория: {path}")
    except Exception as e:
        print(f"Ошибка при удалении {path}: {e}")

def main():
    base_dir = Path(__file__).parent
    
    # Файлы и директории для удаления
    to_remove = [
        # Celery файлы
        base_dir / "Dockerfile.celery-beat",
        base_dir / "Dockerfile.celery-worker",
        base_dir / "app" / "tasks",
        
        # Nginx
        base_dir / "nginx",
        
        # Временные и тестовые файлы
        base_dir / "temp_analytics.txt",
        base_dir / "temp_wizard.txt",
        
        # Дополнительные Docker Compose файлы
        base_dir / "docker-compose.override.yml",
        base_dir / "docker-compose.test.yml",
        
        # Вспомогательные скрипты
        base_dir / "cleanup_test_files.py",
        base_dir / "create_test_image.py",
        base_dir / "create_valid_image.py",
        base_dir / "final_verification.py",
        base_dir / "locustfile.py",
    ]
    
    # Удаляем тестовые файлы
    test_files = list(base_dir.glob("test_*.*"))
    test_py_files = [f for f in base_dir.glob("test_*.py") if str(f) != str(base_dir / "test_api.py")]
    
    to_remove.extend(test_files)
    to_remove.extend(test_py_files)
    
    print("Начинаем удаление ненужных файлов...\n")
    
    # Удаляем файлы и директории
    for item in to_remove:
        if item.exists():
            print(f"Удаление: {item}")
            remove_file_or_dir(item)
    
    print("\nОчистка завершена!")

if __name__ == "__main__":
    main()
