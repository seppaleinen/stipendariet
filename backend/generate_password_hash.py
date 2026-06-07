"""
Utility to generate the correct password hash for stipendie admin
"""

from passlib.context import CryptContext

# Initialize password hashing context to match what's used in the application
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plaintext password using the same method as the application."""
    return pwd_context.hash(password)

if __name__ == "__main__":
    password = "placeholder-password"
    hashed = hash_password(password)
    print(f"Original password: {password}")
    print(f"Hashed password: {hashed}")
    print("\nTo fix the login issue, execute this SQL command in your database:")
    print(f"UPDATE users SET hashed_password = '{hashed}' WHERE email = 'davidbaeriksson@gmail.com';")
    print("\nOr if the user doesn't exist, you can create them:")
    print(f"INSERT INTO users (email, hashed_password, name, is_active, is_admin) VALUES ('davidbaeriksson@gmail.com', '{hashed}', 'Admin User', true, true);")