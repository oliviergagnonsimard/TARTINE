from database import *

helpChat = """
================
1) Create recipe
2) See recipes
3) Quit
================
"""

conn = connectToDB()

def SeeRecipes():
    with conn.cursor() as curs:
        curs.execute(f"SELECT * FROM client")
        rows = curs.fetchall()
        print("===================================")
        for row in rows:
            print(row)
        print("===================================")
        id = input("idClient: ")
        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {id}")
        rows = curs.fetchall()
        curs.execute(f"SELECT name FROM client WHERE \"idClient\" = {id}")
        name = curs.fetchone()[0]
        print("===================================")
        print(f"Voici les recettes enregistrées de {name}")
        for row in rows:
            print(row)

    

while True:
    print(helpChat)
    ask = input("Choice: ")

    if ask == "1":
        continue

    if ask == "2":
        SeeRecipes()

    if ask == "3":
        exit()