-- Создание admin пользователя для Vertex AR
-- Пароль: admin123
-- Хеш: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF2PQaDi

DELETE FROM users WHERE email = 'admin@vertexar.com';

INSERT INTO users (email, hashed_password, full_name, role, is_active, login_attempts, created_at, updated_at)
VALUES (
    'admin@vertexar.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF2PQaDi',
    'Vertex AR Admin',
    'ADMIN'::userrole,
    true,
    0,
    now(),
    now()
);

SELECT id, email, full_name, role FROM users WHERE email = 'admin@vertexar.com';
