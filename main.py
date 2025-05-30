from database import *

helpChat = """
================
1) Create recipe
2) See recipes
3) Quit
================
"""

conn = connectToDB()

def showClients():
    with conn.cursor() as curs:
        curs.execute(f"SELECT * FROM client")
        rows = curs.fetchall()
        print("===================================")
        for row in rows:
            print(row)
        print("===================================")

def SeeRecipes():
    with conn.cursor() as curs:
        showClients()
        id = input("idClient: ")
        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {id}")
        rows = curs.fetchall()
        curs.execute(f"SELECT name FROM client WHERE \"idClient\" = {id}")
        name = curs.fetchone()[0]
        print("===================================")
        print(f"Voici les recettes enregistrées de {name}:")
        for row in rows:
            print(row)


def addRecipe():
    with conn.cursor() as curs:
        showClients()
        id = input("idClient: ")
        desc = input("Description de la recette: ")

        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {id} ORDER BY \"idRecette\" DESC")
        newRecipeId = curs.fetchone()[1]
        newRecipeId += 1

        curs.execute(f"INSERT INTO recette VALUES({id}, {newRecipeId}, \'{desc}\')")
        confirmCommitToDB(conn)
    

while True:
    print(helpChat)
    ask = input("Choice: ")

    if ask == "1":
        addRecipe()

    if ask == "2":
        SeeRecipes()

    if ask == "3":
        exit()