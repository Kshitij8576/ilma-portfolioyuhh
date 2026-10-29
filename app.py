
from flask import Flask, render_template, request
from werkzeug.security import generate_password_hash
import sqlite3

app = Flask(__name__)

DATABASE = "placement.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            course TEXT,
            skills TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            required_skills TEXT,
            minimum_cgpa REAL,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Pending',
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, job_id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    # Add a sample company if it doesn't exist
    cursor.execute(
        "SELECT id FROM companies WHERE name = ?",
        ("PlaceMate Careers",)
    )
    company = cursor.fetchone()

    if company is None:
        cursor.execute(
            "INSERT INTO companies (name, description) VALUES (?, ?)",
            ("PlaceMate Careers", "Student placement opportunities")
        )
        company_id = cursor.lastrowid
    else:
        company_id = company["id"]

    # Add sample jobs without creating duplicates
    jobs = [
        ("Web Developer", "Create and maintain websites",
         "HTML, CSS, JavaScript", 6.0),
        ("Data Analyst", "Analyze data and prepare reports",
         "Excel, SQL, Python", 6.0),
        ("Python Developer", "Build applications using Python",
         "Python, Flask, SQL", 6.0)
    ]

    for title, description, skills, cgpa in jobs:
        cursor.execute(
            "SELECT id FROM jobs WHERE title = ?",
            (title,)
        )

        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO jobs
                (company_id, title, description, required_skills, minimum_cgpa)
                VALUES (?, ?, ?, ?, ?)
            """, (company_id, title, description, skills, cgpa))

    connection.commit()
    connection.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        course = request.form.get("course", "").strip()
        skills = request.form.get("skills", "").strip()

        if not name or not email or not password:
            return "Please fill in your name, email, and password."

        hashed_password = generate_password_hash(password)
        connection = get_db_connection()

        try:
            connection.execute("""
                INSERT INTO students
                (name, email, password, course, skills)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, hashed_password, course, skills))

            connection.commit()
            return "Registration successful! You can now apply for jobs."

        except sqlite3.IntegrityError:
            return "This email is already registered. Please use another email."

        finally:
            connection.close()

    return render_template("register.html")


@app.route("/apply", methods=["POST"])
def apply():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    job_title = request.form.get("job_title", "").strip()

    if not name or not email or not job_title:
        return "Please provide your name, email, and selected job."

    connection = get_db_connection()

    try:
        student = connection.execute(
            "SELECT id, name FROM students WHERE email = ?",
            (email,)
        ).fetchone()

        if student is None:
            return "Please register first using this email address."

        if student["name"].strip().lower() != name.lower():
            return "The name does not match this registered email."

        job = connection.execute(
            "SELECT id FROM jobs WHERE title = ?",
            (job_title,)
        ).fetchone()

        if job is None:
            return "This job was not found in the database."

        connection.execute("""
            INSERT INTO applications (student_id, job_id)
            VALUES (?, ?)
        """, (student["id"], job["id"]))

        connection.commit()
        return "Application submitted successfully!"

    except sqlite3.IntegrityError:
        return "You have already applied for this job."

    finally:
        connection.close()


@app.route("/my-applications")
def my_applications():
    # Temporary demo view: enter a registered student's email
    email = request.args.get("email", "").strip().lower()
    applications = []
    error = ""

    if email:
        connection = get_db_connection()

        student = connection.execute(
            "SELECT id, name FROM students WHERE email = ?",
            (email,)
        ).fetchone()

        if student:
            applications = connection.execute("""
                SELECT jobs.title, jobs.description,
                       applications.status, applications.applied_at
                FROM applications
                JOIN jobs ON applications.job_id = jobs.id
                WHERE applications.student_id = ?
                ORDER BY applications.applied_at DESC
            """, (student["id"],)).fetchall()
        else:
            error = "No registered student found with that email."

        connection.close()

    return render_template(
        "my_applications.html",
        applications=applications,
        email=email,
        error=error
    )


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
