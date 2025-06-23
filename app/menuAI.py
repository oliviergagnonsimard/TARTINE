from database import conn
from main import getUserRecipes
from scrapping import model

def getUserRecipes(idClient):
    pass

def getUserIngrediants(idClient):
    pass

def MenuAiText():
    EXTRACT_CIRCULAIRE_PROMPT = f"""You have a very important and critical job to do. Your goal is to suggest meals to prepare using ingrediants that are
    on sale this week. Try to recommend meals that combine multiple reduced ingrediants if possible, also, suggest meals that use a big portion of an ingrediant
    that is on sale.
    """
    return EXTRACT_CIRCULAIRE_PROMPT

