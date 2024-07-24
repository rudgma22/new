from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from auth import auth_bp
from views import views_bp
from models import db, Student, Teacher, OutingRequest

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 블루프린트 등록
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(views_bp, url_prefix='/views')

@app.route('/')
def index():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
