"""
Voice Booking Agent — Backend Server
Handles Vapi webhooks + mock calendar (SQLite)
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
app = Flask(__name__, static_folder=WEB_DIR, static_url_path="/static")
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "bookings.db")

# --------------- Database ---------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            date TEXT NOT NULL,
            time_start TEXT NOT NULL,
            time_end TEXT NOT NULL,
            purpose TEXT,
            status TEXT DEFAULT 'confirmed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --------------- Calendar Logic ---------------

BUSINESS_HOURS = {"start": 9, "end": 17}  # 9 AM - 5 PM
SLOT_DURATION = 30  # minutes

def get_available_slots(date_str: str) -> list:
    """Get available 30-min slots for a given date."""
    conn = get_db()
    booked = conn.execute(
        "SELECT time_start, time_end FROM appointments WHERE date = ? AND status = 'confirmed'",
        (date_str,)
    ).fetchall()
    conn.close()

    booked_times = set()
    for b in booked:
        booked_times.add(b["time_start"])

    slots = []
    current = BUSINESS_HOURS["start"] * 60  # minutes from midnight
    end = BUSINESS_HOURS["end"] * 60

    while current + SLOT_DURATION <= end:
        h, m = divmod(current, 60)
        time_str = f"{h:02d}:{m:02d}"
        if time_str not in booked_times:
            slots.append(time_str)
        current += SLOT_DURATION

    return slots

def book_appointment(name: str, date_str: str, time_str: str, purpose: str = "", phone: str = "", email: str = "") -> dict:
    """Book an appointment slot."""
    # Check if slot is available
    available = get_available_slots(date_str)
    if time_str not in available:
        return {"success": False, "error": f"Slot {time_str} on {date_str} is not available."}

    h, m = map(int, time_str.split(":"))
    end_minutes = h * 60 + m + SLOT_DURATION
    eh, em = divmod(end_minutes, 60)
    time_end = f"{eh:02d}:{em:02d}"

    conn = get_db()
    conn.execute(
        "INSERT INTO appointments (name, email, phone, date, time_start, time_end, purpose) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, email, phone, date_str, time_str, time_end, purpose)
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "appointment": {
            "name": name,
            "date": date_str,
            "time": f"{time_str} - {time_end}",
            "purpose": purpose
        }
    }

# --------------- Vapi Webhook ---------------

@app.route("/vapi/webhook", methods=["POST"])
def vapi_webhook():
    """Handle Vapi server-side function calls."""
    data = request.json
    msg = data.get("message", {})
    msg_type = msg.get("type", "")

    # Handle function calls from the voice agent
    if msg_type == "function-call":
        function_call = msg.get("functionCall", {})
        fn_name = function_call.get("name", "")
        params = function_call.get("parameters", {})

        if fn_name == "check_availability":
            date_str = params.get("date", datetime.now().strftime("%Y-%m-%d"))
            slots = get_available_slots(date_str)
            if slots:
                slot_text = ", ".join(slots[:6])  # Show max 6 slots
                result = f"Available slots on {date_str}: {slot_text}"
                if len(slots) > 6:
                    result += f" and {len(slots) - 6} more."
            else:
                result = f"No available slots on {date_str}. Please try another date."
            return jsonify({"results": [{"result": result}]})

        elif fn_name == "book_appointment":
            result = book_appointment(
                name=params.get("name", "Unknown"),
                date_str=params.get("date", ""),
                time_str=params.get("time", ""),
                purpose=params.get("purpose", ""),
                phone=params.get("phone", ""),
                email=params.get("email", "")
            )
            if result["success"]:
                apt = result["appointment"]
                msg = f"Appointment booked for {apt['name']} on {apt['date']} at {apt['time']}."
                if apt["purpose"]:
                    msg += f" Purpose: {apt['purpose']}."
            else:
                msg = result["error"]
            return jsonify({"results": [{"result": msg}]})

        elif fn_name == "cancel_appointment":
            name = params.get("name", "")
            date_str = params.get("date", "")
            conn = get_db()
            cursor = conn.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE name LIKE ? AND date = ? AND status = 'confirmed'",
                (f"%{name}%", date_str)
            )
            conn.commit()
            cancelled = cursor.rowcount
            conn.close()
            if cancelled:
                result = f"Cancelled appointment for {name} on {date_str}."
            else:
                result = f"No appointment found for {name} on {date_str}."
            return jsonify({"results": [{"result": result}]})

    # Handle other webhook events (status updates, end-of-call, etc.)
    if msg_type == "end-of-call-report":
        print(f"Call ended. Duration: {msg.get('duration', 'unknown')}s")
        return jsonify({"ok": True})

    return jsonify({"ok": True})

# --------------- REST API (for web dashboard) ---------------

@app.route("/api/appointments", methods=["GET"])
def list_appointments():
    """List all appointments."""
    date_filter = request.args.get("date")
    conn = get_db()
    if date_filter:
        rows = conn.execute(
            "SELECT * FROM appointments WHERE date = ? ORDER BY time_start", (date_filter,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM appointments WHERE status = 'confirmed' ORDER BY date, time_start"
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/appointments", methods=["POST"])
def create_appointment():
    """Create appointment via web form."""
    data = request.json
    result = book_appointment(
        name=data.get("name", ""),
        date_str=data.get("date", ""),
        time_str=data.get("time", ""),
        purpose=data.get("purpose", ""),
        phone=data.get("phone", ""),
        email=data.get("email", "")
    )
    return jsonify(result)

@app.route("/api/slots/<date>", methods=["GET"])
def available_slots(date):
    """Get available slots for a date."""
    slots = get_available_slots(date)
    return jsonify({"date": date, "slots": slots})

@app.route("/api/appointments/<int:apt_id>", methods=["DELETE"])
def cancel_appointment_api(apt_id):
    """Cancel an appointment."""
    conn = get_db()
    conn.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (apt_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/", methods=["GET"])
def index():
    return app.send_static_file("index.html")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "voice-booking-agent"})

# --------------- Main ---------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3020))
    print(f"🗓️ Voice Booking Agent running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
