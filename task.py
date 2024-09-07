from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from models import db, Extern

def clear_externs_table():
    print("Externs 테이블 초기화 중...")
    try:
        Extern.query.delete()  # 테이블의 모든 행 삭제
        db.session.commit()
        print("Externs 테이블이 성공적으로 초기화되었습니다.")
    except Exception as e:
        db.session.rollback()
        print(f"Externs 테이블 초기화 중 오류 발생: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    # 매주 일요일 22시 30분에 clear_externs_table 실행
    scheduler.add_job(clear_externs_table, 'cron', day_of_week='sun', hour=22, minute=30)
    scheduler.start()

# 앱 시작 시 스케줄러 실행
start_scheduler()
