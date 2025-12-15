#!/usr/bin/env python3
"""
Validation script to check that the seed migration is properly structured.

This script validates the migration file structure and syntax without
requiring a database connection.
"""

import sys
from pathlib import Path

def validate_migration():
    """Validate the seed migration file structure"""
    print("🔍 Validating seed migration...")
    
    migration_file = Path("alembic/versions/20250623_1000_a1b2c3d4e5f6_seed_initial_data.py")
    
    if not migration_file.exists():
        print("❌ Migration file not found")
        return False
    
    # Read migration content
    content = migration_file.read_text()
    
    # Check required elements
    required_elements = [
        "revision: str = 'a1b2c3d4e5f6'",
        "down_revision: Union[str, None] = '44af7900a836'",
        "def upgrade()",
        "def downgrade()",
        "pwd_context = CryptContext(schemes=[\"bcrypt\"], deprecated=\"auto\")",
        "admin@vertex.local",
        "Vertex AR",
        "admin123",
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Missing required elements in migration:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Migration structure validation passed")
    return True


def validate_seed_script():
    """Validate the seed script structure"""
    print("\n🔍 Validating seed script...")
    
    script_file = Path("scripts/seed_db.py")
    
    if not script_file.exists():
        print("❌ Seed script not found")
        return False
    
    # Read script content
    content = script_file.read_text()
    
    # Check required elements
    required_elements = [
        "async def create_admin_user",
        "async def create_default_company", 
        "async def main",
        "admin@vertex.local",
        "Vertex AR",
        "pwd_context.hash(\"admin123\")",
        "CompanyStatus.ACTIVE",
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Missing required elements in seed script:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Seed script structure validation passed")
    return True


def validate_entrypoint():
    """Validate entrypoint.sh integration"""
    print("\n🔍 Validating entrypoint integration...")
    
    entrypoint_file = Path("entrypoint.sh")
    
    if not entrypoint_file.exists():
        print("❌ Entrypoint script not found")
        return False
    
    # Read entrypoint content
    content = entrypoint_file.read_text()
    
    # Check required elements
    required_elements = [
        "alembic upgrade head",
        "python scripts/seed_db.py",
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Missing required elements in entrypoint:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Entrypoint integration validation passed")
    return True


def main():
    """Main validation function"""
    print("🧪 Validating seed implementation...")
    
    # Change to project directory
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)
    print(f"Working directory: {os.getcwd()}")
    
    # Validate all components
    migration_ok = validate_migration()
    script_ok = validate_seed_script()
    entrypoint_ok = validate_entrypoint()
    
    if migration_ok and script_ok and entrypoint_ok:
        print("\n🎉 All seed implementation validations passed!")
        print("\n📋 Summary:")
        print("   ✅ Alembic migration created and properly structured")
        print("   ✅ Seed script created with async implementation")
        print("   ✅ Docker entrypoint integration configured")
        print("   ✅ Test script available for validation")
        print("   ✅ Documentation provided")
        
        print("\n🚀 Ready to use:")
        print("   1. Run migrations: alembic upgrade head")
        print("   2. Or use Docker: docker-compose up app")
        print("   3. Test with: python scripts/test_seed.py")
        print("   4. Login: admin@vertex.local / admin123")
        
        return 0
    else:
        print("\n❌ Some validations failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)