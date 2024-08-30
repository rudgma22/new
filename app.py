from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from auth import auth_bp  # 인증 관련 블루프린트
from views import views_bp  # 기타 뷰 관련 블루프린트
from models import db, Student, Teacher, OutingRequest, execute_with_retry  # 데이터베이스 및 모델들
import os
from flask_migrate import Migrate
from sqlalchemy import create_engine  # 추가된 부분
from sqlalchemy.exc import OperationalError  # 추가된 부분

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# SQLAlchemy 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://gimpass2024:ehdud0116**@211.47.75.102:3306/dbgimpass2024'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 1800,  # 30분마다 연결 재활용
    'pool_size': 10,  # 연결 풀 크기 설정
    'max_overflow': 5,  # 최대 초과 연결 수 설정
    'connect_args': {"connect_timeout": 10}
}

# 데이터베이스 초기화
db.init_app(app)
migrate = Migrate(app, db)

# 블루프린트 등록
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(views_bp, url_prefix='/views')

# 모든 요청을 HTTPS로 리디렉션하는 함수
@app.before_request
def before_request():
    scheme = request.headers.get('X-Forwarded-Proto')
    if scheme and scheme == 'http' and request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

@app.route('/')
def index():
    return render_template('login.html')

# 데이터베이스 초기화 함수
def initialize_database():
    with app.app_context():
        print("Initializing the database...")
        db.create_all()  # 기존 데이터베이스에 테이블을 만듭니다.
        print("Database initialized.")

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True, host='0.0.0.0', port=8081)
