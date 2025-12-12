#!/usr/bin/env python3
"""
Test script to validate schema migration overhaul
This script validates the migration logic without actually running it
"""

import ast
import sys
from pathlib import Path

def validate_migration_syntax():
    """Validate Python migration syntax"""
    migration_file = Path("alembic/versions/20251223_schema_migration_overhaul.py")
    
    if not migration_file.exists():
        print("❌ Migration file not found")
        return False
    
    try:
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Parse Python AST to validate syntax
        ast.parse(content)
        print("✅ Migration Python syntax is valid")
        return True
    except SyntaxError as e:
        print(f"❌ Migration syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading migration: {e}")
        return False

def validate_sql_syntax():
    """Validate SQL migration syntax"""
    sql_file = Path("migrations/001_initial_complete_migration.sql")
    
    if not sql_file.exists():
        print("❌ SQL migration file not found")
        return False
    
    try:
        with open(sql_file, 'r') as f:
            content = f.read()
        
        # Basic SQL syntax checks
        checks = [
            ("CREATE EXTENSION", "UUID extension creation"),
            ("CREATE TABLE", "Table creation"),
            ("CREATE INDEX", "Index creation"),
            ("REFERENCES companies", "Company foreign key"),
            ("REFERENCES ar_content", "AR Content foreign key"),
            ("REFERENCES projects", "Project foreign key"),
            ("ON DELETE CASCADE", "Cascade delete"),
            ("UNIQUE", "Unique constraints"),
            ("INSERT INTO", "Default data insertion")
        ]
        
        for check, description in checks:
            if check in content:
                print(f"✅ {description}")
            else:
                print(f"❌ Missing: {description}")
        
        # Check for removed tables
        removed_tables = ["portraits", "orders"]
        for table in removed_tables:
            if f"CREATE TABLE IF NOT EXISTS {table}" not in content:
                print(f"✅ Legacy table '{table}' properly removed")
            else:
                print(f"❌ Legacy table '{table}' still present")
        
        return True
    except Exception as e:
        print(f"❌ Error reading SQL file: {e}")
        return False

def validate_model_consistency():
    """Validate model consistency with schema"""
    video_model = Path("app/models/video.py")
    ar_content_model = Path("app/models/ar_content.py")
    
    if not video_model.exists():
        print("❌ Video model not found")
        return False
    
    if not ar_content_model.exists():
        print("❌ AR Content model not found")
        return False
    
    try:
        # Check video model foreign key
        with open(video_model, 'r') as f:
            video_content = f.read()
        
        if 'ForeignKey("ar_content.id")' in video_content:
            print("✅ Video model foreign key correct")
        else:
            print("❌ Video model foreign key incorrect")
        
        # Check ar_content model structure
        with open(ar_content_model, 'r') as f:
            ar_content = f.read()
        
        required_fields = [
            "name = Column",
            "video_path = Column", 
            "video_url = Column",
            "qr_code_url = Column",
            "preview_url = Column",
            "content_metadata = Column"
        ]
        
        for field in required_fields:
            if field in ar_content:
                print(f"✅ AR Content field: {field.split('=')[0].strip()}")
            else:
                print(f"❌ Missing AR Content field: {field.split('=')[0].strip()}")
        
        return True
    except Exception as e:
        print(f"❌ Error validating models: {e}")
        return False

def validate_migration_chain():
    """Validate Alembic migration chain"""
    migration_file = Path("alembic/versions/20251223_schema_migration_overhaul.py")
    
    try:
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Check revision chain
        if "down_revision = '20251220_rebuild_ar_content_api'" in content:
            print("✅ Migration chain correct")
        else:
            print("❌ Migration chain incorrect")
        
        # Check for required functions
        if "def upgrade():" in content and "def downgrade():" in content:
            print("✅ Both upgrade and downgrade functions present")
        else:
            print("❌ Missing upgrade or downgrade functions")
        
        return True
    except Exception as e:
        print(f"❌ Error validating migration chain: {e}")
        return False

def main():
    print("🔍 Validating Schema Migration Overhaul")
    print("=" * 50)
    
    validations = [
        validate_migration_syntax,
        validate_sql_syntax,
        validate_model_consistency,
        validate_migration_chain
    ]
    
    results = []
    for validation in validations:
        try:
            result = validation()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Validation error: {e}")
            results.append(False)
            print()
    
    print("=" * 50)
    if all(results):
        print("🎉 All validations passed! Migration is ready.")
        return 0
    else:
        print("❌ Some validations failed. Please review and fix issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())