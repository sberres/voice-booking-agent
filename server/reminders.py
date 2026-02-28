"""
Outbound Reminder Calls — Voice Booking Agent
Scans Google Calendar for tomorrow's appointments and calls to confirm.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from google_calendar import get_service, CALENDAR_ID, TIMEZONE

VAPI_API_KEY = os.environ.get("VAPI_API_KEY", "")
VAPI_PHONE_NUMBER_ID = os.environ.get("VAPI_PHONE_NUMBER_ID", "")
VAPI_ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID", "")


def get_tomorrows_appointments():
    """Get all appointments for tomorrow from Google Calendar."""
    service = get_service()
    tomorrow = datetime.now() + timedelta(days=1)
    time_min = tomorrow.replace(hour=0, minute=0, second=0).isoformat() + "Z"
    time_max = tomorrow.replace(hour=23, minute=59, second=59).isoformat() + "Z"

    events = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        timeZone=TIMEZONE,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    appointments = []
    for event in events.get("items", []):
        summary = event.get("summary", "")
        if not summary.startswith("Appointment:"):
            continue

        # Extract phone from description
        description = event.get("description", "")
        phone = ""
        name = ""
        for line in description.split("\n"):
            if line.startswith("Phone:"):
                phone = line.replace("Phone:", "").strip()
            if line.startswith("Name:"):
                name = line.replace("Name:", "").strip()

        start = event["start"].get("dateTime", "")
        if "T" in start:
            time_str = start.split("T")[1][:5]
        else:
            time_str = "unknown"

        appointments.append({
            "event_id": event["id"],
            "name": name or summary.replace("Appointment:", "").strip(),
            "phone": phone,
            "time": time_str,
            "date": tomorrow.strftime("%Y-%m-%d"),
            "summary": summary
        })

    return appointments


def make_reminder_call(appointment: dict) -> dict:
    """Make an outbound reminder call via Vapi."""
    if not VAPI_API_KEY:
        return {"success": False, "error": "VAPI_API_KEY not set"}
    if not appointment.get("phone"):
        return {"success": False, "error": f"No phone number for {appointment['name']}"}

    tomorrow_date = appointment["date"]
    time = appointment["time"]
    name = appointment["name"]

    # Create outbound call via Vapi API
    payload = {
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": appointment["phone"]
        },
        "assistantOverrides": {
            "firstMessage": f"Hi {name}, this is Riley from Wellness Partners calling to remind you about your appointment tomorrow, {tomorrow_date}, at {time}. Can you confirm you'll be there?",
            "model": {
                "messages": [
                    {
                        "role": "system",
                        "content": f"""You are Riley, a friendly appointment reminder assistant for Wellness Partners.
You are calling {name} to remind them about their appointment tomorrow ({tomorrow_date}) at {time}.

Your goals:
1. Confirm they can make the appointment
2. If they need to reschedule, use the check_availability and book_appointment tools
3. If they want to cancel, use cancel_appointment
4. Be brief and friendly — this is a reminder call, keep it under 2 minutes

Today's date is {datetime.now().strftime('%Y-%m-%d')}."""
                    }
                ]
            }
        }
    }

    if VAPI_ASSISTANT_ID:
        payload["assistantId"] = VAPI_ASSISTANT_ID
    
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(
            "https://api.vapi.ai/call",
            headers=headers,
            json=payload
        )
        if resp.status_code in [200, 201]:
            return {"success": True, "call": resp.json()}
        else:
            return {"success": False, "error": resp.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_all_reminders():
    """Send reminder calls for all tomorrow's appointments."""
    appointments = get_tomorrows_appointments()
    results = []

    for apt in appointments:
        if apt.get("phone"):
            result = make_reminder_call(apt)
            results.append({
                "name": apt["name"],
                "phone": apt["phone"],
                "time": apt["time"],
                **result
            })
        else:
            results.append({
                "name": apt["name"],
                "phone": "missing",
                "time": apt["time"],
                "success": False,
                "error": "No phone number"
            })

    return {
        "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_appointments": len(appointments),
        "calls_made": sum(1 for r in results if r.get("success")),
        "results": results
    }


if __name__ == "__main__":
    print("📞 Checking tomorrow's appointments...")
    appointments = get_tomorrows_appointments()
    print(f"Found {len(appointments)} appointments:")
    for apt in appointments:
        print(f"  - {apt['name']} at {apt['time']} | Phone: {apt.get('phone', 'N/A')}")

    if VAPI_API_KEY:
        print("\n📞 Sending reminder calls...")
        results = send_all_reminders()
        print(json.dumps(results, indent=2))
    else:
        print("\n⚠️ Set VAPI_API_KEY to send actual calls")
