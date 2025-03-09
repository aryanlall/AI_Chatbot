import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token
from agno.agent import Agent
import nltk
from reportlab.pdfgen import canvas

nltk.download("punkt")
load_dotenv()  # ✅ Load environment variables from .env

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["JWT_SECRET_KEY"] = "your_secret_key"

db = SQLAlchemy(app)
jwt = JWTManager(app)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ✅ Debugging: Print API Key (Remove this in production)
if not GROQ_API_KEY:
    print("🔴 ERROR: GROQ_API_KEY is missing from .env file!")


# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    role = db.Column(db.String(50))  # student, employee, admin
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


# Leave Request Model
class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    leave_type = db.Column(db.String(50))
    start_date = db.Column(db.String(50))
    end_date = db.Column(db.String(50))
    status = db.Column(db.String(20), default="Pending")


# ✅ NLP Agent using Groq API
class NLPAgent(Agent):
    def handle_request(self, data):
        prompt = data.get("query", "")
        response = self.query_groq(prompt)
        return {"response": response}

    def query_groq(self, text):
        if not GROQ_API_KEY:
            return "Groq API Key is missing!"

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",  # ✅ Ensure this model is available
            "messages": [{"role": "user", "content": text}],
            "temperature": 0.7
        }

        try:
            response = requests.post(GROQ_API_URL, json=payload, headers=headers)
            print("🔍 API Request Sent to Groq:", payload)
            print("🔍 API Response Status Code:", response.status_code)
            print("🔍 API Response Content:", response.text)

            if response.status_code != 200:
                return f"Groq API Error: {response.text}"

            return response.json().get("choices", [{}])[0].get("message", {}).get("content",
                                                                                  "Error processing request.")

        except requests.exceptions.RequestException as e:
            return f"Network Error: {str(e)}"


# ✅ Certificate Agent
class CertificateAgent(Agent):
    def handle_request(self, data):
        student_id = data.get("student_id")
        cert_type = data.get("type", "Bonafide")

        cert_path = f"certificates/{student_id}_{cert_type}.pdf"
        os.makedirs("certificates", exist_ok=True)

        pdf = canvas.Canvas(cert_path)
        pdf.drawString(100, 750, f"{cert_type} Certificate")
        pdf.drawString(100, 730, f"Student ID: {student_id}")
        pdf.save()

        return {"status": "Certificate generated", "path": cert_path}


# ✅ Leave Sanction Agent
class LeaveAgent(Agent):
    def handle_request(self, data):
        leave = LeaveRequest(
            user_id=data["user_id"],
            leave_type=data["leave_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            status="Approved"
        )
        db.session.add(leave)
        db.session.commit()
        return {"status": "Leave Approved", "leave_id": leave.id}


# ✅ Query Agent
class QueryAgent(Agent):
    def handle_request(self, data):
        queries = {
            "academic_calendar": "The academic calendar is available online.",
            "backlog_exams": "Backlog exams will be held next month.",
        }
        return {"response": queries.get(data["query"], "Unknown query")}


# ✅ Custom Multi-Agent System
class AgentManager:
    def __init__(self):
        self.agents = {
            "nlp": NLPAgent(),
            "leave": LeaveAgent(),
            "certificate": CertificateAgent(),
            "query": QueryAgent(),
        }

    def handle_request(self, agent_type, data):
        if agent_type in self.agents:
            return self.agents[agent_type].handle_request(data)
        return {"error": "Invalid agent type"}


# ✅ Initialize Agent System
agent_manager = AgentManager()


# ✅ API Routes
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    new_user = User(name=data["name"], role=data["role"], email=data["email"], password=data["password"])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"], password=data["password"]).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    access_token = create_access_token(identity=user.id)
    return jsonify({"token": access_token})


@app.route("/request", methods=["POST"])
def handle_request():
    data = request.json
    agent_type = data.get("agent_type")

    response = agent_manager.handle_request(agent_type, data)
    return jsonify(response)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
