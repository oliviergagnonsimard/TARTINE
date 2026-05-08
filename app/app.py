from flask import Flask, render_template, url_for, request, redirect, session, jsonify
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from download import DownloadAllCirculaires
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import os
from main import *
from database import *
from r2 import imageExists, getImageUrl, deleteFolderFromR2
from email_service import *
from datetime import date
import re
from functools import wraps
from scrapper import *

STORES = ['maxi', 'metro', 'iga', 'superc', 'provigo']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_URL = getURI()

BCRYPT = Bcrypt()

app = Flask(__name__, template_folder='templates')
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.secret_key = os.environ.get("SECRET_KEY")
db = SQLAlchemy(app)


class User(UserMixin):
    def __init__(self, id):
        self.id = id
        self.name = getNameFromId(id)

@login_manager.user_loader
def load_user(userID):
    info = getUserInfo(userID)
    if info is None:
        return None

    session["firstName"] = info[2]
    session["lastName"] = info[3]

    user = User(userID)
    return user


# FONCTIONS HELPER -----------------------------

def downloadFlyersJob():
    print("⏰ Téléchargement automatique des circulaires...")
    if not checkIfFlyersAlreadyDownloaded():
        
        week_start = getFlyerStartWeekStr()
        prev_week = getFlyerWeek(week_start)  # à importer/définir

        # 1. Vider la table discounts
        print("🧹 Suppression des anciens rabais en base...")
        clearDiscounts()

        # 2. Supprimer les anciens circulaires dans R2
        print("☁️  Suppression des anciens circulaires R2...")
        for store in STORES:
            deleteFolderFromR2(f"circulaires/{store}_{prev_week}/")

        # 3. Télécharger les nouveaux circulaires
        DownloadAllCirculaires()
        print("✅ Circulaires téléchargées!")

        # 4. Scraper chaque store
        for store in STORES:
            idEpicerie = getIdEpicerie(store)
            scrapeStoreFlyer(store, idEpicerie, week_start)

        # 5. Notifier les users
        users = getAllUsers(limit=9999)
        for user in users:
            createNotification(user[0], "Nouveaux circulaires!", "Les circulaires de la semaine sont disponibles!")
    else:
        print("✅ Circulaires déjà à jour!")

def updateUserRank():
    userId = session.get("userID")
    if userId:
        leaderboard = getLeaderboard(limit=999)  # tous les users
        for row in leaderboard:
            if int(row[2]) == int(userId):
                session["userRank"] = int(row[0])
                return
        session["userRank"] = None

def resetSessionData(userID):
    session["userID"] = userID
    session["data"] = getUserRecipes(userID)
    session["name"] = getNameFromId(userID)
    
    # Rank ici au lieu de load_user
    leaderboard = getLeaderboard(limit=999)
    for row in leaderboard:
        if int(row[2]) == int(userID):
            session["userRank"] = int(row[0])
            return
    session["userRank"] = None

def triggerDownloadFlyers():
    if checkIfFlyersAlreadyDownloaded():
        print("Flyers already downloaded.")
        return
    DownloadAllCirculaires()
    print("Flyers downloaded.")


# ROUTES HTML --------------------------------


@app.route('/test-notif')
def test_notif():
    createNotification(1, "Hey!", "Test de notification #2")
    return "OK"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    row = verifyUserToken(token)
    if row is None:
        return render_template('auth/login.html', error="Lien invalide ou déjà utilisé")
    
    idClient = row[0]
    login_user(User(idClient))
    resetSessionData(idClient)
    updateUserRank()
    return redirect(url_for('dashboard'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == 'POST':
        firstName = request.form.get('firstName')
        lastName = request.form.get('lastName')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        birthday = request.form.get('birthday')
        isoBirthday = date.fromisoformat(request.form.get('birthday'))
        age = calculate_age(isoBirthday)

        if not email or not password:
            return render_template('auth/register.html', error="Champs manquants" , 
                                                    firstName=firstName, 
                                                    lastName=lastName, 
                                                    email=email, 
                                                    birthday=isoBirthday)
        if len(password) < 6:
            return render_template('auth/register.html', error="Le mot de passe doit avoir minimum 6 caractères" , 
                                                    firstName=firstName, 
                                                    lastName=lastName, 
                                                    email=email, 
                                                    birthday=isoBirthday)

        if password != confirm:
            return render_template('auth/register.html', error="Les mots de passe ne match pas" , 
                                                    firstName=firstName, 
                                                    lastName=lastName, 
                                                    email=email, 
                                                    birthday=isoBirthday)
        
        if age < 13 or age > 100:
            return render_template('auth/register.html', error="L'âge n'est pas valide" , 
                                                    firstName=firstName, 
                                                    lastName=lastName, 
                                                    email=email, 
                                                    birthday=isoBirthday)
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return render_template('auth/register.html', error="Courriel invalide", 
                firstName=firstName, lastName=lastName, email=email, birthday=isoBirthday)

        existing = getUserByEmail(email)
        if existing:
            return render_template('auth/register.html', error="Compte déjà existant" , 
                                                    firstName=firstName, 
                                                    lastName=lastName, 
                                                    email=email, 
                                                    birthday=isoBirthday)

        # hash
        password_hash = BCRYPT.generate_password_hash(password).decode('utf-8')

        # créer user
        userID = createUser(firstName, lastName, email, password_hash, birthday)

        # send notif
        createNotification(userID, "Bienvenue!", "Merci de vous être inscrit à Tartine!")

        # Générer et envoyer le token de confirmation
        token = createVerificationToken(userID)
        sendConfirmationEmail(email, token)

        # Pas de login automatique avant confirmation
        return render_template('auth/register.html', success="Vérifie ton courriel pour confirmer ton compte!")

    return render_template('auth/register.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        if not email or not password:
            return render_template('auth/login.html', error="Champs manquants")

        user = getUserByEmail(email)

        if not user:
            return render_template('auth/login.html', error="Login invalide")
        

        userId = user[0]
        password_hash = user[7]
        hasVerifiedEmail = user[11]

        if not hasVerifiedEmail:
            return render_template('auth/login.html', error="Confirme ton courriel avant de te connecter")
        
        
        try:
            if BCRYPT.check_password_hash(password_hash, password):
                login_user(User(userId))
                resetSessionData(userId)
                updateUserRank()
                updateLastLogin(userId)
                return redirect(url_for('dashboard'))
        except ValueError:
            return render_template('auth/login.html', error="Compte invalide")

        return render_template('auth/login.html', error="Login invalide")

    return render_template('auth/login.html')
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

    
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    userID = session.get("userID")
    
    if request.method == 'POST':
        email = request.form['email']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        birthday = request.form['birthday']
        participe = request.form.get('participe') == 'on'

        setUserInfo(userID, email, firstname, lastname, birthday, participe)
        return redirect(url_for('dashboard'))
    
    data = getUserRecipes(userID)
    name = session.get("name")
    clientInfo = getUserInfo(userID)
    notifications = getNotifications(userID, False)

    return render_template('dashboard.html', userID=userID, data=data, name=name, clientInfo=clientInfo, notifications=notifications)

@app.route('/flyers')
def flyers():
    areFlyersDownloaded = checkIfFlyersAlreadyDownloaded()
    if not areFlyersDownloaded:
        threading.Thread(target=triggerDownloadFlyers).start()
    epiceries = getAllEpiceries()
    week = getFlyerWeek()
    return render_template('flyers/flyers.html', epiceries=epiceries, week=week, downloading=not areFlyersDownloaded)

@app.route('/flyers/status')
def flyers_status():
    downloading = checkIfFlyersAlreadyDownloaded()
    return {"downloading": not downloading}

from r2 import imageExists, getImageUrl

@app.route('/flyers/<store>')
def flyer(store):
    if store not in STORES:
        return 404
    
    week_start = getFlyerStartWeekStr()
    
    # Compte les pages disponibles dans R2
    nbPages = 0
    while imageExists(f"circulaires/{store}_{week_start}/{store}{nbPages}.png"):
        nbPages += 1
    
    # Génère les URLs R2 pour chaque page
    image_urls = [
        getImageUrl(f"circulaires/{store}_{week_start}/{store}{i}.png")
        for i in range(0, nbPages, 2)  # ton compteur va de 2 en 2
    ]
    
    return render_template('flyers/flyer.html', store=store, image_urls=image_urls, week_start=week_start)

# ====================================
# ====================================
#               RECETTES
# ====================================
# ====================================

@app.route('/recipes')
def recipes():

    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    
    userID = session.get("userID")
    data = getUserRecipes(userID)
    name = session.get("name")
    headings = ["Ordre", "Nom", "Portions", "Date de création"]

    return render_template('recipes/recipes.html', userID=userID, headings=headings, data=data, name=name)

@app.route('/recipes/reorder', methods=['POST'])
@login_required
def reorder_recipes():
    userID = session.get("userID")
    data = request.get_json()
    updateRecipesOrder(userID, data['ordre'])
    return jsonify({'success': True})

@app.route('/recipes/<int:idRecette>')
@login_required
def recipe_detail(idRecette):
    userID = session.get("userID")
    recette, ingredients = getRecetteWithIngredients(idRecette, userID)
    
    if recette is None:
        return redirect(url_for('recipes') + '?error=Recette introuvable')
    
    return render_template('recipes/recipes_detail.html', recette=recette, ingredients=ingredients)

@app.route('/recipes/create', methods=['GET', 'POST'])
@login_required
def create_recipe():
    if request.method == 'POST':
        userID = session.get("userID")
        nom = request.form.get('nom')
        portions = request.form.get('portions', 4)
        instructions = request.form.get('instructions')

        # Créer la recette
        idRecette = createRecette(userID, nom, portions, instructions)

        # Ajouter les ingrédients — le formulaire envoie des listes
        noms = request.form.getlist('ingredient_nom')
        quantites = request.form.getlist('ingredient_quantite')
        unites = request.form.getlist('ingredient_unite')

        for nom_ing, quantite, unite in zip(noms, quantites, unites):
            if nom_ing.strip():
                addIngredientToRecette(idRecette, nom_ing, quantite, unite)

        return redirect(url_for('recipes') + '?success=Recette créée!')
    
    return render_template('recipes/recipes_create.html')

@app.route('/recipes/<int:idRecette>/delete', methods=['GET', 'POST'])
@login_required
def delete_recipe(idRecette):
    userID = session.get("userID")
    deleteRecipe(userID, idRecette)

    return redirect(url_for('recipes'))

# app.py
@app.route('/recipes/<int:idRecette>/edit', methods=['POST'])
@login_required
def edit_recipe(idRecette):
    userID = session.get("userID")
    data = request.get_json()
    updateRecette(userID, idRecette, data['nom'], data['portions'], data['instructions'], data['ingredients'])
    return jsonify({'success': True})

# ====================================
# ====================================
#             LEADERBOARD
# ====================================
# ====================================

@app.route('/leaderboard')
@app.route('/leaderboard/<int:page>')
def leaderboard(page=1):
    leaderboard = getLeaderboard(page=page)
    headings = ( "Classement", "Nom", "Score")
    userId = session.get("userID")

    return render_template('leaderboard.html', leaderboard=leaderboard, headings=headings, page=page, current_Id=userId)

# ====================================
# ====================================
#            NOTIFICATIONS
# ====================================
# ====================================

@app.route('/notifications/read/<int:id>', methods=['POST'])
def read_notification(id):
    userId = session.get("userID")
    readNotification(userId, id)
    return jsonify({"success": True})

@app.route('/notifications')
@login_required
def get_notifications():
    userID = session.get("userID")
    notifs = getNotifications(userID, False)
    return jsonify([{
        "id": n[0],
        "title": n[1],
        "message": n[2],
        "isread": n[3],
        "created_at": n[4].strftime('%d/%m/%Y %Hh%M')
    } for n in notifs])

@app.route('/notifications/dismiss/<int:id>', methods=['POST'])
def dismiss_notification(id):
    idClient = session.get('userID')
    dismissNotification(idClient, id)
    return jsonify({'success': True})

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = getUserByEmail(email)
        if user:
            token = createResetToken(user[0])
            sendResetEmail(email, token)
        # Toujours afficher le même message pour pas révéler si l'email existe
        return render_template('auth/password_forgot.html', success="Si ce courriel existe, un lien a été envoyé.")
    return render_template('auth/password_forgot.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if password != confirm:
            return render_template('auth/password_forgot.html', token=token, error="Les mots de passe ne matchent pas")
        
        idClient = verifyResetToken(token)
        
        if idClient is None:  # ← ici en premier
            return render_template('auth/password_forgot.html', token=token, error="Lien invalide ou expiré")

        clientInfo = getUserInfo(idClient)
        last_change = clientInfo[15]
        if passwordTimeLimitRespected(idClient):
            return render_template('auth/password_forgot.html', token=token, error="Vous devez attendre 24h entre chaque changement de mot de passe")

        password_hash = BCRYPT.generate_password_hash(password).decode('utf-8')
        updatePassword(idClient, password_hash)
        return render_template('dashboard.html', success="Mot de passe changé avec succès.")
    

    return render_template('auth/password_forgot.html', token=token)

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    userID = session.get("userID")
    clientInfo = getUserInfo(userID)

    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm = request.form.get('confirm')

    if not passwordTimeLimitRespected(userID):
            return redirect(url_for('dashboard') + '?error=Attendez 24h entre chaque changement!')

    if not BCRYPT.check_password_hash(clientInfo[7], old_password):
        return redirect(url_for('dashboard') + '?error=Ancien mot de passe incorrect')

    if new_password != confirm:
        return redirect(url_for('dashboard') + '?error=Les mots de passe ne matchent pas')

    if len(new_password) < 6:
        return redirect(url_for('dashboard') + '?error=Minimum 6 caractères')

    password_hash = BCRYPT.generate_password_hash(new_password).decode('utf-8')
    updatePassword(userID, password_hash)
    return redirect(url_for('dashboard') + '?success=Mot de passe changé!')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        userID = session.get("userID")
        clientInfo = getUserInfo(userID)
        if clientInfo[10] != 'admin':  # index 10 = role
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@app.route('/admin/<int:page>')
@admin_required
def admin(page=1):
    search = request.args.get('search', '').strip()
    users = getAllUsers(page=page, limit=20, search=search)
    total_users = countAllUsers(search=search)
    total_pages = (total_users + 19) // 20
    return render_template('admin.html', users=users, page=page, total_pages=total_pages, search=search)

@app.route('/admin/notify', methods=['POST'])
@admin_required
def admin_notify():
    title = request.form.get('title')
    message = request.form.get('message')
    target = request.form.get('target')

    if target == 'all':
        users = getAllUsers(limit=9999)
        for user in users:
            createNotification(user[0], title, message)
    
    elif target == 'specific':
        user_ids = request.form.get('user_ids', '')
        ids = [uid.strip() for uid in user_ids.split(',') if uid.strip().isdigit()]
        for uid in ids:
            createNotification(int(uid), title, message)

    return redirect(url_for('admin') + '?success=Notification envoyée!')

@app.route('/admin/reset-timer/<int:idClient>', methods=['POST'])
@admin_required
def admin_reset_timer(idClient):
    passwordTimeLimitRemove(idClient)
    return redirect(url_for('admin') + '?success=Timer reset!')

@app.route('/admin/notify-user/<int:idClient>', methods=['POST'])
@admin_required
def admin_notify_user(idClient):
    title = request.form.get('title', 'Message de l\'administration')
    message = request.form.get('message', '')
    createNotification(idClient, title, message)
    return redirect(url_for('admin') + '?success=Notification envoyée!')
# Automatic download des circulaires -------------------------------

scheduler = BackgroundScheduler()
scheduler.add_job(
    downloadFlyersJob,
    'cron',
    day_of_week='thu',  # jeudi
    hour=3,
    minute=0,
    timezone='America/Montreal'  # ← important !
)
scheduler.add_job(
    deleteUnverifiedAccounts,
    'interval',
    hours=1,
    timezone='America/Montreal'
)
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host='0.0.0.0', port=port, debug=debug)