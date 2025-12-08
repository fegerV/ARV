UPDATE users 
SET hashed_password = 'sha256$240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9' 
WHERE email = 'admin@vertexar.com';

SELECT email, hashed_password FROM users WHERE email = 'admin@vertexar.com';
