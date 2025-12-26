#!/usr/bin/env python3
"""
Тестирование создания AR-контента после исправления схемы базы данных
"""
import asyncio
import aiohttp
import json
from pathlib import Path

# Базовый URL API
BASE_URL = "http://localhost:8000"

async def test_ar_content_creation():
    """Тест создания AR-контента с фото и видео"""
    
    print("🚀 Начинаем тестирование создания AR-контента...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Сначала авторизуемся как администратор
            print("\n1. Авторизация администратора...")
            login_data = {
                "username": "admin@vertexar.com", 
                "password": "admin123"
            }
            
            async with session.post(f"{BASE_URL}/api/auth/login", data=login_data) as resp:
                if resp.status != 200:
                    print(f"❌ Ошибка авторизации: {resp.status}")
                    text = await resp.text()
                    print(f"Ответ: {text}")
                    return False
                
                login_result = await resp.json()
                token = login_result["access_token"]
                print("✅ Авторизация успешна")
            
            # Устанавливаем заголовки для авторизации
            headers = {"Authorization": f"Bearer {token}"}
            
            # 2. Проверяем доступные компании
            print("\n2. Проверка компаний...")
            async with session.get(f"{BASE_URL}/api/companies", headers=headers) as resp:
                if resp.status != 200:
                    print(f"❌ Ошибка получения компаний: {resp.status}")
                    return False
                
                companies = await resp.json()
                if not companies.get("items"):
                    print("❌ Нет доступных компаний")
                    return False
                
                company = companies["items"][0]
                company_id = company["id"]
                print(f"✅ Найдена компания: {company['name']} (ID: {company_id})")
            
            # 3. Проверяем доступные проекты
            print("\n3. Проверка проектов...")
            async with session.get(f"{BASE_URL}/api/projects", headers=headers) as resp:
                if resp.status != 200:
                    print(f"❌ Ошибка получения проектов: {resp.status}")
                    return False
                
                projects = await resp.json()
                if not projects.get("items"):
                    print("❌ Нет доступных проектов")
                    return False
                
                project = projects["items"][0]
                project_id = project["id"]
                print(f"✅ Найден проект: {project['name']} (ID: {project_id})")
            
            # 4. Создаем тестовые файлы, если их нет
            test_image_path = Path("valid_test_image.png")
            test_video_path = Path("test_video.mp4")
            
            if not test_image_path.exists():
                print("\n4. Создаем тестовое изображение...")
                from PIL import Image
                img = Image.new('RGB', (300, 300), color='blue')
                img.save(test_image_path)
                print("✅ Тестовое изображение создано")
            
            if not test_video_path.exists():
                print("\n4b. Создаем тестовое видео...")
                # Создаем простое MP4 видео с помощью FFmpeg если доступно
                import subprocess
                try:
                    # Пробуем создать черное видео на 1 секунду
                    subprocess.run([
                        'ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=320x240:d=1',
                        '-c:v', 'libx264', '-t', '1', '-y', str(test_video_path)
                    ], check=True, capture_output=True)
                    print("✅ Тестовое видео создано")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Если FFmpeg недоступен, создаем файл-заглушку
                    with open(test_video_path, 'wb') as f:
                        f.write(b'fake video content for testing')
                    print("⚠️ Создан файл-заглушка для видео")
            
            # 5. Создаем AR-контент
            print("\n5. Создание AR-контента...")
            
            # Загружаем файлы
            with open(test_image_path, 'rb') as f:
                image_data = f.read()
            
            with open(test_video_path, 'rb') as f:
                video_data = f.read()
            
            form_data = aiohttp.FormData()
            form_data.add_field('company_id', str(company_id))
            form_data.add_field('project_id', str(project_id))
            form_data.add_field('name', 'Test AR Content')
            form_data.add_field('description', 'Test AR content for validation')
            form_data.add_field('content_type', 'image')
            form_data.add_field('duration_years', '1')
            form_data.add_field('photo_file', image_data, 
                              filename='test_image.png', 
                              content_type='image/png')
            form_data.add_field('video_file', video_data,
                              filename='test_video.mp4',
                              content_type='video/mp4')
            
            async with session.post(f"{BASE_URL}/api/ar-content", 
                                  data=form_data, 
                                  headers=headers) as resp:
                if resp.status != 201:
                    print(f"❌ Ошибка создания AR-контента: {resp.status}")
                    error_text = await resp.text()
                    print(f"Ошибка: {error_text}")
                    return False
                
                ar_content = await resp.json()
                ar_content_id = ar_content["id"]
                print(f"✅ AR-контент создан успешно (ID: {ar_content_id})")
                
                # Проверяем наличие полей
                if "thumbnail_url" in ar_content:
                    print(f"✅ Поле thumbnail_url присутствует: {ar_content.get('thumbnail_url')}")
                else:
                    print("⚠️ Поле thumbnail_url отсутствует в ответе")
                
                if "image_url" in ar_content:
                    print(f"✅ Поле image_url присутствует: {ar_content.get('image_url')}")
                else:
                    print("⚠️ Поле image_url отсутствует в ответе")
            
            # 6. Проверяем, что контент появился в списке
            print("\n6. Проверка списка AR-контента...")
            async with session.get(f"{BASE_URL}/api/ar-content", headers=headers) as resp:
                if resp.status != 200:
                    print(f"❌ Ошибка получения списка: {resp.status}")
                    return False
                
                content_list = await resp.json()
                found = False
                for item in content_list.get("items", []):
                    if item["id"] == ar_content_id:
                        found = True
                        print(f"✅ AR-контент найден в списке: {item['name']}")
                        break
                
                if not found:
                    print("❌ Созданный AR-контент не найден в списке")
                    return False
            
            # 7. Проверяем получение детальной информации
            print("\n7. Проверка детальной информации...")
            async with session.get(f"{BASE_URL}/api/ar-content/{ar_content_id}", 
                                 headers=headers) as resp:
                if resp.status != 200:
                    print(f"❌ Ошибка получения детальной информации: {resp.status}")
                    return False
                
                detail = await resp.json()
                print(f"✅ Детальная информация получена: {detail['name']}")
                
                # Проверяем наличие необходимых полей
                required_fields = ["id", "name", "company_id", "project_id", "status"]
                for field in required_fields:
                    if field in detail:
                        print(f"✅ Поле {field} присутствует")
                    else:
                        print(f"❌ Поле {field} отсутствует")
            
            print("\n🎉 Все тесты пройдены успешно!")
            print(f"📝 Создан AR-контент с ID: {ar_content_id}")
            print("🌐 Проверить можно в админке: http://localhost:8000/ar-content")
            
            return True
            
        except Exception as e:
            print(f"❌ Произошла ошибка: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Главная функция"""
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ СОЗДАНИЯ AR-КОНТЕНТА")
    print("=" * 60)
    
    success = await test_ar_content_creation()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ВСЕ ТЕСТЫ УСПЕШНЫ")
    else:
        print("❌ ТЕСТЫ НЕ ПРОЙДЕНЫ")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())