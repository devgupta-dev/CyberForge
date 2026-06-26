from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            score INTEGER DEFAULT 0
        )
    """)

    # CHALLENGES
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            category TEXT,
            difficulty TEXT,
            points INTEGER,
            flag TEXT
        )
    """)

    # SOLVES
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            challenge_id INTEGER
        )
    """)

    # INSERT SAMPLE CHALLENGES
    cursor.execute("SELECT * FROM challenges")

    if not cursor.fetchall():

        challenges = [

            (
                "Weak Password",
                "The admin uses a weak password. Find the flag.",
                "Web",
                "Easy",
                100,
                "flag{easy_password}"
            ),

            (
                "Hidden File",
                "A secret file exists on the server.",
                "Linux",
                "Easy",
                150,
                "flag{hidden_linux_file}"
            ),

            (
                "Base64 Challenge",
                "Decode this string: ZmxhZ3tiYXNlNjRfZGVjb2RlZH0=",
                "Crypto",
                "Easy",
                120,
                "flag{base64_decoded}"
            ),

            (
                "Admin Panel",
                "An admin panel is hidden somewhere.",
                "Web",
                "Medium",
                200,
                "flag{hidden_admin_panel}"
            ),

            (
                "Suspicious Traffic",
                "Analyze the packet capture.",
                "Forensics",
                "Medium",
                250,
                "flag{suspicious_dns}"
            ),

            (
                "Broken Hash",
                "Crack the MD5 hash: 5f4dcc3b5aa765d61d8327deb882cf99",
                "Crypto",
                "Easy",
                100,
                "flag{password}"
            )
        ]

        cursor.executemany("""
            INSERT INTO challenges
            (title, description, category, difficulty, points, flag)
            VALUES (?, ?, ?, ?, ?, ?)
        """, challenges)

    conn.commit()
    conn.close()


init_db()


# ---------------- HOME ----------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()

        try:

            cursor.execute("""
                INSERT INTO users (username, password)
                VALUES (?, ?)
            """, (username, hashed_password))

            conn.commit()

        except:
            return "Username already exists"

        conn.close()

        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users
            WHERE username=?
        """, (username,))

        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user"] = username

            return redirect("/dashboard")

        else:
            return "Invalid login"

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM users
        WHERE username=?
    """, (session["user"],))

    user = cursor.fetchone()

    # RANK SYSTEM
    score = user["score"]

    if score >= 1000:
        rank = "Legend"

    elif score >= 700:
        rank = "Elite"

    elif score >= 400:
        rank = "Operator"

    elif score >= 200:
        rank = "Analyst"

    else:
        rank = "Recruit"

    # SOLVED CHALLENGES
    cursor.execute("""
        SELECT challenge_id
        FROM solves
        WHERE username=?
    """, (session["user"],))

    solved_rows = cursor.fetchall()

    solved_ids = []

    for row in solved_rows:
        solved_ids.append(row["challenge_id"])

    # GET ALL CHALLENGES
    cursor.execute("""
        SELECT * FROM challenges
    """)

    challenges = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        challenges=challenges,
        rank=rank,
        solved_ids=solved_ids
    )


# ---------------- CHALLENGE ----------------

@app.route("/challenge/<int:challenge_id>", methods=["GET", "POST"])
def challenge(challenge_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM challenges
        WHERE id=?
    """, (challenge_id,))

    challenge = cursor.fetchone()

    message = ""

    # CHECK IF ALREADY SOLVED
    cursor.execute("""
        SELECT * FROM solves
        WHERE username=? AND challenge_id=?
    """, (session["user"], challenge_id))

    solved = cursor.fetchone()

    if request.method == "POST":

        answer = request.form["answer"]

        if solved:

            message = "Already solved."

        elif answer == challenge["flag"]:

            cursor.execute("""
                INSERT INTO solves (username, challenge_id)
                VALUES (?, ?)
            """, (session["user"], challenge_id))

            cursor.execute("""
                UPDATE users
                SET score = score + ?
                WHERE username=?
            """, (
                challenge["points"],
                session["user"]
            ))

            conn.commit()

            message = f"Correct! +{challenge['points']} points"

        else:

            message = "Incorrect flag"

    conn.close()

    return render_template(
        "challenge.html",
        challenge=challenge,
        message=message,
        solved=solved
    )


# ---------------- LEADERBOARD ----------------

@app.route("/leaderboard")
def leaderboard():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, score
        FROM users
        ORDER BY score DESC
    """)

    users = cursor.fetchall()

    conn.close()

    return render_template(
        "leaderboard.html",
        users=users
    )


# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)