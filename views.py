from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy.sql import text
from models import get_db_connection, add_outing_request, approve_outing_request, OutingRequest, db

views_bp = Blueprint('views', __name__)


def row_to_dict(row):
    if row is None:
        return None
    return dict(row._mapping)


@views_bp.route('/student_home')
def student_home():
    if 'user_id' in session and session['role'] == 'student':
        conn = get_db_connection()
        student = conn.execute(text('SELECT * FROM students WHERE id = :id'), {'id': session['user_id']}).fetchone()
        student = row_to_dict(student)
        outing_requests = conn.execute(text('SELECT * FROM outing_requests WHERE student_name = :name'),
                                       {'name': student['name']}).fetchall()
        outing_requests = [row_to_dict(request) for request in outing_requests]
        conn.close()
        return render_template('student_home.html', student=student, outing_requests=outing_requests)
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/teacher_manage')
def teacher_manage():
    if 'user_id' in session and session['role'] == 'teacher':
        conn = get_db_connection()
        teacher = conn.execute(text('SELECT * FROM teachers WHERE id = :id'), {'id': session['user_id']}).fetchone()
        teacher = row_to_dict(teacher)
        requests = conn.execute(text(
            'SELECT * FROM outing_requests WHERE student_name IN (SELECT name FROM students WHERE grade = :grade AND student_class = :class)'),
                                {'grade': teacher['grade'], 'class': teacher['teacher_class']}).fetchall()
        requests = [row_to_dict(request) for request in requests]
        conn.close()
        return render_template('student_manage.html', teacher=teacher, requests=requests)
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/admin_page')
def admin_page():
    if 'user_id' in session and session['role'] == 'admin':
        return render_template('admin_page.html')
    else:
        return redirect(url_for('auth.index'))


@views_bp.route('/apply_leave', methods=['POST'])
def apply_leave():
    if 'user_id' in session and session['role'] == 'student':
        student_id = session['user_id']
        start_time = datetime.fromisoformat(request.form['out_time'])
        end_time = datetime.fromisoformat(request.form['in_time'])
        reason = request.form['reason']
        if reason == '기타':
            other_reason = request.form['other_reason']
            reason = f'기타({other_reason})'

        conn = get_db_connection()
        student = conn.execute(text('SELECT name FROM students WHERE id = :id'), {'id': student_id}).fetchone()
        student = row_to_dict(student)
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


@views_bp.route('/reject_leave/<int:request_id>', methods=['POST'])
def reject_leave(request_id):
    if 'user_id' in session and session['role'] == 'teacher':
        rejection_reason = request.form.get('rejection_reason', '').strip()
        if not rejection_reason:
            flash('거절 사유를 입력해주세요')
            return redirect(url_for('views.teacher_manage'))

        outing_request = OutingRequest.query.get(request_id)
        if outing_request:
            outing_request.status = '거절됨'
            outing_request.rejection_reason = rejection_reason
            db.session.commit()
        return redirect(url_for('views.teacher_manage'))
    else:
        return redirect(url_for('auth.index'))
