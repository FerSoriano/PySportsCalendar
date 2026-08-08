# PySportsCalendar 🐍⚽️📅

PySportsCalendar fetches upcoming match schedules from ESPN's public APIs for a configurable list of clubs and national teams, syncs them to Google Calendar, and sends email notifications when events are created, updated, or when an error occurs.

**Main features**

- Fetches match data for club and national teams directly from ESPN's public JSON APIs (no HTML scraping), covering leagues like La Liga, Premier League, Serie A, Liga MX, Ligue 1, Brasileirão, Argentine football, Champions/Europa/Conference League, Libertadores/Sudamericana, CONCACAF competitions, and national-team competitions (World Cup, qualifiers, Nations League, continental cups, etc.).
- Adds and updates events in Google Calendar, keeping a local index (generated at runtime under `data/`, not tracked in git) so existing events are matched by hash and updated in place instead of duplicated when their date/time changes.
- Routes matches involving your favorite teams to a dedicated secondary calendar (`CALENDAR_FAVORITE_TEAMS_ID`); every other team goes to the main calendar (`CALENDAR_ID`). Favorite teams are configured via `FAVORITE_TEAMS` in [modules/espn_scraper.py](modules/espn_scraper.py).
- Sends email notifications on errors, and summarizes how many events were added/updated/skipped after each run.
- Logs to both console and a log file, configurable via `APP_LOG_PATH`. See [modules/logging_config.py](modules/logging_config.py).

**Quick example**

Install dependencies and run the bot:

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

See the runner script at [main.py](main.py).

**Dependencies**

The full list is in [requirements.txt](requirements.txt). Key packages used by the project include:

- `pandas`
- `requests`
- `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`
- `python-dotenv`

**Environment variables**

Configuration is read from a `.env` file in the project root (see [.env.example](.env.example)):

| Variable | Description |
| --- | --- |
| `GOOGLE_CALENDAR_SERVICE_ACCOUNT` | Path to the Google service account JSON key file used to authenticate with the Calendar API. |
| `CALENDAR_ID` | Google Calendar ID where most events are created. |
| `CALENDAR_FAVORITE_TEAMS_ID` | Google Calendar ID where matches involving your favorite teams (see `FAVORITE_TEAMS`) are created instead. |
| `EMAIL` | Sender Gmail address used for notifications. |
| `PASSWORD` | Gmail app password for the sender account. |
| `RECEIVER` | Email address that receives notifications. |
| `APP_LOG_PATH` | Directory where the log file is written (defaults to `~/logs` if unset). |

**Google Calendar configuration (required)**

The project authenticates using a **Google service account**, not the interactive OAuth flow:

1. Enable the Google Calendar API in your Google Cloud project.
2. Create a service account and download its JSON key file.
3. Share the target calendar(s) (`CALENDAR_ID` and `CALENDAR_FAVORITE_TEAMS_ID`) with the service account's email address, granting it permission to make changes to events.
4. Set `GOOGLE_CALENDAR_SERVICE_ACCOUNT` in your `.env` to the path of the downloaded key file.

Failure to configure the service account will prevent events from being added to the calendar. See [modules/gcalendar.py](modules/gcalendar.py) for the implementation.

**Email notifications**

Email behavior is implemented in [modules/notifications.py](modules/notifications.py) and sends via Gmail's SMTP server using the `EMAIL`/`PASSWORD`/`RECEIVER` environment variables.

**Favorite teams calendar migration**

If you previously had favorite-team events created on the main `CALENDAR_ID` before the dual-calendar routing was added, use [scripts/migrate_favorite_teams_calendar.py](scripts/migrate_favorite_teams_calendar.py) to move already-indexed events over to `CALENDAR_FAVORITE_TEAMS_ID`:

```bash
python3 -m scripts.migrate_favorite_teams_calendar          # dry-run, lists what would move
python3 -m scripts.migrate_favorite_teams_calendar --apply  # actually moves the events
```

**Notes & troubleshooting**

- If VS Code reports "Import 'google.oauth2' could not be resolved", install the Google auth packages with `pip install google-auth google-auth-oauthlib google-api-python-client` or install all deps with `pip install -r requirements.txt`.
- If calendar writes fail with a permissions error, double-check the target calendar has been shared with the service account's email (from the JSON key file) with "Make changes to events" access.

---

**Adding your favorite teams**

You can customize which teams are tracked by editing the `TEAMS_URLS` dictionary in [modules/espn_scraper.py](modules/espn_scraper.py). Example — append or modify entries as needed:

```python
TEAMS_URLS = {
	"Barcelona": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/83/",
	"Real Madrid": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/86/",
	# Add your teams below (works for club or national teams):
	"My Favorite FC": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/<TEAM_ID>/",
	"Another Team": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/<TEAM_ID>/",
}

# Replace `<TEAM_ID>` with the numeric id from the ESPN team calendar URL for that club or national team.
# The trailing slash on the URL is optional; only the numeric id is used.
```

To route a team's matches to `CALENDAR_FAVORITE_TEAMS_ID` instead of the main calendar, also add its exact name (as it appears in `Local`/`Visitante`, i.e. its ESPN `displayName`) to the `FAVORITE_TEAMS` set right below `TEAMS_URLS`:

```python
FAVORITE_TEAMS = {"Barcelona", "Atlas"}
```

Example: to add a new team, open [modules/espn_scraper.py](modules/espn_scraper.py), find `TEAMS_URLS` near the top, and add a new key/value pair for the team name and its ESPN calendar URL. Save and run `python3 main.py` to include the new team's matches.
