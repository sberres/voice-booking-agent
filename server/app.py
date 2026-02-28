"""
Voice Booking Agent — Backend Server
Handles Vapi webhooks + Google Calendar (with SQLite fallback)
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

# Try Google Calendar, fall back to SQLite mock
USE_GOOGLE = os.path.exists(os.path.join(os.path.dirname(__file__), "google-credentials.json"))
if USE_GOOGLE:
    try:
        from google_calendar import get_available_slots as gcal_slots, book_appointment as gcal_book, cancel_appointment as gcal_cancel
        print("✅ Google Calendar integration loaded")
    except Exception as e:
        print(f"⚠️ Google Calendar failed to load: {e}")
        USE_GOOGLE = False

if not USE_GOOGLE:
    print("📋 Using SQLite mock calendar")

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

# --------------- Date Parsing ---------------

def parse_date_flexible(date_str: str) -> str:
    """Parse various date formats into YYYY-MM-DD."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    
    # Already in correct format
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        pass
    
    # Try common formats
    for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%d %B %Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Handle day names (Monday, Tuesday, etc.)
    days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    lower = date_str.lower().strip()
    if lower in days:
        today = datetime.now()
        target_day = days[lower]
        days_ahead = target_day - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    if lower == "today":
        return datetime.now().strftime("%Y-%m-%d")
    if lower == "tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Handle "next monday", "next week", etc.
    if lower.startswith("next "):
        day_name = lower.replace("next ", "")
        if day_name in days:
            today = datetime.now()
            target_day = days[day_name]
            days_ahead = target_day - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    print(f"⚠️ Could not parse date: '{date_str}', using as-is")
    return date_str

# --------------- Vapi Webhook ---------------

@app.route("/vapi/webhook", methods=["POST"])
def vapi_webhook():
    """Handle Vapi server-side function calls."""
    data = request.json
    
    # Vapi can send data in different formats
    msg = data.get("message", {})
    msg_type = msg.get("type", "")
    
    # Handle newer Vapi "tool-calls" format where data is at top level
    if not msg_type and "type" in data:
        msg = data
        msg_type = data.get("type", "")

    # Log all incoming webhook data for debugging
    print(f"📥 Webhook: type={msg_type}, full_keys={list(data.keys())}, data={json.dumps(data, default=str)[:800]}")

    # Handle function calls from the voice agent
    if msg_type == "function-call":
        function_call = msg.get("functionCall", {})
        fn_name = function_call.get("name", "")
        params = function_call.get("parameters", {})
        print(f"🔧 Function call: {fn_name} params={params}")

        if fn_name == "check_availability":
            date_str = params.get("date", datetime.now().strftime("%Y-%m-%d"))
            date_str = parse_date_flexible(date_str)
            slots = gcal_slots(date_str) if USE_GOOGLE else get_available_slots(date_str)
            today = datetime.now().strftime("%Y-%m-%d")
            day_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
            if slots:
                slot_text = ", ".join(slots[:6])  # Show max 6 slots
                result = f"Today is {today}. Available slots on {day_name} {date_str}: {slot_text}"
                if len(slots) > 6:
                    result += f" and {len(slots) - 6} more."
            else:
                result = f"Today is {today}. No available slots on {day_name} {date_str}. Please try another date."
            return jsonify({"results": [{"result": result}]})

        elif fn_name == "book_appointment":
            book_fn = gcal_book if USE_GOOGLE else book_appointment
            result = book_fn(
                name=params.get("name", "Unknown"),
                date_str=parse_date_flexible(params.get("date", "")),
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
            if USE_GOOGLE:
                result = gcal_cancel(name, date_str)
                if result["success"]:
                    res = f"Cancelled appointment for {name} on {date_str}."
                else:
                    res = result["error"]
                return jsonify({"results": [{"result": res}]})
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

    # Handle "tool-calls" type (Vapi newer format)
    if msg_type == "tool-calls":
        tool_calls = msg.get("toolCalls", data.get("toolCalls", []))
        results = []
        for tc in tool_calls:
            fn = tc.get("function", {})
            fn_name = fn.get("name", "")
            params = fn.get("arguments", {})
            if isinstance(params, str):
                params = json.loads(params)
            print(f"🔧 Tool call: {fn_name} params={params}")
            
            if fn_name == "check_availability":
                date_str = parse_date_flexible(params.get("date", datetime.now().strftime("%Y-%m-%d")))
                slots = gcal_slots(date_str) if USE_GOOGLE else get_available_slots(date_str)
                if slots:
                    slot_text = ", ".join(slots[:6])
                    res = f"Available slots on {date_str}: {slot_text}"
                    if len(slots) > 6:
                        res += f" and {len(slots) - 6} more."
                else:
                    res = f"No available slots on {date_str}."
                results.append({"toolCallId": tc.get("id"), "result": res})
            
            elif fn_name == "book_appointment":
                book_fn = gcal_book if USE_GOOGLE else book_appointment
                result = book_fn(
                    name=params.get("name", "Unknown"),
                    date_str=parse_date_flexible(params.get("date", "")),
                    time_str=params.get("time", ""),
                    purpose=params.get("purpose", ""),
                    phone=params.get("phone", ""),
                    email=params.get("email", "")
                )
                if result["success"]:
                    apt = result["appointment"]
                    res = f"Appointment booked for {apt['name']} on {apt['date']} at {apt['time']}."
                else:
                    res = result["error"]
                results.append({"toolCallId": tc.get("id"), "result": res})
            
            elif fn_name == "cancel_appointment":
                if USE_GOOGLE:
                    result = gcal_cancel(params.get("name", ""), parse_date_flexible(params.get("date", "")))
                    res = f"Cancelled." if result["success"] else result["error"]
                else:
                    res = "Cancelled."
                results.append({"toolCallId": tc.get("id"), "result": res})
        
        return jsonify({"results": results})

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
    book_fn = gcal_book if USE_GOOGLE else book_appointment
    result = book_fn(
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
    slots = gcal_slots(date) if USE_GOOGLE else get_available_slots(date)
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
