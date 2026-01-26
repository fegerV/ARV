"""
Скрипт для очистки дубликатов компании по умолчанию "Vertex AR".

Удаляет все дубликаты, оставляя только одну компанию "Vertex AR".
"""
import sys
import asyncio
import io
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.company import Company
import structlog

logger = structlog.get_logger()

DEFAULT_COMPANY_NAMES = ["Vertex AR", "VertexAR", "vertex-ar", "vertexar"]


async def cleanup_duplicate_companies():
    """Удалить дубликаты компании по умолчанию, оставив только одну."""
    
    # Create async engine
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite+aiosqlite:///'):
        db_url = db_url.replace('sqlite+aiosqlite:///', 'sqlite+aiosqlite:///')
    
    engine = create_async_engine(db_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            # Find all default companies
            result = await session.execute(
                select(Company).where(
                    func.lower(Company.name).in_([name.lower() for name in DEFAULT_COMPANY_NAMES]) |
                    (Company.slug == "vertex-ar")
                ).order_by(Company.id)
            )
            default_companies = result.scalars().all()
            
            if not default_companies:
                print("[OK] Компания по умолчанию 'Vertex AR' не найдена. Она будет создана при следующем запуске сервера.")
                return
            
            print(f"Найдено компаний по умолчанию: {len(default_companies)}")
            
            # Keep the first one (oldest by ID)
            keep_company = default_companies[0]
            print(f"[OK] Оставляем компанию: ID={keep_company.id}, Name='{keep_company.name}', Slug='{keep_company.slug}'")
            
            # Update it to correct values
            old_name = keep_company.name
            keep_company.name = "Vertex AR"
            keep_company.slug = "vertex-ar"
            keep_company.status = "active"
            
            if old_name != "Vertex AR":
                print(f"[UPDATE] Обновлено имя с '{old_name}' на 'Vertex AR'")
            
            # Delete duplicates
            duplicates = default_companies[1:]
            if duplicates:
                print(f"[DELETE] Удаляем {len(duplicates)} дубликатов:")
                for dup in duplicates:
                    print(f"   - ID={dup.id}, Name='{dup.name}', Slug='{dup.slug}'")
                    await session.delete(dup)
            
            await session.commit()
            
            if duplicates:
                print(f"[OK] Успешно удалено {len(duplicates)} дубликатов")
            else:
                print("[OK] Дубликатов не найдено")
                
        except Exception as e:
            await session.rollback()
            logger.error("cleanup_error", error=str(e), exc_info=True)
            print(f"[ERROR] Ошибка при очистке: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 80)
    print("ОЧИСТКА ДУБЛИКАТОВ КОМПАНИИ ПО УМОЛЧАНИЮ")
    print("=" * 80)
    print()
    
    asyncio.run(cleanup_duplicate_companies())
    
    print()
    print("=" * 80)
    print("ГОТОВО")
    print("=" * 80)
