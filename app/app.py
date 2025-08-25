from flask import Flask, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from main import getNameFromId, getUserRecipes, addRecipe

DB_URL = "postgresql://postgres:2nvvhejBwQF62eroQzA9@tartinedb.cdwy0g0205gp.us-east-2.rds.amazonaws.com/postgres"

app = Flask(__name__, template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.secret_key = "secret"
db = SQLAlchemy(app)

headings = ("idClient", "idRecette", "Description")

data = (
    ("1", "2", "3"),
    ("4", "5", "6")
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        userID = request.form['userID']
        session["userID"] = userID
        session["data"] = getUserRecipes(userID)
        session["name"] = getNameFromId(userID)
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html')
    
@app.route('/addRecipee', methods=['POST', 'GET'])
def addRecipee():
    userID = session.get("userID")
    if request.method == 'POST':
        addRecipe(session["userID"], request.form["desc"])
        session["userID"] = userID
        session["data"] = getUserRecipes(userID)
        session["name"] = getNameFromId(userID)
        return redirect(url_for('dashboard'))
    else:
        return render_template('addRecipee.html')
    
@app.route('/dashboard')
def dashboard():
    userID = session.get("userID")
    data = session.get("data")
    name = session.get("name")
    return render_template('dashboard.html', userID=userID, headings=headings, data=data, name=name)

if __name__ == "__main__":
    app.run(debug=True)