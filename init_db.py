from flask import Flask
from models import db

app = Flask(__name__)

# MySQL 데이터베이스 URI 설정 (변경)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://gimpass2024:ehdud0116**@211.47.75.102:3306/dbgimpass2024'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    print("Initializing the database...")
    db.drop_all()  # 기존 테이블 모두 삭제 (주의: 실사용 환경에서는 조심히 사용)
    db.create_all()  # 모든 테이블 생성
    print("Database initialized.")
