import sys
import argparse
import logging
from pathlib import Path

from googleapiclient.errors import HttpError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.gcalendar import GoogleCalendarManager, CALENDAR_ID, CALENDAR_FAVORITE_TEAMS_ID  # noqa: E402
from modules.espn_scraper import FAVORITE_TEAMS  # noqa: E402
from modules.logging_config import configure_logging  # noqa: E402

logger = logging.getLogger(__name__)


def _parse_teams(summary):
    match_part = summary.split(" | ")[0]
    if " vs " not in match_part:
        return None, None
    local, visitante = match_part.split(" vs ", 1)
    return local.strip(), visitante.strip()


def _find_favorite_team_matches(event_index):
    matches = []
    for event_hash, entry in event_index.items():
        summary = entry.get("summary", "")
        local, visitante = _parse_teams(summary)
        if local is None:
            logger.warning("No se pudo parsear el summary: %s", summary)
            continue
        if local in FAVORITE_TEAMS or visitante in FAVORITE_TEAMS:
            matches.append((event_hash, entry["event_id"], summary))
    return matches


def main():
    parser = argparse.ArgumentParser(
        description="Migra los partidos de los equipos favoritos ya indexados desde CALENDAR_ID hacia CALENDAR_FAVORITE_TEAMS_ID"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta el movimiento real. Sin este flag solo se simula (dry-run).",
    )
    args = parser.parse_args()

    configure_logging()

    if not CALENDAR_FAVORITE_TEAMS_ID:
        logger.error("CALENDAR_FAVORITE_TEAMS_ID no está definido en el entorno (.env)")
        return

    gcalendar = GoogleCalendarManager()
    matches_to_migrate = _find_favorite_team_matches(gcalendar.event_index)

    logger.info("Se encontraron %s partidos de equipos favoritos en el índice", len(matches_to_migrate))

    if not args.apply:
        logger.info("Modo dry-run (usa --apply para ejecutar el movimiento real). Partidos que se moverían:")
        for _, event_id, summary in matches_to_migrate:
            logger.info(" - [%s] %s", event_id, summary)
        return

    moved = 0
    failed = 0
    for _, event_id, summary in matches_to_migrate:
        try:
            gcalendar.move_event(event_id, CALENDAR_ID, CALENDAR_FAVORITE_TEAMS_ID)
            logger.info("Movido: %s", summary)
            moved += 1
        except HttpError as error:
            reason = None
            if isinstance(error.error_details, list) and error.error_details:
                reason = error.error_details[0].get("reason")

            if reason == "cannotChangeOrganizer":
                logger.warning(
                    "Omitido (ya estaba migrado, no pertenece a CALENDAR_ID): %s", summary
                )
            else:
                logger.error(
                    "No se pudo mover el evento: %s (event_id=%s) -> %s",
                    summary, event_id, error.reason,
                )
            failed += 1
        except Exception as error:
            logger.error(
                "No se pudo mover el evento: %s (event_id=%s) -> %s",
                summary, event_id, error,
            )
            failed += 1

    logger.info(
        "Migración finalizada. Movidos: %s, Fallidos: %s, Total detectados: %s",
        moved, failed, len(matches_to_migrate),
    )


if __name__ == "__main__":
    main()
