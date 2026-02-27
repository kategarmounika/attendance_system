from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "attendance_secret_key"


# -------------------- DATABASE CONNECTION --------------------
def connect_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# -------------------- HOME / DASHBOARD --------------------
@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')

    conn = connect_db()

    search = request.args.get('search')

    if search:
        students = conn.execute(
            "SELECT * FROM students WHERE name LIKE ? OR roll_no LIKE ?",
            ('%' + search + '%', '%' + search + '%')
        ).fetchall()
    else:
        students = conn.execute("SELECT * FROM students").fetchall()

    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_attendance = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    present_today = conn.execute("SELECT COUNT(*) FROM attendance WHERE status='Present'").fetchone()[0]
    absent_today = conn.execute("SELECT COUNT(*) FROM attendance WHERE status='Absent'").fetchone()[0]

    total_today = present_today + absent_today
    if total_today > 0:
        attendance_percentage = round((present_today / total_today) * 100, 2)
    else:
        attendance_percentage = 0

    # Chart
    labels = ['Present', 'Absent']
    values = [present_today, absent_today]

    plt.figure(figsize=(5, 5))

    if total_today == 0:
        plt.text(0.5, 0.5, "No Attendance Data",
                 horizontalalignment='center',
                 verticalalignment='center',
                 fontsize=14)
    else:
        plt.pie(values, labels=labels, autopct='%1.1f%%')

    plt.title("Today's Attendance")
    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    chart = base64.b64encode(img.getvalue()).decode()
    plt.close()

    conn.close()

    return render_template(
        'index.html',
        students=students,
        total_students=total_students,
        total_attendance=total_attendance,
        present_today=present_today,
        absent_today=absent_today,
        attendance_percentage=attendance_percentage,
        chart=chart
    )


# -------------------- ADD STUDENT --------------------
@app.route('/add', methods=['GET', 'POST'])
def add_student():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        roll = request.form['roll']

        conn = connect_db()
        conn.execute(
            "INSERT INTO students (name, roll_no) VALUES (?, ?)",
            (name, roll)
        )
        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('add_student.html')


# -------------------- MARK ATTENDANCE --------------------
@app.route('/mark', methods=['GET', 'POST'])
def mark_attendance():
    if 'user' not in session:
        return redirect('/login')

    conn = connect_db()

    if request.method == 'POST':
        students = conn.execute("SELECT * FROM students").fetchall()

        for student in students:
            status = request.form.get(f"status_{student['id']}")

            conn.execute(
                "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                (student['id'], str(date.today()), status)
            )

        conn.commit()
        conn.close()

        return redirect('/report')

    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    return render_template('mark_attendance.html', students=students)

# -------------------- REPORT --------------------
@app.route('/report')
def report():
    if 'user' not in session:
        return redirect('/login')

    conn = connect_db()
    students = conn.execute("SELECT * FROM students").fetchall()

    report_data = []

    for student in students:
        total = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=?",
            (student['id'],)
        ).fetchone()[0]

        present = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'",
            (student['id'],)
        ).fetchone()[0]

        percentage = 0
        if total > 0:
            percentage = round((present / total) * 100, 2)

        report_data.append({
            'name': student['name'],
            'roll_no': student['roll_no'],
            'total': total,
            'present': present,
            'percentage': percentage
        })

    conn.close()

    return render_template('report.html', report_data=report_data)


# -------------------- DOWNLOAD PDF --------------------
@app.route('/download_report')
def download_report():
    if 'user' not in session:
        return redirect('/login')

    conn = connect_db()
    students = conn.execute("SELECT * FROM students").fetchall()

    data = [["Name", "Roll No", "Total", "Present", "Percentage"]]

    for student in students:
        total = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=?",
            (student['id'],)
        ).fetchone()[0]

        present = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'",
            (student['id'],)
        ).fetchone()[0]

        percentage = 0
        if total > 0:
            percentage = round((present / total) * 100, 2)

        data.append([
            student['name'],
            student['roll_no'],
            total,
            present,
            str(percentage) + "%"
        ])

    conn.close()

    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    file_path = "attendance_report.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=letter)

    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Attendance Report", styles['Heading1']))
    elements.append(Spacer(1, 20))

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    return redirect('/report')

# -------------------- LOGIN --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Simple hardcoded login
        if username == "admin" and password == "admin":
            session['user'] = username
            return redirect('/')
        else:
            return "Invalid Credentials"

    return render_template('login.html')


# -------------------- LOGOUT --------------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')
# -------------------- DATABASE INIT --------------------
if __name__ == "__main__":
    conn = connect_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll_no TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()

    app.run(debug=True)
