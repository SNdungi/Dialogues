import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
instance_folder = os.path.join(BASE_DIR,"..",'instance')


# Get all .db files in the instance folder
db_files = [f for f in os.listdir(instance_folder) if f.endswith(".db")]

print("Database files found:")
for db in db_files:
   print(db)