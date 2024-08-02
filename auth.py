from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, add_student, add_teacher, add_admin, Student, Teacher, Admin
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

        if role == 'student':
            name = request.form['student_name']
        elif role == 'teacher':
            name = request.form['teacher_name']
        elif role == 'admin':
            name = request.form['admin_name']

        if Student.query.filter_by(username=username).first() or Teacher.query.filter_by(username=username).first() or Admin.query.filter_by(username=username).first():
            flash('The username already exists. Please use a different username.')
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

            add_student(name, grade, student_class, number, username, password, barcode)

        elif role == 'teacher':
            grade = request.form['grade']
            teacher_class = request.form['teacher_class']
            add_teacher(name, grade, teacher_class, username, password)

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
        return render_template('reset_password.html', username=username)
    else:
        flash('해당 정보로 계정을 찾을 수 없습니다.')
        return redirect(url_for('auth.find_id_reset_password'))

@auth_bp.route('/reset_password_confirm', methods=['POST'])
def reset_password_confirm():
    username = request.form['username']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if new_password != confirm_password:
        flash('비밀번호가 일치하지 않습니다.')
        return redirect(url_for('auth.find_id_reset_password'))

    user = Student.query.filter_by(username=username).first() or Teacher.query.filter_by(username=username).first()

    if user:
        user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.session.commit()
        return render_template('reset_result.html')
    else:
        flash('해당 아이디를 찾을 수 없습니다.')
        return redirect(url_for('auth.find_id_reset_password'))
