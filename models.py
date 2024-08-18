from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.String(80), nullable=False)
    student_class = db.Column(db.String(80), nullable=False)
    number = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    barcode = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.String(80), nullable=False)
    teacher_class = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class OutingRequest(db.Model):
    __tablename__ = 'outing_requests'
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(80), nullable=False)
    barcode = db.Column(db.String(80), nullable=False)  # 바코드 필드 추가
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(80), default='대기중', nullable=False)
    rejection_reason = db.Column(db.String(200), nullable=True)

def get_db_connection():
    return db.session

def add_student(name, grade, student_class, number, username, password, barcode, email):
    new_student = Student(
        name=name,
        grade=grade,
        student_class=student_class,
        number=number,
        username=username,
        password=password,
        barcode=barcode,
        email=email
    )
    db.session.add(new_student)
    db.session.commit()

def add_teacher(name, grade, teacher_class, username, password, email):
    new_teacher = Teacher(
        name=name,
        grade=grade,
        teacher_class=teacher_class,
        username=username,
        password=password,
        email=email
    )
    db.session.add(new_teacher)
    db.session.commit()

def add_admin(name, username, password):
    new_admin = Admin(
        name=name,
        username=username,
        password=password
    )
    db.session.add(new_admin)
    db.session.commit()

def add_outing_request(student_name, barcode, start_time, end_time, reason):
    new_request = OutingRequest(
        student_name=student_name,
        barcode=barcode,
        start_time=start_time,
        end_time=end_time,
        reason=reason,
        status='대기중'
    )
    db.session.add(new_request)
    db.session.commit()

def approve_outing_request(request_id):
    request = OutingRequest.query.get(request_id)
    if request:
        request.status = '승인됨'
        db.session.commit()

def reject_outing_request(request_id, rejection_reason):
    request = OutingRequest.query.get(request_id)
    if request:
        request.status = '거절됨'
        request.rejection_reason = rejection_reason
        db.session.commit()

def get_outing_statistics():
    return db.session.query(
        Student.grade, Student.student_class, func.count(OutingRequest.id)
    ).join(OutingRequest, Student.name == OutingRequest.student_name)\
    .filter(OutingRequest.status == '승인됨')\
    .group_by(Student.grade, Student.student_class).all()

def initialize_database():
    db.drop_all()
    db.create_all()

if __name__ == '__main__':
    from app import app
    with app.app_context():
        initialize_database()
