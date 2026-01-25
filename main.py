# main.py
from db import Database

db = Database()  # auto-creates DB if needed


# only close when shutting down
db.close()
