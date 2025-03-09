from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests

app = Flask(__name__)
app.secret_key = "your_secret_key"

API_URL = "http://127.0.0.1:5000"  # Backend API


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        response = requests.post(f"{API_URL}/login", json={"email": email, "password": password})
        if response.status_code == 200:
            session["token"] = response.json()["token"]
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "token" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/leave", methods=["POST"])
def leave_request():
    if "token" not in session:
        return redirect(url_for("login"))

    data = {
        "agent_type": "leave",
        "user_id": request.form["user_id"],
        "leave_type": request.form["leave_type"],
        "start_date": request.form["start_date"],
        "end_date": request.form["end_date"]
    }

    response = requests.post(f"{API_URL}/request", json=data)
    flash(response.json().get("status", "Failed to process leave request"), "info")
    return redirect(url_for("dashboard"))


@app.route("/certificate", methods=["POST"])
def generate_certificate():
    if "token" not in session:
        return redirect(url_for("login"))

    data = {
        "agent_type": "certificate",
        "student_id": request.form["student_id"],
        "type": request.form["type"]
    }

    response = requests.post(f"{API_URL}/request", json=data)
    flash(response.json().get("status", "Failed to generate certificate"), "info")
    return redirect(url_for("dashboard"))


@app.route("/query", methods=["POST"])
def academic_query():
    if "token" not in session:
        return redirect(url_for("login"))

    data = {"agent_type": "query", "query": request.form["query"]}

    response = requests.post(f"{API_URL}/request", json=data)
    flash(response.json().get("response", "Failed to fetch query response"), "info")
    return redirect(url_for("dashboard"))


@app.route("/chat", methods=["POST"])
def chat_with_bot():
    if "token" not in session:
        return redirect(url_for("login"))

    data = {"agent_type": "nlp", "query": request.form["message"]}

    response = requests.post(f"{API_URL}/request", json=data)
    flash(response.json().get("response", "Failed to process your message"), "info")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.pop("token", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(port=5001, debug=True)
