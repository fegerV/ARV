#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы системы генерации превью
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к приложению
sys.path.append(str(Path(__file__).parent))

from app.services.thumbnail_service import thumbnail_service


async def create_test_image():
    """Создание тестового изображения"""
    from PIL import Image
    import numpy as np
    
    # Создаем тестовое изображение 800x600 с градиентом
    width, height = 800, 600
    array = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Создаем цветной градиент
    for y in range(height):
        for x in range(width):
            array[y, x] = [
                int(255 * x / width),      # Красный канал
                int(255 * y / height),     # Зеленый канал
                int(255 * (x + y) / (width + height))  # Синий канал
            ]
    
    img = Image.fromarray(array)
    test_image_path = Path("test_image.jpg")
    img.save(test_image_path, quality=95)
    print(f"✓ Создано тестовое изображение: {test_image_path}")
    return str(test_image_path)


async def test_image_thumbnail_generation():
    """Тест генерации превью для изображения"""
    print("\n=== Тест генерации превью для изображения ===")
    
    # Создаем тестовое изображение
    test_image_path = await create_test_image()
    
    # Генерируем превью
    print("Генерируем превью...")
    result = await thumbnail_service.generate_image_thumbnail(
        image_path=test_image_path,
        output_dir="storage/content/thumbnails",
        thumbnail_name="test_image_thumb.jpg"
    )
    
    print(f"Результат: {result}")
    
    if result["status"] == "ready":
        print(f"✓ Превью успешно создано")
        print(f"  Путь к файлу: {result['thumbnail_path']}")
        print(f"  URL: {result['thumbnail_url']}")
        
        # Проверяем существование файла
        thumb_path = Path(result['thumbnail_path'])
        if thumb_path.exists():
            size = thumb_path.stat().st_size
            print(f"  Размер файла: {size} байт")
        else:
            print("✗ Файл превью не найден")
            return False
    else:
        print(f"✗ Ошибка генерации превью: {result.get('error')}")
        return False
    
    return True


async def test_video_thumbnail_generation():
    """Тест генерации превью для видео (имитация)"""
    print("\n=== Тест генерации превью для видео ===")
    print("Примечание: Для полноценного теста видео требуется реальный видеофайл")
    print("Тест демонстрирует только структуру вызова функции")
    
    # Создаем тестовое изображение как замену видеофайлу
    test_image_path = await create_test_image()
    
    # Имитируем вызов генерации превью для видео
    print("Имитируем генерацию превью для видео...")
    result = await thumbnail_service.generate_video_thumbnail(
        video_path=test_image_path,  # Используем изображение как замену видео
        output_dir="storage/content/thumbnails",
        thumbnail_name="test_video_thumb.jpg",
        time_position=1.0
    )
    
    print(f"Результат: {result}")
    
    if result["status"] == "ready":
        print(f"✓ Превью для видео успешно создано")
        print(f"  Путь к файлу: {result['thumbnail_path']}")
        print(f"  URL: {result['thumbnail_url']}")
    else:
        print(f"✗ Ошибка генерации превью для видео: {result.get('error')}")
        return False
    
    return True


async def test_thumbnail_validation():
    """Тест валидации превью"""
    print("\n=== Тест валидации превью ===")
    
    # Создаем тестовое изображение
    test_image_path = await create_test_image()
    
    # Генерируем превью
    result = await thumbnail_service.generate_image_thumbnail(
        image_path=test_image_path,
        output_dir="storage/content/thumbnails",
        thumbnail_name="validation_test_thumb.jpg"
    )
    
    if result["status"] == "ready":
        # Проверяем валидацию
        is_valid = await thumbnail_service.validate_thumbnail(result['thumbnail_path'])
        print(f"Результат валидации: {'✓ Валидно' if is_valid else '✗ Не валидно'}")
        return is_valid
    else:
        print("✗ Невозможно проверить валидацию - превью не создано")
        return False


async def main():
    """Основная функция тестирования"""
    print("Запуск комплексного теста системы генерации превью")
    print("=" * 50)
    
    try:
        # Тест генерации превью для изображения
        image_test_passed = await test_image_thumbnail_generation()
        
        # Тест генерации превью для видео
        video_test_passed = await test_video_thumbnail_generation()
        
        # Тест валидации
        validation_test_passed = await test_thumbnail_validation()
        
        print("\n" + "=" * 50)
        print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        print(f"• Генерация превью для изображения: {'✓ Пройден' if image_test_passed else '✗ Провален'}")
        print(f"• Генерация превью для видео: {'✓ Пройден' if video_test_passed else '✗ Провален'}")
        print(f"• Валидация превью: {'✓ Пройден' if validation_test_passed else '✗ Провален'}")
        
        overall_result = image_test_passed and video_test_passed and validation_test_passed
        print(f"\nОбщий результат: {'✓ Все тесты пройдены успешно' if overall_result else '✗ Некоторые тесты провалены'}")
        
        return overall_result
        
    except Exception as e:
        print(f"\n✗ Критическая ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)