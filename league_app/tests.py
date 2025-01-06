# league_app/tests.py

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from league_app.models import Team, Referee, Match, Season
from datetime import datetime

class LeagueAPITestCase(APITestCase):
    def setUp(self):
        # Sample data
        self.team1 = Team.objects.create(name="Liverpool")
        self.team2 = Team.objects.create(name="Man United")
        self.referee = Referee.objects.create(name="M Clattenburg")
        self.season = Season.objects.create(name="2024/2025", start_date="2024-08-16", end_date="2024-12-26")

        Match.objects.create(
            date="2024-12-01",
            home_team=self.team1,
            away_team=self.team2,
            referee=self.referee,
            full_time_result="H",
            half_time_result="D",
            home_goals=3,
            away_goals=1,
            season=self.season,
            home_yellow_cards=2,
            away_yellow_cards=3,
            home_red_cards=0,
            away_red_cards=1
        )

    def test_head_to_head_history_no_matches(self):
        url = reverse('head-to-head-history', args=["Arsenal", "Chelsea"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "No matches found between these teams.")

    def test_referee_impact_analysis_nonexistent_referee(self):
        url = reverse('referee-impact', args=["Unknown Referee"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "No matches found for this referee.")

    def test_dynamic_league_standings_no_matches(self):
        url = reverse('dynamic-league-standings') + "?date=01/09/2024"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "No matches found up to this date.")

    def test_add_match_validation_missing_fields(self):
        url = reverse('add-match')
        data = {
            "date": "2024-12-05",
            "home_team": "",
            "away_team": "Chelsea",
            "referee": "M Clattenburg",
            "full_time_result": "A",
            "season": "2024/2025",
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("home_team", response.data)

    def test_add_match_validation_invalid_data(self):
        url = reverse('add-match')
        data = {
            "date": "2024-12-05",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "referee": "M Clattenburg",
            "full_time_result": "A",
            "home_goals": "three",  # Invalid value
            "season": "2024/2025",
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("home_goals", response.data)

    def test_fiercest_rivalries_limit(self):
        url = reverse('fiercest-rivalries') + "?limit=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_comeback_kings_limit(self):
        url = reverse('comeback-kings') + "?limit=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 1)

    def test_dynamic_league_standings_large_dataset(self):
        for i in range(50):
            Team.objects.create(name=f"Team {i+1}")
        url = reverse('dynamic-league-standings') + "?date=01/12/2024"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["number_of_teams"], 2)

    def test_add_match_create_new_season(self):
        url = reverse('add-match')
        data = {
            "date": "2025-01-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "referee": "M Clattenburg",
            "full_time_result": "D",
            "half_time_result": "A",
            "home_goals": 2,
            "away_goals": 2,
            "season": "2025/2026",
            "season_start_date": "2025-01-01",
            "season_end_date": "2025-06-01"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["season"], "2025/2026")
