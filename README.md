# PySportsCalendar 🐍⚽️📅

PySportsCalendar scrapes match schedules from ESPN, adds upcoming matches to a Google Calendar, and sends email notifications when new events are created.

**Main features**

- Scrapes team match data from ESPN.
- Adds events to Google Calendar.
- Sends email notifications on errors or when new events are added.

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
- `beautifulsoup4`
- `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`
- `python-dotenv` (if you prefer env-based config)
- `selenium` and `undetected-chromedriver` (used by the scraper when needed)

**Google Calendar configuration (required)**

1. Enable the Google Calendar API in your Google Cloud project.
2. Create OAuth 2.0 credentials (Desktop app) and download the `credentials.json` file.
3. Place `credentials.json` in the project root directory (same folder as [main.py](main.py)).
4. On first run the app will open a browser window to authorize access and will create a `token.json` (or similar) file for subsequent runs.

Failure to configure the Google credentials will prevent events from being added to the calendar. See the calendar manager implementation in [modules/gcalendar.py](modules/gcalendar.py) for more details.

**Email notifications**

Email behavior is implemented in [modules/notifications.py](modules/notifications.py). Configure SMTP credentials or the environment variables it expects before running the bot.

**Notes & troubleshooting**

- If VS Code reports "Import 'google.oauth2' could not be resolved", install the Google auth packages with `pip install google-auth google-auth-oauthlib google-api-python-client` or install all deps with `pip install -r requirements.txt`.
- If the scraper needs a browser driver, ensure `chromedriver` or `webdriver-manager` is available (see `requirements.txt`).

---

**Adding your favorite teams**

You can customize which teams the scraper collects by editing the `TEAMS_URLS` dictionary in [modules/espn_scraper.py](modules/espn_scraper.py). Example — append or modify entries as needed:

```python
TEAMS_URLS = {
	"Barcelona": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/83/",
	"Real Madrid": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/86/",
	# Add your favorites below:
	"My Favorite FC": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/<TEAM_ID>/",
	"Another Team": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/<TEAM_ID>/",
}

# Replace `<TEAM_ID>` with the numeric id from the ESPN team calendar URL for that club or national team.
```

Example: to add a new team, open [modules/espn_scraper.py](modules/espn_scraper.py), find `TEAMS_URLS` at the top, and add a new key/value pair for the team name and its ESPN calendar URL. Save and run `python3 main.py` to include the new team's matches.
