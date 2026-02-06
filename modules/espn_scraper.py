import requests
from bs4 import BeautifulSoup
import pandas as pd
import dateparser

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

    "Atlas": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/216",

    "Argentina": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/202",
    "Mexico": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/203",
    "Brasil": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/205",
    "Espana": "https://www.espn.com.mx/futbol/equipo/calendario/_/id/164",
}


class EspnScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'  # noqa
        }

    def get_matches(self, team_name, url):
        print(f"⚽ Procesando: {team_name}...")
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            matches = []

            # Buscamos todas las filas
            rows = soup.find_all('tr')

            for row in rows:
                cols = row.find_all('td')

                # Necesitamos filas con datos
                if len(cols) < 5:
                    continue

                # 1. Extracción de datos crudos
                date_text = cols[0].get_text(strip=True)
                local_team = cols[1].get_text(strip=True)
                away_team = cols[3].get_text(strip=True)
                time_text = cols[4].get_text(strip=True)
                competition = cols[5].get_text(strip=True) if len(cols) > 5 else "N/A"

                # 2. FILTROS
                # Ignorar encabezados o filas vacías
                if "FECHA" in date_text:
                    continue

                # Ignorar partidos sin hora definida (P.A. = Por Anunciar)
                if "P.A." in time_text or "TBD" in time_text:
                    continue

                # Si no tiene ":" o "AM/PM", probablemente es un resultado final
                if ":" not in time_text:
                    continue

                # 4. Construcción de Fecha Completa
                clean_date_text = date_text
                if "," in date_text:
                    clean_date_text = date_text.split(",")[-1].strip()

                full_date_str = f"{clean_date_text} {time_text}"

                dt_obj = dateparser.parse(full_date_str, languages=['es'])

                if dt_obj:
                    matches.append({
                        'Local': local_team,
                        'Visitante': away_team,
                        'Fecha_Obj': dt_obj,  # Objeto datetime real
                        'Fecha_Str': dt_obj.strftime("%Y-%m-%d"),
                        'Hora': dt_obj.strftime("%H:%M"),
                        'Competencia': competition
                    })

            return matches

        except Exception as e:
            print(f"❌ Error escaneando {team_name}: {e}")
            return []

    def run_all(self, teams_dict):
        all_data = []
        for team, url in teams_dict.items():
            team_matches = self.get_matches(team, url)
            all_data.extend(team_matches)

        return pd.DataFrame(all_data)


if __name__ == "__main__":
    scraper = EspnScraper()
    df = scraper.run_all(TEAMS_URLS)

    print("\n--- 📅 PARTIDOS ENCONTRADOS ---")
    if not df.empty:
        print(df[['Local', 'Visitante', 'Fecha_Obj', 'Fecha_Str', 'Hora', 'Competencia']])
    else:
        print("⚠️ No se encontraron partidos confirmados (o todos están como P.A.).")
