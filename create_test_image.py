import numpy as np
from PIL import Image

# Создаем простое изображение 500x500 пикселей
width, height = 500, 500
array = np.zeros([height, width, 3], dtype=np.uint8)
array[:, :] = [255, 128, 0]  # Оранжевый цвет

# Добавляем несколько элементов
# Красный квадрат в центре
center_x, center_y = width // 2, height // 2
square_size = 100
array[center_y-square_size//2:center_y+square_size//2, 
      center_x-square_size//2:center_x+square_size//2] = [255, 0, 0]

# Зеленый круг в левом верхнем углу
circle_center = (100, 100)
radius = 50
for y in range(height):
    for x in range(width):
        if (x - circle_center[0])**2 + (y - circle_center[1])**2 <= radius**2:
            array[y, x] = [0, 255, 0]

# Сохраняем изображение
img = Image.fromarray(array)
img.save('test_image.png')
print("Test image created successfully!")