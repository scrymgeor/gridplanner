import io
import hashlib
import random
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime, date, timedelta
from database import get_db, init_db
import models
import services

app = Flask(__name__)
app.secret_key = "gridos_secret_key_sem3_session"

init_db()
services.start_background_monitor()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def rebuild_schedule(user_id):
    conn = get_db()
    raw_tasks = conn.execute("SELECT * FROM tasks WHERE user_id = ? AND is_completed = 0", (user_id,)).fetchall()
    
    task_objs = []
    for t in raw_tasks:
        ttype = t['task_type'].upper()
        if ttype == 'FITNESS':
            task_objs.append(models.FitnessHabitTask(t['id'], t['title'], t['subject'], t['deadline'], 
                                                     t['estimated_hours'], t['priority'], t['specific_meta'], t['color_tag']))
        elif ttype == 'WORK':
            task_objs.append(models.WorkProjectTask(t['id'], t['title'], t['subject'], t['deadline'], 
                                                    t['estimated_hours'], t['priority'], t['specific_meta'], t['color_tag']))
        elif ttype == 'ACADEMIC':
            task_objs.append(models.AcademicTask(t['id'], t['title'], t['subject'], t['deadline'], 
                                                 t['estimated_hours'], t['priority'], t['specific_meta'], t['color_tag']))
        else:
            task_objs.append(models.GeneralTask(t['id'], t['title'], t['subject'], t['deadline'], 
                                                t['estimated_hours'], t['priority'], t['specific_meta'], t['color_tag']))

    raw_slots = conn.execute("SELECT * FROM free_slots WHERE user_id = ?", (user_id,)).fetchall()
    time_slots = []
    today = date.today()

    for i in range(7):
        cur_day = today + timedelta(days=i)
        day_idx = cur_day.weekday()
        for s in raw_slots:
            if s['day_of_week'] == day_idx:
                time_slots.append(models.TimeSlot(cur_day, s['start_hour'], s['duration_hours']))

    scheduler = models.AutoScheduler(task_objs, time_slots)
    new_blocks = scheduler.generate()

    conn.execute("DELETE FROM schedule WHERE user_id = ?", (user_id,))
    for b in new_blocks:
        conn.execute("""
            INSERT INTO schedule (user_id, task_id, task_title, subject, color_tag, session_date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, b['task_id'], b['task_title'], b['subject'], b['color_tag'], b['session_date'], b['start_time'], b['end_time']))

    conn.commit()
    all_scheduled = conn.execute("SELECT * FROM schedule WHERE user_id = ?", (user_id,)).fetchall()
    services.generate_analytics_chart([dict(r) for r in all_scheduled])
    conn.close()

# --- AUTH ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed = hash_password(password)

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, hashed)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            return redirect(url_for('index'))
        else:
            error = "Invalid username or password."
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not services.validate_email(email):
            return render_template('register.html', error="Invalid email format.")

        hashed = hash_password(password)
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", (username, email, hashed))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()

            session['user_id'] = user_id
            session['username'] = username
            session['email'] = email
            services.log_event(f"User created: {username}")
            return redirect(url_for('index'))
        except Exception:
            error = "Username or email is already registered."
            conn.close()

    return render_template('register.html', error=error)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = None
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        
        if user:
            otp = str(random.randint(100000, 999999))
            conn.execute("UPDATE users SET reset_token = ? WHERE email = ?", (otp, email))
            conn.commit()
            conn.close()

            services.send_reset_otp_email(email, otp)
            return render_template('reset_password.html', email=email)
        else:
            message = "Email address not found."
            conn.close()

    return render_template('forgot_password.html', message=message)

@app.route('/reset_password', methods=['POST'])
def reset_password():
    email = request.form['email']
    entered_otp = request.form['otp'].strip()
    new_password = request.form['new_password']

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ? AND reset_token = ?", (email, entered_otp)).fetchone()

    if user:
        new_hash = hash_password(new_password)
        conn.execute("UPDATE users SET password_hash = ?, reset_token = NULL WHERE email = ?", (new_hash, email))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    else:
        conn.close()
        return render_template('reset_password.html', email=email, error="Invalid code. Please try again.")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- DASHBOARD & ACTIONS (Protected) ---

@app.route('/')
@login_required
def index():
    user_id = session['user_id']
    conn = get_db()
    tasks = conn.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY is_completed ASC, deadline ASC", (user_id,)).fetchall()
    schedule = conn.execute("SELECT * FROM schedule WHERE user_id = ? ORDER BY session_date ASC, start_time ASC", (user_id,)).fetchall()
    slots = conn.execute("SELECT * FROM free_slots WHERE user_id = ?", (user_id,)).fetchall()
    habits = conn.execute("SELECT * FROM habits WHERE user_id = ?", (user_id,)).fetchall()
    today_str = date.today().strftime("%Y-%m-%d")
    conn.close()
    return render_template('index.html', tasks=tasks, schedule=schedule, slots=slots, habits=habits, today=today_str, username=session['username'])

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    user_id = session['user_id']
    title = request.form['title']
    subject = request.form['subject']
    task_type = request.form['task_type']
    deadline = request.form['deadline'].replace('T', ' ')
    hours = float(request.form['estimated_hours'])
    priority = int(request.form['priority'])
    meta = request.form['specific_meta']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (user_id, title, subject, task_type, deadline, estimated_hours, priority, specific_meta)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, title, subject, task_type, deadline, hours, priority, meta))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    services.undo_stack.push("ADD", new_id)
    rebuild_schedule(user_id)
    return redirect(url_for('index'))

@app.route('/add_habit', methods=['POST'])
@login_required
def add_habit():
    title = request.form['title']
    user_id = session['user_id']
    conn = get_db()
    conn.execute("INSERT INTO habits (user_id, title, streak, last_completed) VALUES (?, ?, 0, NULL)", (user_id, title))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/toggle_habit/<int:habit_id>')
@login_required
def toggle_habit(habit_id):
    user_id = session['user_id']
    conn = get_db()
    habit = conn.execute("SELECT * FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id)).fetchone()
    today_str = date.today().strftime("%Y-%m-%d")

    if habit and habit['last_completed'] != today_str:
        new_streak = habit['streak'] + 1
        conn.execute("UPDATE habits SET streak = ?, last_completed = ? WHERE id = ?", (new_streak, today_str, habit_id))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/complete/<int:task_id>')
@login_required
def complete(task_id):
    user_id = session['user_id']
    conn = get_db()
    conn.execute("UPDATE tasks SET is_completed = 1 WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    conn.close()
    rebuild_schedule(user_id)
    return redirect(url_for('index'))

@app.route('/undo')
@login_required
def undo():
    action = services.undo_stack.pop()
    if action:
        action_type, task_id = action
        if action_type == "ADD":
            conn = get_db()
            conn.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, session['user_id']))
            conn.commit()
            conn.close()
            rebuild_schedule(session['user_id'])
    return redirect(url_for('index'))

@app.route('/add_slot', methods=['POST'])
@login_required
def add_slot():
    user_id = session['user_id']
    conn = get_db()
    conn.execute("INSERT INTO free_slots (user_id, day_of_week, start_hour, duration_hours) VALUES (?, ?, ?, ?)",
                 (user_id, int(request.form['day_of_week']), int(request.form['start_hour']), float(request.form['duration'])))
    conn.commit()
    conn.close()
    rebuild_schedule(user_id)
    return redirect(url_for('index'))

@app.route('/export_csv')
@login_required
def export_csv():
    conn = get_db()
    schedule = conn.execute("SELECT * FROM schedule WHERE user_id = ? ORDER BY session_date, start_time", (session['user_id'],)).fetchall()
    conn.close()
    services.export_schedule_to_csv([dict(r) for r in schedule])
    return send_file("study_schedule.csv", as_attachment=True)

@app.route('/import_csv', methods=['POST'])
@login_required
def import_csv():
    file = request.files['file']
    user_id = session['user_id']
    if file:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        tasks = services.import_tasks_from_csv(stream)
        conn = get_db()
        for t in tasks:
            conn.execute("""
                INSERT INTO tasks (user_id, title, subject, task_type, deadline, estimated_hours, priority, specific_meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, t['title'], t['subject'], t['task_type'], t['deadline'], t['estimated_hours'], t['priority'], t['specific_meta']))
        conn.commit()
        conn.close()
        rebuild_schedule(user_id)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
