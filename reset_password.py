import bcrypt

# Generate a hash for a simple password
password = "password"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(f"New hash: {hashed.decode('utf-8')}")