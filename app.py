from flask import Flask, render_template, request, redirect, session, flash, jsonify
from datetime import datetime
import os
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=6543,
        sslmode="require",
        cursor_factory=RealDictCursor
    )

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (request.form["username"], request.form["password"])
        )

        user = cur.fetchone()

        print("HASIL QUERY:", user)
        if user:
             print("ROLE:", user["role"])
        print("USERNAME:", request.form["username"])
        print("PASSWORD:", request.form["password"])
        print("HASIL QUERY:", user)

        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin")

            elif user["role"] == "outlet":
                return redirect("/dashboard")

            elif user["role"] == "user":
                return redirect("/dashboard")

            else:
                return redirect("/")

        flash("Login gagal")

    return render_template("login.html")

@app.route("/cekuser")
def cekuser():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users")
    users = cur.fetchall()

    conn.close()

    return jsonify(users)

@app.route("/api/login", methods=["POST"])
def api_login():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (request.form.get("username"), request.form.get("password"))
    )

    user = cur.fetchone()
    conn.close()

    if user:
        return jsonify({
            "success": True,
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"]
        })

    return jsonify({"success": False, "message": "Login gagal"})

@app.route("/api/ticket", methods=["POST"])
def api_ticket():
    conn = get_db()
    cur = conn.cursor()

    nomor_ticket = datetime.now().strftime("IT%Y%m%d%H%M%S")

    cur.execute("""
        INSERT INTO tickets
        (nomor_ticket,user_id,perusahaan,nama,departemen,kategori,detail,foto,status,tanggal)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        nomor_ticket,
        request.form.get("user_id"),
        request.form.get("perusahaan"),
        request.form.get("nama"),
        request.form.get("departemen"),
        request.form.get("kategori"),
        request.form.get("detail"),
        "",
        "Menunggu",
        datetime.now()
    ))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Ticket berhasil dibuat"})

@app.route("/api/riwayat/<int:user_id>")
def api_riwayat(user_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM tickets WHERE user_id=%s ORDER BY id DESC",
        (user_id,)
    )

    tickets = cur.fetchall()
    conn.close()

    return jsonify(tickets)

@app.route("/api/notifikasi/<int:user_id>")
def api_notifikasi(user_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM notifications WHERE user_id=%s ORDER BY id DESC",
        (user_id,)
    )

    notif = cur.fetchall()
    conn.close()

    return jsonify(notif)

@app.route("/dashboard")
def dashboard():
    print("SESSION USER ID =", session.get("user_id"))
    print("SESSION ROLE =", session.get("role"))
    
    if session.get("role") not in ["user", "outlet"]:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM tickets WHERE user_id=%s ORDER BY id DESC LIMIT 5",
        (session["user_id"],)
    )
    tickets = cur.fetchall()

    cur.execute(
        "SELECT * FROM notifications WHERE user_id=%s ORDER BY id DESC LIMIT 5",
        (session["user_id"],)
    )
    notifications = cur.fetchall()

    cur.execute(
        "SELECT COUNT(*) total FROM tickets WHERE user_id=%s",
        (session["user_id"],)
    )
    total = cur.fetchone()["total"]

    cur.execute(
        "SELECT COUNT(*) total FROM tickets WHERE user_id=%s AND status='Menunggu'",
        (session["user_id"],)
    )
    menunggu = cur.fetchone()["total"]

    cur.execute(
        "SELECT COUNT(*) total FROM tickets WHERE user_id=%s AND status='Diproses'",
        (session["user_id"],)
    )
    diproses = cur.fetchone()["total"]

    cur.execute(
        "SELECT COUNT(*) total FROM tickets WHERE user_id=%s AND status='Selesai'",
        (session["user_id"],)
    )
    selesai = cur.fetchone()["total"]

    conn.close()

    return render_template(
        "user_dashboard.html",
        tickets=tickets,
        notifications=notifications,
        total=total,
        menunggu=menunggu,
        diproses=diproses,
        selesai=selesai
    )

@app.route("/riwayat")
def riwayat():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    if session["role"] == "admin":
        cur.execute("SELECT * FROM tickets ORDER BY id DESC")
    else:
        cur.execute("SELECT * FROM tickets WHERE user_id=%s ORDER BY id DESC",
                    (session["user_id"],))

    tickets = cur.fetchall()
    conn.close()

    return render_template("riwayat.html", tickets=tickets)

@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT t.*, u.username
        FROM tickets t
        JOIN users u ON t.user_id=u.id
        ORDER BY t.id DESC
    """)
    tickets = cur.fetchall()

    cur.execute("SELECT COUNT(*) total FROM tickets")
    total = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) total FROM tickets WHERE status='Menunggu'")
    menunggu = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) total FROM tickets WHERE status='Diproses'")
    diproses = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) total FROM tickets WHERE status='Selesai'")
    selesai = cur.fetchone()["total"]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        tickets=tickets,
        total=total,
        menunggu=menunggu,
        diproses=diproses,
        selesai=selesai
    )

@app.route("/update/<int:id>/<status>")
def update_status(id, status):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM tickets WHERE id=%s",
        (id,)
    )

    ticket = cur.fetchone()

    cur.execute(
        "UPDATE tickets SET status=%s WHERE id=%s",
        (status, id)
    )

    cur.execute("""
        INSERT INTO notifications
        (user_id,pesan,dibaca,tanggal)
        VALUES(%s,%s,0,%s)
    """,
    (
        ticket["user_id"],
        f"Ticket {ticket['nomor_ticket']} sekarang {status}",
        datetime.now()
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/notifications")
def notifications():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM notifications WHERE user_id=%s ORDER BY id DESC",
        (session["user_id"],)
    )
    data = cur.fetchall()

    cur.execute(
        "UPDATE notifications SET dibaca=1 WHERE user_id=%s",
        (session["user_id"],)
    )

    conn.commit()
    conn.close()

    return render_template("notifications.html", data=data)

@app.route("/detail_ticket/<int:id>")
def detail_ticket(id):
    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE id=%s", (id,))
    ticket = cur.fetchone()

    conn.close()

    return render_template("detail_ticket.html", ticket=ticket)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
