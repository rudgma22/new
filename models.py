from flask_sqlalchemy import SQLAlchemy

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

class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.String(80), nullable=False)
    teacher_class = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class OutingRequest(db.Model):
    __tablename__ = 'outing_requests'
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(80), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(80), default='대기중', nullable=False)

def get_db_connection():
    return db.session

def add_student(name, grade, student_class, number, username, password, barcode):
    new_student = Student(
        name=name,
        grade=grade,
        student_class=student_class,
        number=number,
        username=username,
        password=password,
        barcode=barcode
    )
    db.session.add(new_student)
    db.session.commit()

def add_teacher(name, grade, teacher_class, username, password):
    new_teacher = Teacher(
        name=name,
        grade=grade,
        teacher_class=teacher_class,
        username=username,
        password=password
    )
    db.session.add(new_teacher)
    db.session.commit()

def add_outing_request(student_name, start_time, end_time, reason):
    new_request = OutingRequest(
        student_name=student_name,
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
