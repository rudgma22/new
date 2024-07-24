from flask import Blueprint, render_template, request, redirect, url_for, session
from sqlalchemy.sql import text
from models import get_db_connection, add_outing_request, approve_outing_request

views_bp = Blueprint('views', __name__)

@views_bp.route('/student_home')
def student_home():
    if 'user_id' in session and session['role'] == 'student':
        conn = get_db_connection()
        student = conn.execute(text('SELECT * FROM students WHERE id = :id'), {'id': session['user_id']}).fetchone()
        outing_requests = conn.execute(text('SELECT * FROM outing_requests WHERE student_name = :name'), {'name': student['name']}).fetchall()
        conn.close()
        return render_template('student_home.html', student=student, outing_requests=outing_requests)
    else:
        return redirect(url_for('auth.index'))

@views_bp.route('/teacher_manage')
def teacher_manage():
    if 'user_id' in session and session['role'] == 'teacher':
        conn = get_db_connection()
        teacher = conn.execute(text('SELECT * FROM teachers WHERE id = :id'), {'id': session['user_id']}).fetchone()
        requests = conn.execute(text('SELECT * FROM outing_requests WHERE student_name IN (SELECT name FROM students WHERE grade = :grade AND student_class = :class)'),
                                {'grade': teacher['grade'], 'class': teacher['teacher_class']}).fetchall()
        conn.close()
        return render_template('student_manage.html', requests=requests)
    else:
        return redirect(url_for('auth.index'))

@views_bp.route('/apply_leave', methods=['POST'])
def apply_leave():
    if 'user_id' in session and session['role'] == 'student':
        student_id = session['user_id']
        start_time = request.form['out_time']
        end_time = request.form['in_time']
        reason = request.form['reason']
        if reason == '기타':
            other_reason = request.form['other_reason']
            reason = f'기타({other_reason})'

        conn = get_db_connection()
        student = conn.execute(text('SELECT name FROM students WHERE id = :id'), {'id': student_id}).fetchone()
        add_outing_request(student['name'], start_time, end_time, reason)
        conn.close()
        return redirect(url_for('views.student_home'))
    else:
        return redirect(url_for('auth.index'))

@views_bp.route('/approve_leave/<int:request_id>', methods=['POST'])
def approve_leave(request_id):
    if 'user_id' in session and session['role'] == 'teacher':
        approve_outing_request(request_id)
        return redirect(url_for('views.teacher_manage'))
    else:
        return redirect(url_for('auth.index'))
