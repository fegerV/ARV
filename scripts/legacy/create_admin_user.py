"""
Скрипт для создания администратора напрямую в SQLite базе данных
"""
import sqlite3
import hashlib
from datetime import datetime

def create_admin_user():
    """Создание администратора в SQLite базе данных"""
    print("Creating admin user in SQLite database...")
    
    # Подключаемся к базе данных
    conn = sqlite3.connect("test_vertex_ar.db")
    cursor = conn.cursor()
    
    # Создаем хэш пароля
    password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    
    # Создаем пользователя администратора
    try:
        # Проверяем, существует ли уже пользователь
        cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@vertexar.com",))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print("Admin user already exists, updating...")
            cursor.execute("""
                UPDATE users 
                SET hashed_password = ?, full_name = ?, role = ?, is_active = 1
                WHERE email = ?
            """, (password_hash, "Vertex AR Admin", "admin", "admin@vertexar.com"))
        else:
            print("Creating new admin user...")
            cursor.execute("""
                INSERT INTO users (email, hashed_password, full_name, role, is_active, created_at, updated_at, login_attempts, locked_until)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "admin@vertexar.com",
                password_hash,
                "Vertex AR Admin",
                "admin",
                1,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                0,
                None
            ))
        
        conn.commit()
        print("Admin user created/updated successfully!")
        print("Email: admin@vertexar.com")
        print("Password: admin123")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def create_default_company():
    """Создание компании по умолчанию"""
    print("Creating default company...")
    
    conn = sqlite3.connect("test_vertex_ar.db")
    cursor = conn.cursor()
    
    try:
        # Проверяем, существует ли уже компания
        cursor.execute("SELECT id FROM companies WHERE name = ?", ("Vertex AR",))
        existing_company = cursor.fetchone()
        
        if existing_company:
            print("Default company already exists")
        else:
            print("Creating default company...")
            cursor.execute("""
                INSERT INTO companies (name, slug, contact_email, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "Vertex AR",
                "vertex-ar",
                "admin@vertexar.com",
                "active",
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            conn.commit()
            print("Default company created successfully!")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin_user()
    create_default_company()
    print("\nSetup completed!")
    print("Server should now recognize the admin user.")
