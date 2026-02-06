
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from .notifications import EmailNotification

email = EmailNotification()
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = os.getenv('CALENDAR_ID')


class GoogleCalendarService():
    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        try:
            creds = service_account.Credentials.from_service_account_file(
                os.getenv('SERVICEACCOUNT'), scopes=SCOPES
            )
            return build("calendar", "v3", credentials=creds)

        except Exception as error:
            error_message = "Error al autenticar la cuenta de servicio."
            print(error)
            email.sendNotification(
                    subject=error_message,
                    body=error
                )
            raise


class GoogleCalendarManager(GoogleCalendarService):
    def __init__(self):
        super().__init__()

    def create_event(self, event_data, calendar_id):
        event = self.service.events().insert(
            calendarId=calendar_id,
            body=event_data
        ).execute()
        return event

    def event_exists(self, calendar_id, summary, start_date, end_date):
        events_result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=start_date,
            timeMax=end_date,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get('items', [])

        for event in events:
            if event.get('summary') == summary:
                return True
        return False

    def add_events_from_dataframe(self, df):
        event_created = False
        total_events = 0
        for _, row in df.iterrows():
            match_name = f"{row['Local']} vs {row['Visitante']} | {row['Competencia']} ⚽️"
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
            }

            if not self.event_exists(CALENDAR_ID, match_name, row['start_iso'], row['end_iso']):
                self.create_event(
                    event_data=event_data,
                    calendar_id=CALENDAR_ID
                )
                print(f"Nuevo evento: {match_name} el dia {row['Fecha_Str']}")
                total_events += 1
                event_created = True
        return event_created, total_events
