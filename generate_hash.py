import bcrypt

# Generate a hash for the password "admin"
password = "admin"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(hashed.decode('utf-8'))