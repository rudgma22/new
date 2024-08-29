# app.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from auth import auth_bp
from views import views_bp
from models import db, Student, Teacher, OutingRequest
import os
from flask_migrate import Migrate

def create_app():
    app = Flask(__name__)
    app.secret_key = 'supersecretkey'

    # 프로젝트 루트 디렉토리 경로를 가져옵니다.
    project_root = os.path.dirname(os.path.abspath(__file__))

    # 데이터베이스 파일 경로를 설정합니다.
    database_path = os.path.join(project_root, 'database.db')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # 블루프린트 등록
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(views_bp, url_prefix='/views')

    # 데이터베이스 초기화
    with app.app_context():
        print("Initializing the database...")
        db.create_all()
        print("Database initialized.")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)
