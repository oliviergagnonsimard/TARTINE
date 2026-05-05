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
from r2 import imageExists, getImageUrl
from email_service import *
from datetime import date
import re

STORES = ['maxi', 'metro', 'iga', 'superc', 'provigo']
headings = ("idClient", "idRecette", "Description")

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
    user = User(userID)

    info = getUserInfo(userID)
    if info is None:
        return None

    session["firstName"] = info[2]
    session["lastName"] = info[3]

    # Met à jour le rank à chaque requête
    with app.app_context():
        leaderboard = getLeaderboard(limit=999)
        for row in leaderboard:
            if int(row[0]) == int(userID):
                session["userRank"] = int(row[2])
                break
    return user


# FONCTIONS HELPER -----------------------------

def downloadFlyersJob():
    print("⏰ Téléchargement automatique des circulaires...")
    if not checkIfFlyersAlreadyDownloaded():
        DownloadAllCirculaires()
        print("✅ Circulaires téléchargées et uploadées sur R2 !")
    else:
        print("✅ Circulaires déjà à jour !")

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
        return render_template('login.html', error="Lien invalide ou déjà utilisé")
    
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
            return render_template('register.html', error="Champs manquants" , 
                                                    firstName=firstName, 
                                                    lastName=lastName, 
                                                    email=email, 
                                                    birthday=isoBirthday)
        if len(password) < 6:
            return render_template('register.html', error="Le mot de passe doit avoir minimum 6 caractères" , 
                                                    firstName=firstName, 
                                                    lastName=lastName, 
                                                    email=email, 
                                                    birthday=isoBirthday)

        if password != confirm:
            return render_template('register.html', error="Les mots de passe ne match pas" , 
                                                    firstName=firstName, 
                                                    lastName=lastName, 
                                                    email=email, 
                                                    birthday=isoBirthday)
        
        if age < 13 or age > 100:
            return render_template('register.html', error="L'âge n'est pas valide" , 
                                                    firstName=firstName, 
                                                    lastName=lastName, 
                                                    email=email, 
                                                    birthday=isoBirthday)
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return render_template('register.html', error="Courriel invalide", 
                firstName=firstName, lastName=lastName, email=email, birthday=isoBirthday)

        existing = getUserByEmail(email)
        if existing:
            return render_template('register.html', error="Compte déjà existant" , 
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
        return render_template('register.html', success="Vérifie ton courriel pour confirmer ton compte!")

    return render_template('register.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        if not email or not password:
            return render_template('login.html', error="Champs manquants")

        user = getUserByEmail(email)

        if not user:
            return render_template('login.html', error="Login invalide")
        

        userId = user[0]
        password_hash = user[7]
        hasVerifiedEmail = user[11]

        if not hasVerifiedEmail:
            return render_template('login.html', error="Confirme ton courriel avant de te connecter")
        
        
        try:
            if BCRYPT.check_password_hash(password_hash, password):
                login_user(User(userId))
                resetSessionData(userId)
                updateUserRank()
                return redirect(url_for('dashboard'))
        except ValueError:
            return render_template('login.html', error="Compte invalide")

        return render_template('login.html', error="Login invalide")

    return render_template('login.html')
    
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

    notifications = getNotifications(userID)
    return render_template('dashboard.html', userID=userID, headings=headings, data=data, name=name, clientInfo=clientInfo, notifications=notifications)

@app.route('/flyers')
def flyers():
    areFlyersDownloaded = checkIfFlyersAlreadyDownloaded()
    if not areFlyersDownloaded:
        threading.Thread(target=triggerDownloadFlyers).start()
    epiceries = getAllEpiceries()
    week = getFlyerWeek()
    return render_template('flyers.html', epiceries=epiceries, week=week, downloading=not areFlyersDownloaded)

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
    
    return render_template('flyer.html', store=store, image_urls=image_urls, week_start=week_start)

@app.route('/recipes')
def recipes():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    
    userID = session.get("userID")
    data = getUserRecipes(userID)
    name = session.get("name")
    return render_template('recipes.html', userID=userID, headings=headings, data=data, name=name)

@app.route('/leaderboard')
@app.route('/leaderboard/<int:page>')
def leaderboard(page=1):
    leaderboard = getLeaderboard(page=page)
    headings = ( "Classement", "Nom", "Score")
    userId = session.get("userID")

    return render_template('leaderboard.html', leaderboard=leaderboard, headings=headings, page=page, current_Id=userId)

@app.route('/notifications/read/<int:id>', methods=['POST'])
def read_notification(id):
    userId = session.get("userID")
    readNotification(userId, id)
    return jsonify({"success": True})

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = getUserByEmail(email)
        if user:
            token = createResetToken(user[0])
            sendResetEmail(email, token)
        # Toujours afficher le même message pour pas révéler si l'email existe
        return render_template('forgot_password.html', success="Si ce courriel existe, un lien a été envoyé.")
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        if password != confirm:
            return render_template('reset_password.html', token=token, error="Les mots de passe ne matchent pas")
        idClient = verifyResetToken(token)
        if idClient is None:
            return render_template('reset_password.html', token=token, error="Lien invalide ou expiré")
        password_hash = BCRYPT.generate_password_hash(password).decode('utf-8')
        updatePassword(idClient, password_hash)
        return render_template('login.html', success="Mot de passe changé! Tu peux te connecter.")
    return render_template('reset_password.html', token=token)

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
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host='0.0.0.0', port=port, debug=debug)