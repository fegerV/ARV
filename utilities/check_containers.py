import subprocess
import time

def check_containers():
    try:
        # Проверяем запущенные контейнеры
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
        print("Запущенные контейнеры:")
        print(result.stdout)
        
        if result.stderr:
            print("Ошибки:")
            print(result.stderr)
            
        # Проверяем все контейнеры (включая остановленные)
        result_all = subprocess.run(['docker', 'ps', '-a'], capture_output=True, text=True, timeout=10)
        print("\nВсе контейнеры:")
        print(result_all.stdout)
        
    except subprocess.TimeoutExpired:
        print("Таймаут при выполнении команды docker")
    except Exception as e:
        print(f"Ошибка при проверке контейнеров: {e}")

if __name__ == "__main__":
    check_containers()