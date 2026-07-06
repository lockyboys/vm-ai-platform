import os

from flask.cli import load_dotenv
from dotenv import load_dotenv

load_dotenv()
host = os.getenv("MONGODB_HOST")
port = os.getenv("MONGODB_PORT")
user = os.getenv("MONGODB_USER")
password = os.getenv("MONGODB_PASSWORD")
auth_db = os.getenv("MONGODB_AUTH_DATABASE")

print(host)
print(port)
print(user)
print(password)
print(auth_db)