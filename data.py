import pandas as pd
import bcrypt
from models import db, Student  # 같은 폴더에 있는 models.py에서 필요한 클래스 가져오기
from flask import Flask

# Flask 앱과 SQLAlchemy 설정
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://gimpass2024:ehdud0116**@211.47.75.102:3306/dbgimpass2024'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 1800,  # 30분마다 연결 재활용
    'pool_size': 10,  # 연결 풀 크기 설정
    'max_overflow': 5,  # 최대 초과 연결 수 설정
    'connect_args': {"connect_timeout": 10}
}

db.init_app(app)


def hash_password(password):
    """비밀번호를 bcrypt로 해시"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def load_data_from_excel(file_path):
    """Excel 파일에서 데이터를 로드하고 비밀번호를 해시하여 MySQL에 삽입"""
    df = pd.read_excel(file_path)

    # NaN 값을 None으로 변환하여 SQLAlchemy가 NULL로 처리하도록 함
    df = df.where(pd.notnull(df), None)

    with app.app_context():
        for index, row in df.iterrows():
            name = row['name']

            # grade, student_class, number에 학년, 반, 번호 추가
            grade = f"{row['grade']}학년"
            student_class = f"{row['student_class']}반"
            number = f"{row['number']}번"

            username = row['username']
            password = row['password']
            barcode = row['barcode']
            email = row['email'] or "default@example.com"  # email이 None이면 기본값 설정

            # 비밀번호 해시
            hashed_password = hash_password(password)

            # 중복된 username이 있는지 확인
            existing_student = Student.query.filter_by(username=username).first()
            if existing_student:
                print(f"중복된 username '{username}'이(가) 발견되었습니다. 건너뜁니다.")
                continue

            # 중복된 barcode가 있는지 확인
            existing_barcode = Student.query.filter_by(barcode=barcode).first()
            if existing_barcode:
                print(f"중복된 barcode '{barcode}'이(가) 발견되었습니다. 건너뜁니다.")
                continue

            # Student 객체 생성
            new_student = Student(
                name=name,
                grade=grade,
                student_class=student_class,
                number=number,
                username=username,
                password=hashed_password,
                barcode=barcode,
                email=email
            )

            # 데이터베이스에 추가
            db.session.add(new_student)

        # 변경 사항 커밋
        db.session.commit()
        print("데이터가 성공적으로 추가되었습니다.")


if __name__ == '__main__':
    excel_file_path = 'GCHS_student_data_2024.xlsx'  # 같은 폴더에 있는 엑셀 파일의 이름
    load_data_from_excel(excel_file_path)
