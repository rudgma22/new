from flask import Flask
from models import db
import os

app = Flask(__name__)

# 프로젝트 루트 디렉토리 경로를 가져옵니다.
project_root = os.path.dirname(os.path.abspath(__file__))

# 데이터베이스 파일 경로를 설정합니다.
database_path = os.path.join(project_root, 'database.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    print("Initializing the database...")
    db.create_all()
    print("Database initialized.")
