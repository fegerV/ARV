#!/usr/bin/env python3
"""
Комплексный тест для проверки работоспособности админки Vertex AR
"""

import asyncio
import aiohttp
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

class AdminPanelTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.api_url = f"{self.base_url}/api"
        self.admin_email = "admin@vertexar.com"
        self.admin_password = "admin123"
        self.session = None
        self.auth_token = None
        self.company_id = None
        self.project_id = None
        self.ar_content_id = None
        
    async def setup(self):
        """Инициализация сессии"""
        self.session = aiohttp.ClientSession()
        
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.session:
            await self.session.close()
            
    async def login(self):
        """Аутентификация в админке"""
        print("🔐 Вход в админку...")
        
        # OAuth2PasswordRequestForm ожидает поля username и password
        # но фактически username используется для email
        login_data = {
            "username": self.admin_email,
            "password": self.admin_password
        }
        
        async with self.session.post(
            f"{self.api_url}/auth/login",
            data=login_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                self.auth_token = result.get("access_token")
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                print(f"✅ Успешный вход: {self.admin_email}")
                return headers
            else:
                error_text = await response.text()
                print(f"❌ Ошибка входа: {response.status} - {error_text}")
                return None
                
    async def get_or_create_company(self, headers):
        """Получение или создание компании Vertex AR"""
        print("🏢 Поиск компании Vertex AR...")
        
        # Поиск существующей компании
        async with self.session.get(
            f"{self.api_url}/companies",
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                companies = result if isinstance(result, list) else result.get("items", [])
                for company in companies:
                    if isinstance(company, dict) and company.get("name") == "Vertex AR":
                        self.company_id = company["id"]
                        print(f"✅ Найдена компания: {company['name']} (ID: {company['id']})")
                        return self.company_id
                        
        # Создание новой компании
        print("🏢 Создание компании Vertex AR...")
        company_data = {
            "name": "Vertex AR",
            "contact_email": "admin@vertexar.com",
            "status": "active"
        }
        
        async with self.session.post(
            f"{self.api_url}/companies",
            headers=headers,
            json=company_data
        ) as response:
            if response.status == 201:
                company = await response.json()
                self.company_id = company["id"]
                print(f"✅ Компания создана: {company['name']} (ID: {company['id']})")
                return self.company_id
            else:
                error_text = await response.text()
                print(f"❌ Ошибка создания компании: {response.status} - {error_text}")
                return None
                
    async def create_project(self, headers):
        """Создание проекта 'Портреты'"""
        print("📁 Создание проекта 'Портреты'...")
        
        project_data = {
            "name": "Портреты",
            "description": "Проект для создания портретов с AR-контентом",
            "company_id": self.company_id,
            "status": "active"
        }
        
        async with self.session.post(
            f"{self.api_url}/projects",
            headers=headers,
            json=project_data
        ) as response:
            if response.status in [200, 201]:
                project = await response.json()
                self.project_id = project["id"]
                print(f"✅ Проект создан: {project['name']} (ID: {project['id']})")
                return self.project_id
            else:
                error_text = await response.text()
                print(f"❌ Ошибка создания проекта: {response.status} - {error_text}")
                return None
                
    async def create_ar_content(self, headers):
        """Создание AR-контента"""
        print("🎨 Создание AR-контента...")
        
        # Генерация уникального ID
        unique_id = f"portrait_{int(time.time())}"
        
        ar_content_data = {
            "name": "Портрет с AR-эффектом",
            "unique_id": unique_id,
            "company_id": self.company_id,
            "project_id": self.project_id,
            "customer_info": {
                "name": "Иван Петров",
                "email": "ivan.petrov@example.com",
                "phone": "+7 (900) 123-45-67",
                "address": "г. Москва, ул. Примерная, д. 1"
            },
            "description": "Портрет с дополненной реальностью для демонстрации",
            "status": "pending"
        }
        
        async with self.session.post(
            f"{self.api_url}/ar-content",
            headers=headers,
            json=ar_content_data
        ) as response:
            if response.status in [200, 201]:
                ar_content = await response.json()
                self.ar_content_id = ar_content["id"]
                print(f"✅ AR-контент создан: {ar_content['name']} (ID: {ar_content['id']})")
                print(f"   Уникальный ID: {ar_content['unique_id']}")
                return self.ar_content_id
            else:
                error_text = await response.text()
                print(f"❌ Ошибка создания AR-контента: {response.status} - {error_text}")
                return None

async def main():
    """Главная функция"""
    tester = AdminPanelTest()
    
    try:
        await tester.setup()
        
        # 1. Аутентификация
        headers = await tester.login()
        if not headers:
            return False
            
        # 2. Получение/создание компании
        if not await tester.get_or_create_company(headers):
            return False
            
        # 3. Создание проекта
        if not await tester.create_project(headers):
            return False
            
        # 4. Создание AR-контента
        if not await tester.create_ar_content(headers):
            return False
            
        print("\n🎉 БАЗОВЫЙ ТЕСТ УСПЕШНО ЗАВЕРШЕН!")
        print("✅ Проверенные функции:")
        print("   🔐 Аутентификация в админке")
        print("   🏢 Создание/получение компании")
        print("   📁 Создание проекта 'Портреты'")
        print("   🎨 Создание AR-контента с данными заказчика")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка выполнения теста: {e}")
        return False
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n🎯 Базовые функции админки работают корректно!")
    else:
        print("\n❌ Обнаружены проблемы в работе админки!")