# reset_table.py

from app import create_app, db  # Flask 애플리케이션과 데이터베이스 객체 임포트
from models import Extern  # 초기화하려는 테이블의 모델 임포트

app = create_app()

# Flask 애플리케이션 컨텍스트에서 실행하기 위한 작업
with app.app_context():
    try:
        print("Initializing the database...")

        # 특정 테이블 데이터 삭제
        db.session.query(Extern).delete()
        db.session.commit()

        print("Database initialized.")
    except Exception as e:
        db.session.rollback()  # 예외 발생 시 롤백
        print(f"테이블 초기화 중 오류가 발생했습니다: {e}")
