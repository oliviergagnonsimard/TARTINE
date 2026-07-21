import os
import logging
from download import DownloadAllCirculaires
from r2 import deleteFolderFromR2
from main import getFlyerStartWeekStr, getPrevWeekStart, matchCatalogWithDiscounts
from database import clearDiscounts, getIdEpicerie, notifyAllUsers
from scrapper import scrapeStoreFlyer

# STORES list centralized for scheduler
STORES = ['maxi', 'metro', 'iga', 'superc', 'provigo']

# Logging: if not configured by the importer, configure a file logger
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(BASE_DIR, 'logs')
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, 'scheduler.log')
logger = logging.getLogger('tartine.scheduler')
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    logger = logging.getLogger('tartine.scheduler')


def downloadFlyersJob():
    logger.info("⏰ Téléchargement automatique des circulaires...")
    try:
        week_start = getFlyerStartWeekStr()
        logger.info("Current week: %s", week_start)
        prev_week = getPrevWeekStart(week_start)
        logger.info("Last week: %s", prev_week)

        if checkIfFlyersAlreadyDownloaded():
            logger.info("✅ Circulaires déjà à jour pour la semaine en cours.")
            return

        # 1. Vider la table discounts
        logger.info("🧹 Suppression des anciens rabais en base...")
        clearDiscounts()

        # 2. Supprimer les anciens circulaires dans R2
        logger.info("☁️  Suppression des anciens circulaires R2...")
        for store in STORES:
            prefix = f"circulaires/{store}_{prev_week}/"
            logger.info("  - %s", prefix)
            deleteFolderFromR2(prefix)

        # 3. Télécharger les nouveaux circulaires
        DownloadAllCirculaires()
        logger.info("✅ Circulaires téléchargées!")

        # 4. Scraper chaque store
        for store in STORES:
            idEpicerie = getIdEpicerie(store)
            scrapeStoreFlyer(store, idEpicerie, week_start)

        # 5. Matcher catalog avec discounts
        matchCatalogWithDiscounts(week_start)

        # 6. Notifier les users
        notifyAllUsers("Nouveaux circulaires!", "Les circulaires de la semaine sont disponibles!")
        logger.info("downloadFlyersJob terminé avec succès")
    except Exception:
        logger.exception("Erreur dans downloadFlyersJob")
        raise
