from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from models import get_db_connection, add_student, add_teacher
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

    conn = get_db_connection()
    if role == 'student':
        user = conn.execute('SELECT * FROM students WHERE username = ?', (username,)).fetchone()
    else:
        user = conn.execute('SELECT * FROM teachers WHERE username = ?', (username,)).fetchone()

    conn.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        session['user_id'] = user['id']
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
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())

        if role == 'student':
            name = request.form['student_name']
            grade = request.form['grade']
            student_class = request.form['class']
            number = request.form['student_id']
            barcode = request.form['barcode']
            add_student(name, grade, student_class, number, username, password, barcode)

        elif role == 'teacher':
            name = request.form['teacher_name']
            grade = request.form['teacher_grade']
            teacher_class = request.form['teacher_class']
            add_teacher(name, grade, teacher_class, username, password)

        return redirect(url_for('auth.index'))

    return render_template('register.html')
