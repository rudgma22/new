from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, add_student, add_teacher, Student, Teacher
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    user = None
    if role == 'student':
        user = Student.query.filter_by(username=username).first()
    elif role == 'teacher':
        user = Teacher.query.filter_by(username=username).first()

    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        session['user_id'] = user.id
        session['role'] = role
        if role == 'student':
            return redirect(url_for('views.student_home'))
        else:
            return redirect(url_for('views.teacher_manage'))
    else:
        flash('Invalid credentials')
        return redirect(url_for('auth.index'))

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

        # Check if username already exists
        if Student.query.filter_by(username=username).first() or Teacher.query.filter_by(username=username).first():
            flash('The username already exists. Please use a different username.')
            return redirect(url_for('auth.register'))

        if role == 'student':
            name = request.form['name']
            grade = request.form['grade']
            student_class = request.form['student_class']
            number = request.form['number']
            barcode = request.form['barcode']

            # 바코드 중복 확인
            existing_student = Student.query.filter_by(barcode=barcode).first()
            if existing_student:
                flash('The barcode already exists. Please use a different barcode.')
                return redirect(url_for('auth.register'))

            add_student(name, grade, student_class, number, username, password, barcode)

        elif role == 'teacher':
            name = request.form['name']
            grade = request.form['grade']
            teacher_class = request.form['teacher_class']
            add_teacher(name, grade, teacher_class, username, password)

        elif role == 'admin':
            name = request.form['name']
            # 필요한 추가 필드 처리
            add_teacher(name, "", "", username, password)  # 예시로, 추가 필드를 처리하지 않음

        return redirect(url_for('auth.index'))

    return render_template('register.html')
