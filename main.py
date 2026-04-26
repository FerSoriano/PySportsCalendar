
import pandas as pd
from modules import GoogleCalendarManager, EmailNotification, EspnScraper, TEAMS_URLS


def main():
    gcalendar = GoogleCalendarManager()
    email = EmailNotification()

    try:
        print("--- OBTENIENDO DATOS DE ESPN ---")
        scraper = EspnScraper()
        df_matches = scraper.run_all(TEAMS_URLS)

        if df_matches.empty:
            print("⚠️ No hay partidos nuevos para procesar.")
            return

        print(f"\n✅ Se encontraron {len(df_matches)} partidos 📅")

        print("\nACTUALIZANDO CALENDARIO...")

        print("PROCESANDO FECHAS...⌛️\n")
        df_matches['end_datetime'] = df_matches['Fecha_Obj'] + pd.Timedelta(hours=2)
        # Convertimos a string ISO con zona horaria (-06:00 México)
        df_matches['start_iso'] = df_matches['Fecha_Obj'].apply(lambda x: x.strftime("%Y-%m-%dT%H:%M:%S-06:00"))
        df_matches['end_iso'] = df_matches['end_datetime'].apply(lambda x: x.strftime("%Y-%m-%dT%H:%M:%S-06:00"))

    except Exception as error:
        print('error:', error)
        email.sendNotification(
            subject="🤖 BOT: Error al procesar los partidos. ❌",
            body=error
        )
        return

    event_created, total_events, total_updated, total_skipped = gcalendar.add_events_from_dataframe(df_matches)

    if event_created or total_updated:
        msg = f"\n✅📅 Se agregaron {total_events} partidos nuevos, se actualizaron {total_updated} y se omitieron {total_skipped} sin cambios"
        email.sendNotification(
            subject="🤖 BOT: Nuevos Partidos 🎉 - Google Calendar",
            body=msg
        )
        print(msg)
        print("\nProceso finalizado 🍺")
    else:
        print(f"No se agregaron ni actualizaron eventos. Omitidos sin cambios: {total_skipped}")


if __name__ == "__main__":
    main()
