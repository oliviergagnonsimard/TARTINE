from database import connectToDB, releaseConn
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()
password_hash = bcrypt.generate_password_hash("password123").decode('utf-8')

first_names = ["Liam", "Emma", "Noah", "Olivia", "William", "Ava", "James", "Isabella", "Oliver", "Sophia",
               "Benjamin", "Mia", "Elijah", "Charlotte", "Lucas", "Amelia", "Mason", "Harper", "Logan", "Evelyn",
               "Alexandre", "Marie", "Gabriel", "Sophie", "Antoine", "Camille", "Nicolas", "Léa", "Thomas", "Chloé",
               "Maxime", "Jade", "Raphaël", "Manon", "Hugo", "Inès", "Théo", "Lucie", "Mathis", "Clara"]

last_names = ["Tremblay", "Gagnon", "Roy", "Côté", "Bouchard", "Gauthier", "Morin", "Lavoie", "Fortin", "Gagné",
              "Ouellet", "Pelletier", "Leblanc", "Bergeron", "Savard", "Lapointe", "Simard", "Bélanger", "Lévesque", "Paquette"]

import random
from datetime import date, timedelta

conn = connectToDB()
with conn.cursor() as curs:
    for i in range(100):
        firstName = random.choice(first_names)
        lastName = random.choice(last_names)
        email = f"{firstName.lower()}.{lastName.lower()}{i}@example.com"
        username = f"{firstName.lower()}{i}"
        birthday = date(1970, 1, 1) + timedelta(days=random.randint(0, 365*50))
        
        curs.execute("""
            INSERT INTO client (email, "firstName", "lastName", "birthDate", username, password_hash, is_verified, role, ranked)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE, 'user', TRUE)
        """, (email, firstName, lastName, birthday, username, password_hash))

conn.commit()
releaseConn(conn)
print("100 users créés!")