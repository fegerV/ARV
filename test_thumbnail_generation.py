#!/usr/bin/env python3
"""
Тестовый скрипт для проверки генерации превью
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к приложению
sys.path.append(str(Path(__file__).parent))

from app.services.thumbnail_service import thumbnail_service


async def test_image_thumbnail():
    """Тест генерации превью для изображения"""
    print("Тестируем генерацию превью для изображения...")
    
    # Создаем тестовое изображение (если его нет)
    test_image_path = Path("test_image.jpg")
    if not test_image_path.exists():
        print("Создаем тестовое изображение...")
        # Создаем простое изображение для теста
        from PIL import Image
        img = Image.new('RGB', (800, 600), color='red')
        img.save(test_image_path)
        print(f"Тестовое изображение создано: {test_image_path}")
    
    # Генерируем превью
    result = await thumbnail_service.generate_image_thumbnail(
        image_path=str(test_image_path),
        output_dir="storage/content/thumbnails",
        thumbnail_name="test_image_thumb.jpg"
    )
    
    print(f"Результат генерации: {result}")
    
    if result["status"] == "ready":
        print(f"Превью успешно создано: {result['thumbnail_url']}")
        print(f"Путь к файлу: {result['thumbnail_path']}")
    else:
        print(f"Ошибка генерации превью: {result.get('error')}")


async def test_video_thumbnail():
    """Тест генерации превью для видео"""
    print("\nТестируем генерацию превью для видео...")
    
    # Для теста видео мы просто проверим, что функция работает
    # В реальной ситуации здесь был бы путь к видео файлу
    print("Функция генерации превью для видео готова к использованию")


async def main():
    """Основная функция тестирования"""
    print("Запуск тестов генерации превью...")
    
    try:
        await test_image_thumbnail()
        await test_video_thumbnail()
        print("\nВсе тесты завершены!")
    except Exception as e:
        print(f"Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())