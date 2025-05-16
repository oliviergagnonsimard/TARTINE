# =======================================================
#                   PROJET TARTINE
# Par:
# - Olivier Gagnon-Simard
# - Victor Messier
# - Simon Petit
# =======================================================

import os
import google.generativeai as generativeAI
import json
import platform
from database import *

# ======================================================================== FONCTIONS
def createConfigFile():
    with open(configFile, "w") as f:
        api_text = { "API_KEY": "null"}

        jsonObject = json.dumps(api_text, indent=4)
        f.write(jsonObject)

def noConfigFile():
        # Si le fichier de config n'existe pas, on le créé et demande de mettre la clé API.
        print("No config file found, creating one...")
        createConfigFile()
        print("Config file created. Please add your GeminiAPI key in the 'config.json' file.")
        exit()

def noApiKey():
        # Si la clé API est nulle ou vide, on demande à l'utilisateur de la mettre dans le fichier de config.
        print("ERROR: Please add your GeminiAPI key in the 'config.json' file.")
        print("You can get your key at: https://ai.google.dev/gemini-api/docs/api-key")
        exit()

def loadAPIKey():
    if not os.path.isfile(configFile):
        noConfigFile()

    with open(configFile, "r") as config_file:
        config = json.load(config_file)

        print("Setting up API key")
        apkey = config["API_KEY"]
        if apkey == "null" or apkey == "":
            noApiKey()

        return config["API_KEY"]
    
def sendPDF(GROCERY):
    with open(f"{DIR_PATH}{SLASHS}circulaire.pdf", "rb") as f:
         contenu = f.read()

    ans = model.generate_content(
         [scrappingPDFText(GROCERY), {"mime_type": "application/pdf", "data": contenu}]
         ).text

    return parseSQL(ans)

def scrappingPDFText(GROCERY):
    EXTRACT_CIRCULAIRE_PROMPT = f"""You have a very important and critical job to do. You need to get ALL of the discounts from the: 
    {GROCERY} grocery store and need to extract all of the information precisely, otherwise, customers using my service will 
    get very angry. Children may also die of hunger if you don't do your job right. YOUR JOB IS TO SEND AND CREATE AN SQL STATEMENT THAT FILLS
    EVERY SINGLE DISCOUNT FROM THE GROCERY STORE IN THE 'discount' TABLE. DO NOT ANSWER ANYTHING OTHER THAN THE SQL STATEMENT ITSELF! JUST SEND THE
    SQL STATEMENT, NO OTHER TEXT IS ALLOWED IN YOU ANSWER. YOU NEED TO BE EXTREMELY PRECISE WITH EVERY PRICING AND DISCOUNT.
    NOTE THAT IF YOU CAN'T FIND THE ORIGINAL PRICING, CALCULATE IT WITH THE DiscountPercent. The 'discount' table has the following attributes:
    discountID			INT,
	ProductName			VARCHAR(255),
	DiscountPercent		NUMERIC,
	OriginalPrice		NUMERIC,
	DiscountedPrice		NUMERIC,
    """
    return EXTRACT_CIRCULAIRE_PROMPT

    
    
# ======================================================================== DÉBUT DU PROGRAMME

# --- Gestion des slashs en fonction de l'OS
PLATFORM = platform.system()
SLASHS = "\\"

if PLATFORM == "Linux":
    SLASHS = "/"

# --- Endroit où est éxécuté le programme
DIR_PATH = os.path.dirname(os.path.realpath(__file__))

# --- Gestion de la clé API
configFile = DIR_PATH + SLASHS + "config.json"
model = generativeAI.GenerativeModel("gemini-2.5-pro-exp-03-25")
apKey = loadAPIKey()

generativeAI.configure(api_key=apKey)