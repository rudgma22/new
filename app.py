from flask import Flask, redirect, url_for
from flask_mail import Mail
from auth import auth_bp
from views import views_bp
from models import db
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.config.from_object('config.DevelopmentConfig')

# Flask-Mail 초기화
mail = Mail(app)

db.init_app(app)

# 블루프린트 등록
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(views_bp, url_prefix='/views')

@app.route('/')
def index():
    return redirect(url_for('auth.index'))

# 데이터베이스 초기화
with app.app_context():
    print("Initializing the database...")
    db.create_all()
    print("Database initialized.")

if __name__ == '__main__':
    app.run(debug=True)
