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
from google import genai

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
    
def sendPDF():
    client = genai.Client(api_key=apKey)

    myFile = client.files.upload(file=f"{DIR_PATH}{SLASHS}circulaire.pdf")  

    with open(f"{DIR_PATH}{SLASHS}circulaire.pdf", "rb") as f:
         contenu = f.read()

    ans = model.generate_content(
         [EXTRACT_CIRCULAIRE_PROMPT, {"mime_type": "application/pdf", "data": contenu}]
         )

    print(ans.text)

    
    
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



# --- Début de l'extraction
GROCERY_STORE = "MAXI"

EXTRACT_CIRCULAIRE_PROMPT = f"""You have a very important and critical job to do. You need to get ALL of the discounts from the: 
{GROCERY_STORE} grocery store and need to extract all of the information precisely, otherwise, customers using my service will 
get very angry. Children may also die of hunger if you don't do your job right. EXTRACT EVERY SINGLE DISCOUNT THERE IS THIS GROCERY
STORE in a STRICT and readable JSON format and give NO OTHER TEXT IN YOUR ANSWER, because you're answer will be used for a database.
ALSO NOTE: If you can't find the original price of the product, calculate it with the discounted price and percentage of reduction.
IMPORTANT PART: EACH JSON OBJECT MUST CONTAIN THE FOLLOWING ATTRIBUTES:
1) The name of the product: "Name"
2) Original pricing: "OriginalPrice"
3) Discounted pricing: "DiscountedPrice"
"""

chat_session = model.start_chat(history=[])

while True:
    print("----------------------------------")
    ask = input("ask: ")

    if ask == "/q":
        exit()
    if ask == "/g":
         sendPDF()
         continue
    if ask == "":
        continue
    if ask == "/":
        help()
        continue

    try:
        ans = chat_session.send_message(ask)
    except Exception as e:
        print("=--ERROR--= Clé API invalide.")
        exit()


    print(f"Gemini: {ans.text}")
