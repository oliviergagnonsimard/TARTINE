from flask import Flask, render_template, url_for, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from main import getNameFromId, showRecipes

DB_URL = "postgresql://postgres:2nvvhejBwQF62eroQzA9@tartinedb.cdwy0g0205gp.us-east-2.rds.amazonaws.com/postgres"

app = Flask(__name__, template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
db = SQLAlchemy(app)

headings = ("idClient", "idRecette", "Description")

data = (
    ("1", "2", "3"),
    ("4", "5", "6")
)

name = ""

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Task %r>' % self.id

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
        data = showRecipes(userID)
        name = getNameFromId(userID)
        return render_template('home.html', idUser=userID, data=data, name=name)
    else:
        return render_template('login.html')
    
@app.route('/addRecipee')
def addRecipee():
    return render_template('addRecipee.html')
    
@app.route('/home')
def home():
    return render_template('home.html')

if __name__ == "__main__":
    app.run(debug=True)