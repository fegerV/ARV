from PIL import Image, ImageDraw

# Создаем простое изображение 500x500 пикселей
width, height = 500, 500
image = Image.new('RGB', (width, height), color='orange')

# Добавляем несколько элементов
draw = ImageDraw.Draw(image)

# Красный квадрат в центре
center_x, center_y = width // 2, height // 2
square_size = 100
draw.rectangle([
    (center_x - square_size//2, center_y - square_size//2),
    (center_x + square_size//2, center_y + square_size//2)
], fill='red')

# Зеленый круг в левом верхнем углу
circle_center = (100, 100)
radius = 50
draw.ellipse([
    (circle_center[0] - radius, circle_center[1] - radius),
    (circle_center[0] + radius, circle_center[1] + radius)
], fill='green')

# Сохраняем изображение
image.save('valid_test_image.png')
print("Valid test image created successfully!")