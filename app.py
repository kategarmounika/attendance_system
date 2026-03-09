from flask import Flask, render_template, request, redirect, session
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template, request, redirect, session, send_file
from werkzeug.security import check_password_hash
import sqlite3
from datetime import date
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

app = Flask(__name__)
app.secret_key = "attendance_secret_key"


# ---------------- DATABASE ----------------
import sqlite3

def connect_db():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row   # VERY IMPORTANT
    return conn


# ---------------- LOGIN ----------------
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "attendance_secret"

@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == "POST":

        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin":
            session['user'] = username
            return redirect(url_for('report'))
        else:
            return "Invalid Username or Password"

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------
@app.route('/')
def index():

    conn = connect_db()

    students = conn.execute("SELECT * FROM students").fetchall()

    total_students = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    present_today = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE status='Present'"
    ).fetchone()[0]

    absent_today = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE status='Absent'"
    ).fetchone()[0]

    total_attendance = conn.execute(
        "SELECT COUNT(*) FROM attendance"
    ).fetchone()[0]

    # ✅ Attendance Percentage
    attendance_percentage = 0
    if total_students > 0:
        attendance_percentage = round(
            (present_today / total_students) * 100, 2
        )


    # ✅ CHART CODE
    present = present_today
    absent = absent_today

    labels = ['Present', 'Absent']
    values = [present, absent]

    plt.figure(figsize=(4,4))
    plt.pie(values, labels=labels, autopct='%1.1f%%')
    plt.title("Attendance")

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    chart = base64.b64encode(img.getvalue()).decode()
    plt.close()


    conn.close()

    return render_template(
        "index.html",
        students=students,
        total_students=total_students,
        present_today=present_today,
        absent_today=absent_today,
        attendance_percentage=attendance_percentage,
        total_attendance=total_attendance,
        chart=chart
    )
# ---------------- ADD STUDENT ----------------
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


# ---------------- MARK ATTENDANCE ----------------
from datetime import date

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    student_id = request.form.get('student_id')
    status = request.form.get('status')

    today = str(date.today())

    conn = connect_db()

    # Delete existing record for today (avoid duplicates)
    conn.execute(
        "DELETE FROM attendance WHERE student_id=? AND date=?",
        (student_id, today)
    )

    # Insert new attendance
    conn.execute(
        "INSERT INTO attendance (student_id, status, date) VALUES (?, ?, ?)",
        (student_id, status, today)
    )

    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit(id):

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        date = request.form["date"]
        status = request.form["status"]

        cursor.execute(
        "UPDATE attendance SET student=?, date=?, status=? WHERE id=?",
        (name, date, status, id)
        )

        conn.commit()
        conn.close()

        return redirect("/")

    cursor.execute("SELECT * FROM attendance WHERE id=?", (id,))
    student = cursor.fetchone()
    conn.close()

    return render_template("edit.html", student=student)
@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):

    conn = connect_db()

    if request.method == 'POST':
        name = request.form['name']

        conn.execute(
            "UPDATE students SET name=? WHERE id=?",
            (name, id)
        )

        conn.commit()
        conn.close()

        return redirect('/')

    student = conn.execute(
        "SELECT * FROM students WHERE id=?",
        (id,)
    ).fetchone()

    conn.close()

    return render_template("edit_student.html", student=student)

@app.route('/delete_student/<int:id>')
def delete_student(id):

    conn = connect_db()

    conn.execute(
        "DELETE FROM students WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect('/')

# ---------------- REPORT ----------------
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

        percentage = round((present / total) * 100, 2) if total > 0 else 0

        report_data.append({
            'name': student['name'],
            'roll_no': student['roll_no'],
            'percentage': percentage
        })

    conn.close()
    return render_template('report.html', report_data=report_data)


# ---------------- DOWNLOAD PDF ----------------
@app.route('/download_report')
def download_report():
    if 'user' not in session:
        return redirect('/login')

    conn = connect_db()
    students = conn.execute("SELECT * FROM students").fetchall()

    report_data = [["Name", "Roll No", "Attendance %"]]

    for student in students:
        total = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=?",
            (student['id'],)
        ).fetchone()[0]

        present = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'",
            (student['id'],)
        ).fetchone()[0]

        percentage = round((present / total) * 100, 2) if total > 0 else 0

        report_data.append([
            student['name'],
            student['roll_no'],
            str(percentage) + " %"
        ])

    conn.close()

    file_path = "attendance_report.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    elements = []

    style = getSampleStyleSheet()
    elements.append(Paragraph("Attendance Report", style['Heading1']))
    elements.append(Spacer(1, 20))

    table = Table(report_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    return send_file(file_path, as_attachment=True)

@app.route('/monthly_report')
def monthly_report():
    if 'user' not in session:
        return redirect('/login')

    month = request.args.get('month')

    if not month:
        return render_template("monthly_report.html", report=None)

    conn = connect_db()
    students = conn.execute("SELECT * FROM students").fetchall()

    report = []

    for student in students:
        total_days = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=? AND date LIKE ?",
            (student['id'], month + "%")
        ).fetchone()[0]

        present_days = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present' AND date LIKE ?",
            (student['id'], month + "%")
        ).fetchone()[0]

        percentage = 0
        if total_days > 0:
            percentage = round((present_days / total_days) * 100, 2)

        report.append({
            'name': student['name'],
            'roll_no': student['roll_no'],
            'total_days': total_days,
            'present_days': present_days,
            'percentage': percentage
        })

    conn.close()

    return render_template(
        "monthly_report.html",
        report=report,
        selected_month=month
    )
from openpyxl import Workbook
from flask import send_file
import io

@app.route('/download_monthly_excel')
def download_monthly_excel():
    if 'user' not in session:
        return redirect('/login')

    month = request.args.get('month')

    if not month:
        return redirect('/monthly_report')

    conn = connect_db()
    students = conn.execute("SELECT * FROM students").fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Monthly Report"

    # Header Row
    ws.append(["Name", "Roll No", "Total Days", "Present Days", "Attendance %"])

    for student in students:
        total_days = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=? AND date LIKE ?",
            (student['id'], month + "%")
        ).fetchone()[0]

        present_days = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present' AND date LIKE ?",
            (student['id'], month + "%")
        ).fetchone()[0]

        percentage = 0
        if total_days > 0:
            percentage = round((present_days / total_days) * 100, 2)

        ws.append([
            student['name'],
            student['roll_no'],
            total_days,
            present_days,
            percentage
        ])

    conn.close()

    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name=f"Monthly_Report_{month}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
@app.route('/student_history/<int:student_id>')
def student_history(student_id):
    if 'user' not in session:
        return redirect('/login')

    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    conn = connect_db()

    student = conn.execute(
        "SELECT * FROM students WHERE id=?",
        (student_id,)
    ).fetchone()

    if from_date and to_date:
        records = conn.execute(
            """SELECT date, status FROM attendance
               WHERE student_id=? AND date >= ? AND date <= ?
               ORDER BY date DESC""",
            (student_id, from_date, to_date)
        ).fetchall()
    else:
        records = conn.execute(
            "SELECT date, status FROM attendance WHERE student_id=? ORDER BY date DESC",
            (student_id,)
        ).fetchall()

    # ✅ Calculation
    total_days = len(records)
    present_days = sum(1 for r in records if r['status'] == 'Present')
    absent_days = sum(1 for r in records if r['status'] == 'Absent')

    percentage = 0
    if total_days > 0:
        percentage = round((present_days / total_days) * 100, 2)

    conn.close()

    return render_template(
        "student_history.html",
        student=student,
        records=records,
        total_days=total_days,
        present_days=present_days,
        absent_days=absent_days,
        percentage=percentage,
        from_date=from_date,
        to_date=to_date
    )
# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)