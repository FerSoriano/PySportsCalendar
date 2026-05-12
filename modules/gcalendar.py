
import os
import json
import hashlib
import logging
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from .notifications import EmailNotification

logger = logging.getLogger(__name__)
email = EmailNotification()
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = os.getenv('CALENDAR_ID')
EVENT_INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "event_index.json"


class GoogleCalendarService():
    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        key_path = os.getenv('SERVICEACCOUNT')
        if not key_path:
            raise ValueError("Error: La variable de entorno 'SERVICEACCOUNT' no está definida.")
        
        try:
            creds = service_account.Credentials.from_service_account_file(
                key_path, scopes=SCOPES
            )
            return build("calendar", "v3", credentials=creds)

        except Exception as error:
            error_message = "Error al autenticar la cuenta de servicio."
            logger.exception(error_message)
            email.sendNotification(
                    subject=error_message,
                    body=str(error)
                )
            raise


class GoogleCalendarManager(GoogleCalendarService):
    def __init__(self):
        super().__init__()
        self.event_index = self._load_event_index()

    def _load_event_index(self):
        if not EVENT_INDEX_PATH.exists():
            return {}

        try:
            with EVENT_INDEX_PATH.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_event_index(self):
        EVENT_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EVENT_INDEX_PATH.open("w", encoding="utf-8") as file:
            json.dump(self.event_index, file, indent=2, ensure_ascii=False)

    def _build_event_key(self, local_team, away_team, competition):
        raw_key = f"{local_team}|{away_team}|{competition}".strip().lower()
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def _event_datetimes_changed(self, existing_event, new_event_data):
        existing_start = existing_event.get("start", {}).get("dateTime")
        existing_end = existing_event.get("end", {}).get("dateTime")
        new_start = new_event_data.get("start", {}).get("dateTime")
        new_end = new_event_data.get("end", {}).get("dateTime")
        return existing_start != new_start or existing_end != new_end

    def create_event(self, event_data, calendar_id):
        event = self.service.events().insert(
            calendarId=calendar_id,
            body=event_data
        ).execute()
        return event

    def update_event(self, event_id, event_data, calendar_id):
        event = self.service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_data
        ).execute()
        return event

    def get_event_by_id(self, calendar_id, event_id):
        try:
            return self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
        except Exception:
            return None

    def find_event_by_summary(self, calendar_id, summary):
        events_result = self.service.events().list(
            calendarId=calendar_id,
            q=summary,
            timeMin="2000-01-01T00:00:00Z",
            singleEvents=True
        ).execute()
        events = events_result.get("items", [])

        for event in events:
            if event.get("summary") == summary:
                return event
        return None

    def get_event_by_hash(self, calendar_id, event_hash, summary=None):
        indexed_event = self.event_index.get(event_hash)
        if indexed_event:
            event = self.get_event_by_id(calendar_id, indexed_event.get("event_id"))
            if event:
                return event

        events_result = self.service.events().list(
            calendarId=calendar_id,
            privateExtendedProperty=f"event_hash={event_hash}",
            singleEvents=True
        ).execute()
        events = events_result.get('items', [])

        if not events:
            if summary:
                return self.find_event_by_summary(calendar_id, summary)
            return None

        event = events[0]
        self.event_index[event_hash] = {
            "event_id": event["id"],
            "summary": event.get("summary", "")
        }
        self._save_event_index()
        return event

    def add_events_from_dataframe(self, df):
        event_created = False
        total_events = 0
        total_updated = 0
        total_skipped = 0
        for _, row in df.iterrows():
            match_name = f"{row['Local']} vs {row['Visitante']} | {row['Competencia']} ⚽️"
            event_hash = self._build_event_key(row['Local'], row['Visitante'], row['Competencia'])
            event_data = {
                "summary": match_name,
                "start": {
                    "dateTime": row['start_iso'],
                    "timeZone": "America/Mexico_City",
                },
                "end": {
                    "dateTime": row['end_iso'],
                    "timeZone": "America/Mexico_City",
                },
                "extendedProperties": {
                    "private": {
                        "event_hash": event_hash
                    }
                }
            }

            existing_event = self.get_event_by_hash(CALENDAR_ID, event_hash, match_name)

            if existing_event:
                self.event_index[event_hash] = {
                    "event_id": existing_event["id"],
                    "summary": match_name
                }

                if self._event_datetimes_changed(existing_event, event_data):
                    self.update_event(
                        event_id=existing_event["id"],
                        event_data=event_data,
                        calendar_id=CALENDAR_ID
                    )
                    self._save_event_index()
                    logger.info("Evento actualizado: %s el dia %s", match_name, row["Fecha_Str"])
                    total_updated += 1
                else:
                    self._save_event_index()
                    logger.debug("Sin cambios: %s", match_name)
                    total_skipped += 1
            else:
                created_event = self.create_event(
                    event_data=event_data,
                    calendar_id=CALENDAR_ID
                )
                self.event_index[event_hash] = {
                    "event_id": created_event["id"],
                    "summary": match_name
                }
                self._save_event_index()
                logger.info("Nuevo evento: %s el dia %s", match_name, row["Fecha_Str"])
                total_events += 1
                event_created = True
        return event_created, total_events, total_updated, total_skipped
