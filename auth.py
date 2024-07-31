from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, add_student, add_teacher, add_admin, Student, Teacher, Admin
import bcrypt
import random
import string
from flask_mail import Mail, Message

auth_bp = Blueprint('auth', __name__)

# Flask-Mail 설정
mail = Mail()

def send_verification_email(email, code):
    msg = Message('비밀번호 재설정 인증 코드', sender='mintdy09523@gmail.com', recipients=[email])
    msg.body = f'인증 코드는 {code}입니다.'
    mail.send(msg)

@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        user = None
        if role == 'student':
            user = Student.query.filter_by(username=username).first()
        elif role == 'teacher':
            user = Teacher.query.filter_by(username=username).first()
        elif role == 'admin':
            user = Admin.query.filter_by(username=username).first()

        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            session['user_id'] = user.id
            session['role'] = role
            if role == 'student':
                return redirect(url_for('views.student_home'))
            elif role == 'teacher':
                return redirect(url_for('views.teacher_manage'))
            elif role == 'admin':
                return redirect(url_for('views.admin_page'))
        else:
            flash('Invalid credentials')
            return redirect(url_for('auth.index'))
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        email = request.form['email']

        if role == 'student':
            name = request.form['student_name']
        elif role == 'teacher':
            name = request.form['teacher_name']
        elif role == 'admin':
            name = request.form['admin_name']

        if Student.query.filter_by(username=username).first() or Teacher.query.filter_by(username=username).first() or Admin.query.filter_by(username=username).first():
            flash('The username already exists. Please use a different username.')
            return redirect(url_for('auth.register'))

        if Student.query.filter_by(email=email).first() or Teacher.query.filter_by(email=email).first():
            flash('The email already exists. Please use a different email.')
            return redirect(url_for('auth.register'))

        if role == 'student':
            grade = request.form['grade']
            student_class = request.form['student_class']
            number = request.form['number']
            barcode = request.form['barcode']

            existing_student = Student.query.filter_by(barcode=barcode).first()
            if existing_student:
                flash('The barcode already exists. Please use a different barcode.')
                return redirect(url_for('auth.register'))

            add_student(name, grade, student_class, number, username, password, barcode, email)

        elif role == 'teacher':
            grade = request.form['grade']
            teacher_class = request.form['teacher_class']
            add_teacher(name, grade, teacher_class, username, password, email)

        elif role == 'admin':
            add_admin(name, username, password)

        return redirect(url_for('auth.index'))

    return render_template('register.html')

@auth_bp.route('/find_id_reset_password')
def find_id_reset_password():
    return render_template('find_id_reset_password.html')

@auth_bp.route('/find_id', methods=['POST'])
def find_id():
    role = request.form['role']
    name = request.form['name']
    grade = request.form['grade']
    student_class = request.form['class']
    number = request.form['number']

    if role == 'student':
        barcode = request.form['barcode']
        user = Student.query.filter_by(name=name, grade=grade, student_class=student_class, number=number, barcode=barcode).first()
    else:
        user = Teacher.query.filter_by(name=name, grade=grade, teacher_class=student_class).first()

    if user:
        return render_template('find_id.html', name=name, username=user.username)
    else:
        flash('해당 정보로 아이디를 찾을 수 없습니다.')
        return redirect(url_for('auth.find_id_reset_password'))

@auth_bp.route('/reset_password', methods=['POST'])
def reset_password():
    role = request.form['role']
    username = request.form['username']
    name = request.form['name']
    grade = request.form['grade']
    student_class = request.form['class']
    number = request.form['number']

    if role == 'student':
        barcode = request.form['barcode']
        user = Student.query.filter_by(username=username, name=name, grade=grade, student_class=student_class, number=number, barcode=barcode).first()
    else:
        user = Teacher.query.filter_by(username=username, name=name, grade=grade, teacher_class=student_class).first()

    if user:
        verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        session['verification_code'] = verification_code
        session['reset_username'] = username
        send_verification_email(user.email, verification_code)
        return redirect(url_for('auth.verify_code'))
    else:
        flash('해당 정보로 계정을 찾을 수 없습니다.')
        return redirect(url_for('auth.find_id_reset_password'))

@auth_bp.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        input_code = request.form['verification_code']
        if input_code == session.get('verification_code'):
            return redirect(url_for('auth.reset_password_form'))
        else:
            flash('인증 코드가 일치하지 않습니다.')
            return redirect(url_for('auth.verify_code'))
    return render_template('verify_code.html')

@auth_bp.route('/reset_password_form')
def reset_password_form():
    username = session.get('reset_username')
    if not username:
        flash('잘못된 접근입니다.')
        return redirect(url_for('auth.find_id_reset_password'))
    return render_template('reset_password.html', username=username)

@auth_bp.route('/reset_password_confirm', methods=['POST'])
def reset_password_confirm():
    username = request.form['username']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if new_password != confirm_password:
        flash('비밀번호가 일치하지 않습니다.')
        return redirect(url_for('auth.reset_password_form'))

    user = Student.query.filter_by(username=username).first() or Teacher.query.filter_by(username=username).first()

    if user:
        user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.session.commit()
        return render_template('reset_result.html')
    else:
        flash('해당 아이디를 찾을 수 없습니다.')
        return redirect(url_for('auth.find_id_reset_password'))
