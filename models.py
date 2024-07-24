import sqlite3

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def add_student(name, grade, student_class, number, username, password, barcode):
    conn = get_db_connection()
    conn.execute('INSERT INTO students (name, grade, class, number, username, password, barcode) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (name, grade, student_class, number, username, password, barcode))
    conn.commit()
    conn.close()

def add_teacher(name, grade, teacher_class, username, password):
    conn = get_db_connection()
    conn.execute('INSERT INTO teachers (name, grade, class, username, password) VALUES (?, ?, ?, ?, ?)',
                 (name, grade, teacher_class, username, password))
    conn.commit()
    conn.close()

def add_outing_request(student_name, start_time, end_time, reason):
    conn = get_db_connection()
    conn.execute('INSERT INTO outing_requests (student_name, start_time, end_time, reason, status) VALUES (?, ?, ?, ?, ?)',
                 (student_name, start_time, end_time, reason, '대기'))
    conn.commit()
    conn.close()

def approve_outing_request(request_id):
    conn = get_db_connection()
    conn.execute('UPDATE outing_requests SET status = ? WHERE id = ?', ('승인', request_id))
    conn.commit()
    conn.close()
