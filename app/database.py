# Librairie pour intéragir avec notre database
import psycopg2
from psycopg2 import pool
import os
import platform
from dotenv import load_dotenv

load_dotenv()

connection_pool = pool.SimpleConnectionPool(
    1,  # min connections
    10, # max connections
    host=     os.environ.get("DB_HOST"),
    port=     os.environ.get("DB_PORT"),
    dbname=   os.environ.get("DB_NAME"),
    user=     os.environ.get("DB_USER"),
    password= os.environ.get("DB_PASSWORD")
)

# --- Gestion des slashs en fonction de l'OS
PLATFORM = platform.system()
SLASHS = "\\"

if PLATFORM == "Linux":
    SLASHS = "/"

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
configFile = DIR_PATH + SLASHS + "dbinfo.json"

# FONCTIONS ------------------------------------------------------------------------------------------
def connectToDB():
    return connection_pool.getconn()

def releaseConn(conn):
    connection_pool.putconn(conn)

def getURI():
    user =     os.environ.get("DB_USER")
    pwd =      os.environ.get("DB_PASSWORD")
    host =     os.environ.get("DB_HOST")
    port =     os.environ.get("DB_PORT")
    dbName =   os.environ.get("DB_NAME")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{dbName}"


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
    releaseConn()
