import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

import pandas as pd
import requests

logger = logging.getLogger(__name__)

TEAMS_URLS = {
    "Barcelona": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/83/",
    "Real Madrid": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/86/",

    "Arsenal": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/359",
    "Chelsea": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/363/",
    "Liverpool": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/364",
    "Manchester City": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/382",
    "Manchester United": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/360",

    "Milan": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/103",
    "Inter": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/110",
    "Juventus": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/111",

    "Atlas": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/216",
    "Chivas": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/219",

    "Argentina": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/202",
    "Mexico": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/203",
    "Brasil": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/205",
    "Espana": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/164",
    "Francia": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/478",

    "Boca Juniors": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/5",
}


class EspnScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        self.local_tz = ZoneInfo("America/Mexico_City")
        self.lookahead_days = 180
        self.max_workers = 8
        self.team_api_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/teams/{team_id}"
        self.core_leagues_url = "https://sports.core.api.espn.com/v2/sports/soccer/leagues?page={page}&limit=100"
        self.scoreboard_api_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard?dates={date_range}"
        self.club_league_codes = {
            "esp.1",
            "esp.copa_del_rey",
            "esp.super_cup",
            "esp.joan_gamper",
            "eng.1",
            "eng.fa",
            "eng.league_cup",
            "eng.charity",
            "ita.1",
            "ita.coppa_italia",
            "ita.super_cup",
            "mex.1",
            "mex.campeon",
            "arg.1",
            "arg.copa",
            "arg.copa_de_la_superliga",
            "arg.trofeo_de_la_campeones",
            "arg.supercopa",
            "arg.supercopa.internacional",
            "uefa.champions",
            "uefa.europa",
            "uefa.europa.conf",
            "uefa.super_cup",
            "conmebol.libertadores",
            "conmebol.sudamericana",
            "conmebol.recopa",
            "concacaf.champions_cup",
            "fifa.cwc",
            "club.friendly",
        }
        self.national_league_codes = {
            "fifa.world",
            "fifa.worldq.uefa",
            "fifa.worldq.concacaf",
            "fifa.worldq.caf",
            "fifa.worldq.afc",
            "fifa.worldq.conmebol",
            "fifa.worldq.ofc",
            "fifa.worldq.afc.conmebol",
            "fifa.worldq.concacaf.ofc",
            "fifa.friendly",
            "fifa.friendly_u21",
            "fifa.olympics",
            "fifa.concacaf.olympicsq",
            "fifa.conmebol.olympicsq",
            "uefa.nations",
            "uefa.euro",
            "uefa.euroq",
            "conmebol.america",
            "concacaf.gold",
            "concacaf.gold_qual",
            "concacaf.nations.league",
            "concacaf.confederations_playoff",
        }

    def _extract_team_id(self, url):
        match = re.search(r"/id/(\d+)", url)
        if not match:
            raise ValueError(f"No se pudo extraer el team_id desde la URL: {url}")
        return match.group(1)

    def _fetch_json(self, url):
        response = requests.get(url, headers=self.headers, timeout=20)
        response.raise_for_status()
        return response.json()

    def _get_team_info(self, team_id):
        team_data = self._fetch_json(self.team_api_url.format(team_id=team_id))
        team = team_data.get("team", {})
        return {
            "id": str(team_id),
            "name": team.get("displayName", str(team_id)),
            "is_national": team.get("isNational", False),
        }

    def _get_all_league_codes(self):
        league_codes = []
        page = 1

        while True:
            data = self._fetch_json(self.core_leagues_url.format(page=page))
            for item in data.get("items", []):
                ref = item.get("$ref", "")
                match = re.search(r"/leagues/([^?]+)", ref)
                if match:
                    league_codes.append(match.group(1))

            if page >= data.get("pageCount", 1):
                break
            page += 1

        return league_codes

    def _get_relevant_league_codes(self, team_infos):
        requested_codes = set()
        has_club_teams = any(not team_info["is_national"] for team_info in team_infos)
        has_national_teams = any(team_info["is_national"] for team_info in team_infos)

        if has_club_teams:
            requested_codes.update(self.club_league_codes)
        if has_national_teams:
            requested_codes.update(self.national_league_codes)

        available_codes = set(self._get_all_league_codes())
        return sorted(requested_codes.intersection(available_codes))

    def _parse_event(self, event, competition_name, tracked_team_ids):
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])
        competitor_ids = {item.get("team", {}).get("id") for item in competitors}

        if not tracked_team_ids.intersection(competitor_ids):
            return None

        local_team = next(
            (item.get("team", {}).get("displayName") for item in competitors if item.get("homeAway") == "home"),
            None,
        )
        away_team = next(
            (item.get("team", {}).get("displayName") for item in competitors if item.get("homeAway") == "away"),
            None,
        )

        event_dt = pd.to_datetime(event.get("date"), utc=True, errors="coerce")
        if pd.isna(event_dt) or not local_team or not away_team:
            return None

        local_dt = event_dt.tz_convert(self.local_tz)
        if local_dt <= pd.Timestamp.now(tz=self.local_tz):
            return None

        if not competition.get("timeValid", event.get("timeValid", False)):
            return None

        dt_obj = local_dt.tz_localize(None).to_pydatetime()
        return {
            "Event_Id": event.get("id"),
            "Local": local_team,
            "Visitante": away_team,
            "Fecha_Obj": dt_obj,
            "Fecha_Str": dt_obj.strftime("%Y-%m-%d"),
            "Hora": dt_obj.strftime("%H:%M"),
            "Competencia": competition_name,
        }

    def _fetch_league_matches(self, league_code, tracked_team_ids, date_range):
        try:
            scoreboard_data = self._fetch_json(
                self.scoreboard_api_url.format(league_code=league_code, date_range=date_range)
            )
        except Exception:
            return []

        competition_name = scoreboard_data.get("leagues", [{}])[0].get("name", league_code)
        matches = []
        for event in scoreboard_data.get("events", []):
            parsed_event = self._parse_event(event, competition_name, tracked_team_ids)
            if parsed_event:
                matches.append(parsed_event)

        if matches:
            logger.debug("%s: %s partidos", competition_name, len(matches))
        return matches

    def get_matches(self, team_name, url):
        team_id = self._extract_team_id(url)
        team_info = self._get_team_info(team_id)
        start_date = pd.Timestamp.now(tz=self.local_tz).strftime("%Y%m%d")
        end_date = (pd.Timestamp.now(tz=self.local_tz) + pd.Timedelta(days=self.lookahead_days)).strftime("%Y%m%d")
        date_range = f"{start_date}-{end_date}"

        logger.info("Procesando equipo: %s", team_name)
        all_matches = []
        for league_code in self._get_relevant_league_codes([team_info]):
            league_matches = self._fetch_league_matches(league_code, {team_id}, date_range)
            all_matches.extend(league_matches)

        return all_matches

    def run_all(self, teams_dict):
        team_infos = [self._get_team_info(self._extract_team_id(url)) for url in teams_dict.values()]
        tracked_team_ids = {team_info["id"] for team_info in team_infos}
        start_date = pd.Timestamp.now(tz=self.local_tz).strftime("%Y%m%d")
        end_date = (pd.Timestamp.now(tz=self.local_tz) + pd.Timedelta(days=self.lookahead_days)).strftime("%Y%m%d")
        date_range = f"{start_date}-{end_date}"

        logger.info(
            "Escaneando competiciones de ESPN para %s equipos",
            len(tracked_team_ids),
        )
        league_codes = self._get_relevant_league_codes(team_infos)
        all_matches = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._fetch_league_matches, league_code, tracked_team_ids, date_range): league_code
                for league_code in league_codes
            }
            for future in as_completed(futures):
                all_matches.extend(future.result())

        if not all_matches:
            logger.warning("No se encontraron partidos confirmados")
            return pd.DataFrame()

        df = pd.DataFrame(all_matches)
        df = df.drop_duplicates(subset=["Event_Id"]).drop(columns=["Event_Id"])
        logger.debug("Se detectaron %s partidos después de limpiar duplicados", len(df))
        return df.sort_values(by=["Fecha_Obj", "Competencia", "Local", "Visitante"]).reset_index(drop=True)


if __name__ == "__main__":
    from modules.logging_config import configure_logging

    configure_logging()
    logger.info("Ejecutando scraper de ESPN en modo directo")
    scraper = EspnScraper()
    df = scraper.run_all(TEAMS_URLS)
    if df.empty:
        logger.warning("No se encontraron partidos confirmados")
    else:
        logger.debug(
            "Partidos encontrados:\n%s",
            df[["Local", "Visitante", "Fecha_Obj", "Fecha_Str", "Hora", "Competencia"]].to_string(index=False),
        )
