from database import *

helpChat = """
================
1) Create recipe
2) See recipes
3) Quit
================
"""

def clearConsole():
    os.system('cls')

conn = connectToDB()

def showClients():
    with conn.cursor() as curs:
        curs.execute(f"SELECT * FROM client")
        rows = curs.fetchall()
        clearConsole()
        print("===================================")
        for row in rows:
            print(row)
        print("===================================")

def showRecipes(idClient: int):
    with conn.cursor() as curs:
        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {idClient}")
        rows = curs.fetchall()
        clearConsole()
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
        clearConsole()
        print("===================================")
        print(f"Voici les recettes enregistrées de {name}:")
        for row in rows:
            print(row)


def addRecipe():
    with conn.cursor() as curs:
        showClients()
        id = input("idClient: ")
        desc = input("Description de la recette: ")

        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {id}")

        curs.execute(f"SELECT * FROM recette WHERE \"idClient\" = {id} ORDER BY \"idRecette\" DESC")
        newRecipeId = curs.fetchone()[1]
        newRecipeId += 1

        curs.execute(f"INSERT INTO recette VALUES({id}, {newRecipeId}, \'{desc}\')")
        confirmCommitToDB(conn)
        print(f"New recipe ({newRecipeId}) added to UserID: {id}")
        showRecipes(id)

    

while True:
    print(helpChat)
    ask = input("Choice: ")

    if ask == "1":
        addRecipe()
        continue

    if ask == "2":
        SeeRecipes()
        continue

    if ask == "3":
        exit()