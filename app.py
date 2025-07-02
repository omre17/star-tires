from flask import Flask, render_template, request, redirect, session
from collections import defaultdict
from datetime import datetime
import sqlite3
from datetime import datetime
app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_user(username, password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    return user

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user(username, password)
        if user:
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect('/welcome')
        else:
            return render_template('login.html', error='שם משתמש או סיסמה שגויים')
    return render_template('login.html')

@app.route('/welcome')
def welcome():
    if 'role' not in session:
        return render_template('welcome.html', error='לא התקבלה הרשאה.')
    elif session['role'] == 'manager':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT username, action, timestamp FROM work_sessions ORDER BY timestamp")
        rows = c.fetchall()
        conn.close()

        

        work_data = defaultdict(list)

        # מחלקים את הרשומות לפי משתמש
        for username, action, timestamp in rows:
            work_data[username].append((action, timestamp))

        summary = []

        for username, actions in work_data.items():
            total_seconds = 0
            start_time = None

            for action, timestamp in actions:
                time_obj = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                if action == 'start':
                    start_time = time_obj
                elif action == 'end' and start_time:
                    total_seconds += (time_obj - start_time).total_seconds()
                    start_time = None

            hours = round(total_seconds / 3600, 2)
            summary.append((username, hours))

        return render_template('manager.html', sessions=rows, summary=summary)

    elif session['role'] == 'worker':
        return render_template('worker.html')
    else:
        return render_template('welcome.html', error='הרשאה לא תקינה.')

@app.route('/work', methods=['POST'])
def work():
    if 'username' not in session:
        return redirect('/')

    username = session['username']
    action = request.form['action']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO work_sessions (username, action) VALUES (?, ?)", (username, action))
    conn.commit()
    conn.close()

    msg = "הפעולה נרשמה בהצלחה בשעה {} עבור {}".format(
        datetime.now().strftime('%H:%M:%S'),
        "כניסה" if action == "start" else "יציאה"
    )

    # נחזיר את המשתמש חזרה לעמוד ניהול שעות עם הודעה
    return render_template('work_session.html', message=msg)

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'role' not in session or session['role'] != 'manager':
        return redirect('/')

    message = ''
    if request.method == 'POST':
        tire_type = request.form['tire_type']
        quantity = int(request.form['quantity'])

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # בדיקה אם הצמיג כבר קיים
        c.execute("SELECT id FROM inventory WHERE tire_type = ?", (tire_type,))
        existing = c.fetchone()

        if existing:
            # עדכון כמות
            c.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", (quantity, existing[0]))
            message = "עודכן בהצלחה"
        else:
            # הוספה חדשה
            c.execute("INSERT INTO inventory (tire_type, quantity) VALUES (?, ?)", (tire_type, quantity))
            message = "נוסף בהצלחה"

        conn.commit()
        conn.close()

    # שליפה להצגה
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT tire_type, quantity FROM inventory")
    inventory = c.fetchall()
    conn.close()

    return render_template('inventory.html', inventory=inventory, message=message)
@app.route('/payroll')
def payroll_view():
    if 'role' not in session or session['role'] != 'manager':
        return redirect('/')

    # סיכום שעות לפי משתמש
    from collections import defaultdict
    from datetime import datetime

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT username, action, timestamp FROM work_sessions ORDER BY timestamp")
    rows = c.fetchall()
    conn.close()

    work_data = defaultdict(list)
    for username, action, timestamp in rows:
        work_data[username].append((action, timestamp))

    summary = []
    for username, actions in work_data.items():
        total_seconds = 0
        start_time = None
        for action, timestamp in actions:
            time_obj = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            if action == 'start':
                start_time = time_obj
            elif action == 'end' and start_time:
                total_seconds += (time_obj - start_time).total_seconds()
                start_time = None
        hours = round(total_seconds / 3600, 2)
        summary.append((username, hours))

    # מחשבים שכר
    payroll = []
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    for username, hours in summary:
        c.execute("SELECT hourly_rate FROM users WHERE username = ?", (username,))
        rate = c.fetchone()
        rate = rate[0] if rate else 0
        total_pay = round(hours * rate, 2)
        payroll.append((username, hours, rate, total_pay))
    conn.close()

    return render_template('payroll.html', payroll=payroll)

@app.route('/worker_report')
def worker_report():
    username = session.get('username')
    if not username:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # שליפת פעולות לפי זמן
    c.execute("SELECT action, timestamp FROM work_sessions WHERE username = ? ORDER BY timestamp", (username,))
    rows = c.fetchall()

    # חישוב סה"כ שעות לפי זוגות כניסה/יציאה
    total_hours = 0
    start_time = None

    for action, timestamp in rows:
        if action == 'start':
            start_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        elif action == 'end' and start_time:
            end_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            total_hours += (end_time - start_time).total_seconds() / 3600
            start_time = None

    total_hours = round(total_hours, 2)

    # שליפת שכר לשעה
    c.execute("SELECT hourly_rate FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    hourly_rate = result[0] if result else 0

    total_pay = round(total_hours * hourly_rate, 2)

    conn.close()

    return render_template("worker_report.html",
                           sessions=rows,
                           total_hours=total_hours,
                           hourly_rate=hourly_rate,
                           total_pay=total_pay)

@app.route("/work-session")
def work_session():
    if 'username' not in session:
        return redirect("/login")
    return render_template("work_session.html")

if __name__ == '__main__':
    app.run(debug=True)

