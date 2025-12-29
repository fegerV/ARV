"""
Скрипт для запуска Vertex AR сервера
"""
import os
import subprocess
import sys

def start_server():
    """Запуск сервера с правильными переменными окружения"""
    # Устанавливаем переменные окружения
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vertex_ar.db"
    os.environ["ADMIN_EMAIL"] = "admin@vertexar.com"
    os.environ["ADMIN_DEFAULT_PASSWORD"] = "admin123"
    os.environ["DEBUG"] = "true"
    os.environ["ENVIRONMENT"] = "development"
    os.environ["MEDIA_ROOT"] = "./tmp/storage"
    os.environ["STORAGE_BASE_PATH"] = "./tmp/storage"
    os.environ["LOCAL_STORAGE_PATH"] = "./tmp/storage"
    os.environ["LOCAL_STORAGE_PUBLIC_URL"] = "http://localhost:8000/storage"
    os.environ["PUBLIC_URL"] = "http://localhost:8000"
    os.environ["LOG_LEVEL"] = "INFO"
    
    print("Starting Vertex AR server...")
    print("   Server will be available at http://localhost:8000")
    print("   Admin panel: http://localhost:8000/admin")
    print("   API docs: http://localhost:8000/docs")
    print("\n   Login credentials:")
    print("   Email: admin@vertexar.com")
    print("   Password: admin123")
    print("\n   To stop the server, press Ctrl+C")
    print("="*50)
    
    # Запускаем uvicorn сервер
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting server: {e}")
    except KeyboardInterrupt:
        print("\nServer stopped by user")

if __name__ == "__main__":
    start_server()