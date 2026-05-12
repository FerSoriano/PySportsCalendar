
import logging

import pandas as pd

from modules import GoogleCalendarManager, EmailNotification, EspnScraper, TEAMS_URLS
from modules.logging_config import configure_logging


def main():
    configure_logging()
    logger = logging.getLogger(__name__)

    gcalendar = GoogleCalendarManager()
    email = EmailNotification()

    try:
        logger.info("Obteniendo datos de ESPN")
        scraper = EspnScraper()
        df_matches = scraper.run_all(TEAMS_URLS)

        if df_matches.empty:
            logger.warning("No hay partidos nuevos para procesar")
            return

        logger.info("Se encontraron %s partidos", len(df_matches))

        logger.info("Actualizando calendario")

        logger.info("Procesando fechas")
        df_matches['end_datetime'] = df_matches['Fecha_Obj'] + pd.Timedelta(hours=2)
        # Convertimos a string ISO con zona horaria (-06:00 México)
        df_matches['start_iso'] = df_matches['Fecha_Obj'].apply(lambda x: x.strftime("%Y-%m-%dT%H:%M:%S-06:00"))
        df_matches['end_iso'] = df_matches['end_datetime'].apply(lambda x: x.strftime("%Y-%m-%dT%H:%M:%S-06:00"))

    except Exception as error:
        logger.exception("Error al procesar los partidos")
        email.sendNotification(
            subject="🤖 BOT: Error al procesar los partidos. ❌",
            body=str(error)
        )
        return

    event_created, total_events, total_updated, total_skipped = gcalendar.add_events_from_dataframe(df_matches)

    if event_created or total_updated:
        msg = (
            f"Se agregaron {total_events} partidos nuevos, "
            f"se actualizaron {total_updated} y se omitieron {total_skipped} sin cambios"
        )
        email.sendNotification(
            subject="🤖 BOT: Nuevos Partidos 🎉 - Google Calendar",
            body=msg
        )
        logger.info(msg)
        logger.info("Proceso finalizado")
    else:
        logger.warning(
            "No se agregaron ni actualizaron eventos. Omitidos sin cambios: %s",
            total_skipped,
        )


if __name__ == "__main__":
    main()
