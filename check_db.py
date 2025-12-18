from app.core.database import get_db
from app.models.company import Company
from app.models.project import Project
from app.models.user import User
from sqlalchemy import select
import asyncio
import asyncpg

async def check_data():
    # Получаем сессию базы данных
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # Подсчитываем количество компаний
        companies = await db.execute(select(Company))
        companies_list = companies.scalars().all()
        print(f'Companies: {len(companies_list)}')
        for company in companies_list:
            print(f'  - ID: {company.id}, Name: {company.name}, Email: {company.contact_email}')
        
        # Подсчитываем количество проектов
        projects = await db.execute(select(Project))
        projects_list = projects.scalars().all()
        print(f'Projects: {len(projects_list)}')
        for project in projects_list:
            print(f'  - ID: {project.id}, Name: {project.name}, Company ID: {project.company_id}')
        
        # Подсчитываем количество пользователей
        users = await db.execute(select(User))
        users_list = users.scalars().all()
        print(f'Users: {len(users_list)}')
        for user in users_list:
            print(f'  - ID: {user.id}, Email: {user.email}, Role: {user.role}, Active: {user.is_active}')
            
    finally:
        await db.close()
        await db_gen.aclose()

if __name__ == "__main__":
    asyncio.run(check_data())