# Librairie pour intéragir avec notre database
import psycopg2
import json
import os
import platform

# --- Gestion des slashs en fonction de l'OS
PLATFORM = platform.system()
SLASHS = "\\"

if PLATFORM == "Linux":
    SLASHS = "/"

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
configFile = DIR_PATH + SLASHS + "dbinfo.json"

# FONCTIONS ------------------------------------------------------------------------------------------
def createDBFile():
    with open(configFile, "w") as f:
        api_text = { "hostname": "null",
                    "port": "null",
                    "dbname": "null",
                    "user": "null",
                    "password": "null"
                }

        jsonObject = json.dumps(api_text, indent=4)
        f.write(jsonObject)

def connectToDB():
    with open(configFile, "r") as f:
        dbinfo = json.load(f)
        return psycopg2.connect(
            host=       dbinfo["hostname"],
            port=       dbinfo["port"],
            dbname=     dbinfo["dbname"],
            user=       dbinfo["user"],
            password=   dbinfo["password"]
        )

def parseSQL(text):
    text = text[6:-3]
    text = text.replace("\n", "")
    return text

def confirmCommitToDB(conn):
    a = input("Are you sure you want to push your changes to the database? (y/n) ")
    if a == "y":
        conn.commit()

def clearDiscountDB():
    conn = connectToDB()

    with conn.cursor() as curs:
        curs.execute("DELETE FROM discount")

    confirmCommitToDB(conn)
