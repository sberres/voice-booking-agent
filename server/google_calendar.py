"""
Google Calendar integration for Voice Booking Agent
"""

import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "google-credentials.json")
CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "nishithkumar99008@gmail.com")
SLOT_DURATION = 30  # minutes
BUSINESS_START = 9   # 9 AM
BUSINESS_END = 17    # 5 PM
TIMEZONE = os.environ.get("CALENDAR_TIMEZONE", "Asia/Kolkata")


def get_service():
    """Get authenticated Google Calendar service."""
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=credentials)


def get_available_slots(date_str: str) -> list:
    """Get available slots for a given date from Google Calendar."""
    service = get_service()

    # Parse date and create time range (use RFC3339 with timezone)
    date = datetime.strptime(date_str, "%Y-%m-%d")
    time_min = date.replace(hour=0, minute=0).isoformat() + "Z"
    time_max = date.replace(hour=23, minute=59).isoformat() + "Z"

    # Get existing events
    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        timeZone=TIMEZONE,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])

    # Build set of busy times
    busy_slots = set()
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        if "T" in start:
            event_start = datetime.fromisoformat(start.replace("Z", "+00:00")).replace(tzinfo=None)
            end = event["end"].get("dateTime", event["end"].get("date"))
            event_end = datetime.fromisoformat(end.replace("Z", "+00:00")).replace(tzinfo=None)
            # Mark all slots that overlap with this event
            slot_time = date.replace(hour=BUSINESS_START, minute=0)
            while slot_time.hour * 60 + slot_time.minute + SLOT_DURATION <= BUSINESS_END * 60:
                slot_end = slot_time + timedelta(minutes=SLOT_DURATION)
                if slot_time < event_end and slot_end > event_start:
                    busy_slots.add(slot_time.strftime("%H:%M"))
                slot_time = slot_end

    # Generate available slots
    available = []
    current = BUSINESS_START * 60
    end = BUSINESS_END * 60
    while current + SLOT_DURATION <= end:
        h, m = divmod(current, 60)
        time_str = f"{h:02d}:{m:02d}"
        if time_str not in busy_slots:
            available.append(time_str)
        current += SLOT_DURATION

    return available


def book_appointment(name: str, date_str: str, time_str: str, purpose: str = "", phone: str = "", email: str = "") -> dict:
    """Book an appointment on Google Calendar."""
    # Check availability first
    available = get_available_slots(date_str)
    if time_str not in available:
        return {"success": False, "error": f"Slot {time_str} on {date_str} is not available."}

    service = get_service()

    h, m = map(int, time_str.split(":"))
    start_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=h, minute=m)
    end_dt = start_dt + timedelta(minutes=SLOT_DURATION)

    summary = f"Appointment: {name}"
    if purpose:
        summary += f" - {purpose}"

    description = f"Booked by Voice Booking Agent\nName: {name}"
    if phone:
        description += f"\nPhone: {phone}"
    if email:
        description += f"\nEmail: {email}"
    if purpose:
        description += f"\nPurpose: {purpose}"

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
    }

    created = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()

    return {
        "success": True,
        "appointment": {
            "name": name,
            "date": date_str,
            "time": f"{time_str} - {end_dt.strftime('%H:%M')}",
            "purpose": purpose,
            "event_id": created.get("id"),
            "link": created.get("htmlLink")
        }
    }


def cancel_appointment(name: str, date_str: str) -> dict:
    """Cancel an appointment by searching for it."""
    service = get_service()

    date = datetime.strptime(date_str, "%Y-%m-%d")
    time_min = date.replace(hour=0, minute=0).isoformat() + "Z"
    time_max = date.replace(hour=23, minute=59).isoformat() + "Z"

    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        q=name
    ).execute()
    events = events_result.get("items", [])

    if not events:
        return {"success": False, "error": f"No appointment found for {name} on {date_str}."}

    for event in events:
        service.events().delete(calendarId=CALENDAR_ID, eventId=event["id"]).execute()

    return {"success": True, "cancelled": len(events)}
