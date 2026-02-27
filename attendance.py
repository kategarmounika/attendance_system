import sqlite3
from datetime import date

# Connect to database
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    roll_no TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    attendance_date TEXT,
    status TEXT
)
""")

conn.commit()

def add_student():
    name = input("Enter student name: ")
    roll = input("Enter roll number: ")
    cursor.execute("INSERT INTO students (name, roll_no) VALUES (?, ?)", (name, roll))
    conn.commit()
    print("Student added successfully!\n")

def mark_attendance():
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()

    for student in students:
        print(f"{student[0]}. {student[1]} ({student[2]})")
        status = input("Present or Absent (P/A): ").upper()
        status = "Present" if status == "P" else "Absent"
        cursor.execute(
            "INSERT INTO attendance (student_id, attendance_date, status) VALUES (?, ?, ?)",
            (student[0], str(date.today()), status)
        )
    conn.commit()
    print("Attendance marked!\n")

def view_report():
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()

    for student in students:
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE student_id=?", (student[0],))
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'", (student[0],))
        present = cursor.fetchone()[0]

        percentage = (present / total * 100) if total > 0 else 0
        print(f"{student[1]} - Attendance: {percentage:.2f}%")

def main():
    while True:
        print("\n1. Add Student")
        print("2. Mark Attendance")
        print("3. View Report")
        print("4. Exit")

        choice = input("Choose option: ")

        if choice == "1":
            add_student()
        elif choice == "2":
            mark_attendance()
        elif choice == "3":
            view_report()
        elif choice == "4":
            break
        else:
            print("Invalid choice")

main()
conn.close()