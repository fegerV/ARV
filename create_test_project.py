from app.core.database import get_db
from app.models.project import Project
from sqlalchemy.orm import Session
import asyncio

async def create_test_project():
    # Получаем сессию базы данных
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # Создаем тестовый проект для компании с ID 1
        test_project = Project(
            company_id=1,
            name="Test Project",
            status="active"
        )
        
        db.add(test_project)
        await db.commit()
        await db.refresh(test_project)
        
        print(f'Test project created successfully!')
        print(f'Project ID: {test_project.id}')
        print(f'Project Name: {test_project.name}')
        print(f'Company ID: {test_project.company_id}')
        
    except Exception as e:
        print(f'Error creating test project: {str(e)}')
        await db.rollback()
    finally:
        await db.close()
        await db_gen.aclose()

if __name__ == "__main__":
    asyncio.run(create_test_project())