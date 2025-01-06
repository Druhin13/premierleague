# load_data.py

import os
import django
import pandas as pd
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'premier_league_project.settings')
django.setup()

from league_app.models import Team, Referee, Match, Season

DATA_DIR = os.path.join(os.path.dirname(__file__), 'league_app', 'data')

def load_data():
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.csv'):
            filepath = os.path.join(DATA_DIR, filename)
            df = pd.read_csv(filepath)
            
            # Replace NaN with 0 for numeric columns
            numeric_columns = ['HY', 'AY', 'HR', 'AR', 'FTHG', 'FTAG']
            for col in numeric_columns:
                if col in df.columns:
                    df[col].fillna(0, inplace=True)
                else:
                    print(f"Column {col} not found in {filename}. Filling with 0.")
                    df[col] = 0

            # Extract season name from the filename
            season_name = filename.split('.')[0]  # e.g., "season_9900"
            try:
                year_part = ''.join(filter(str.isdigit, season_name))
                if len(year_part) >= 4:
                    start_year = int(year_part[-4:-2])
                    start_year += 2000 if start_year < 50 else 1900
                elif len(year_part) == 2:
                    start_year = int(year_part)
                    start_year += 2000 if start_year < 50 else 1900
                else:
                    raise ValueError("Unexpected season name format.")
                end_year = start_year + 1
            except Exception as e:
                print(f"Error parsing season name from {filename}: {e}")
                continue

            # Dynamically calculate the start and end dates for the season
            try:
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, infer_datetime_format=True)
                season_start_date = df['Date'].min().date()
                season_end_date = df['Date'].max().date()
            except Exception as e:
                print(f"Error processing dates in {filename}: {e}")
                continue

            # Get or create the Season record
            season, created = Season.objects.get_or_create(
                name=f"{start_year}/{end_year}",
                defaults={
                    "start_date": season_start_date,
                    "end_date": season_end_date,
                }
            )
            if created:
                print(f"Created new season: {season.name}")

            for _, row in df.iterrows():
                try:
                    match_date = row['Date'].date()  # Use the parsed date column
                except ValueError as e:
                    print(f"Skipping row due to date format error: {row['Date']} - {e}")
                    continue

                # Handle potential missing columns
                home_team_name = row.get('HomeTeam')
                away_team_name = row.get('AwayTeam')
                referee_name = row.get('Referee', 'Unknown Referee')

                if not home_team_name or not away_team_name:
                    print(f"Skipping row due to missing team names: {row}")
                    continue

                home_team, _ = Team.objects.get_or_create(name=home_team_name)
                away_team, _ = Team.objects.get_or_create(name=away_team_name)
                referee, _ = Referee.objects.get_or_create(name=referee_name)

                full_time_result = row.get('FTR', 'D')  # Default to 'D' if missing
                half_time_result = row.get('HTR', 'D')  # Default to 'D' if missing

                # Ensure numeric fields are integers
                try:
                    home_goals = int(row.get('FTHG', 0))
                    away_goals = int(row.get('FTAG', 0))
                    home_yellow_cards = int(row.get('HY', 0))
                    away_yellow_cards = int(row.get('AY', 0))
                    home_red_cards = int(row.get('HR', 0))
                    away_red_cards = int(row.get('AR', 0))
                except ValueError as e:
                    print(f"Skipping row due to invalid numeric data: {row} - {e}")
                    continue

                # Create or update the Match record
                match, created = Match.objects.update_or_create(
                    date=match_date,
                    home_team=home_team,
                    away_team=away_team,
                    defaults={
                        'full_time_result': full_time_result,
                        'half_time_result': half_time_result,
                        'home_goals': home_goals,
                        'away_goals': away_goals,
                        'referee': referee,
                        'home_yellow_cards': home_yellow_cards,
                        'away_yellow_cards': away_yellow_cards,
                        'home_red_cards': home_red_cards,
                        'away_red_cards': away_red_cards,
                        'season': season,
                    }
                )
                if created:
                    print(f"Created match: {match}")
                else:
                    print(f"Updated match: {match}")

    print("Data loading complete.")

if __name__ == '__main__':
    load_data()
