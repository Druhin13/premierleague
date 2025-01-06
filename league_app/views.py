# league_app/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Sum, Avg
from django.http import JsonResponse
from django.shortcuts import render
from collections import defaultdict
from datetime import datetime
from fuzzywuzzy import process

from .models import Team, Referee, Match, Season
from .serializers import TeamSerializer, RefereeSerializer, MatchSerializer, MatchCreateSerializer

# -----------------------------
# Helper Functions
# -----------------------------

def extract_seasons():
    """
    Extracts all seasons based on contiguous match dates.
    A new season starts if there is a gap of more than 90 days between matches.
    """
    matches = Match.objects.order_by('date').values_list('date', flat=True)
    seasons = []
    current_season = {}
    season_id = 1

    for match_date in matches:
        if not current_season:
            current_season = {
                'season_id': season_id,
                'start_date': match_date,
                'end_date': match_date
            }
        else:
            gap = (match_date - current_season['end_date']).days
            if gap > 90:
                seasons.append(current_season)
                season_id += 1
                current_season = {
                    'season_id': season_id,
                    'start_date': match_date,
                    'end_date': match_date
                }
            else:
                current_season['end_date'] = match_date

    if current_season:
        seasons.append(current_season)

    return seasons

def find_season(seasons, selected_date):
    """
    Finds the season that includes the selected_date.
    Returns the season dictionary or None if not found.
    """
    for season in seasons:
        if season['start_date'] <= selected_date <= season['end_date']:
            return season
    return None

# -----------------------------
# API Views
# -----------------------------

class HeadToHeadHistory(APIView):
    def get(self, request, team1, team2):
        matches = Match.objects.filter(
            (Q(home_team__name=team1) & Q(away_team__name=team2)) |
            (Q(home_team__name=team2) & Q(away_team__name=team1))
        )
        if not matches.exists():
            return Response(
                {"detail": "No matches found between these teams."},
                status=status.HTTP_404_NOT_FOUND
            )

        team1_wins = 0
        team2_wins = 0
        draws = 0
        team1_goals = 0
        team2_goals = 0

        for match in matches:
            if match.home_team.name == team1:
                team1_goals += match.home_goals
                team2_goals += match.away_goals

                if match.full_time_result == 'H':
                    team1_wins += 1
                elif match.full_time_result == 'A':
                    team2_wins += 1
                else:
                    draws += 1

            else:
                team1_goals += match.away_goals
                team2_goals += match.home_goals

                if match.full_time_result == 'H':
                    team2_wins += 1
                elif match.full_time_result == 'A':
                    team1_wins += 1
                else:
                    draws += 1

        total_matches = matches.count()

        average_goals_team1 = (team1_goals / total_matches) if total_matches else 0
        average_goals_team2 = (team2_goals / total_matches) if total_matches else 0

        data = {
            "team1": team1,
            "team2": team2,
            "total_matches": total_matches,
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "draws": draws,
            "total_goals_team1": team1_goals,
            "total_goals_team2": team2_goals,
            "average_goals_team1": round(average_goals_team1, 2),
            "average_goals_team2": round(average_goals_team2, 2),
        }
        return Response(data, status=status.HTTP_200_OK)


class RefereeImpactAnalysis(APIView):
    def get(self, request, referee):
        matches = Match.objects.filter(referee__name=referee)
        if not matches.exists():
            return Response({"detail": "No matches found for this referee."},
                            status=status.HTTP_404_NOT_FOUND)

        total_matches = matches.count()
        avg_yellow_home = matches.aggregate(avg=Avg('home_yellow_cards'))['avg'] or 0
        avg_yellow_away = matches.aggregate(avg=Avg('away_yellow_cards'))['avg'] or 0
        avg_red_home = matches.aggregate(avg=Avg('home_red_cards'))['avg'] or 0
        avg_red_away = matches.aggregate(avg=Avg('away_red_cards'))['avg'] or 0

        home_wins = matches.filter(full_time_result='H').count()
        away_wins = matches.filter(full_time_result='A').count()
        draws = matches.filter(full_time_result='D').count()

        home_win_rate = (home_wins / total_matches) * 100
        away_win_rate = (away_wins / total_matches) * 100
        draw_rate = (draws / total_matches) * 100

        data = {
            "referee": referee,
            "average_yellow_cards_home": round(avg_yellow_home, 2),
            "average_yellow_cards_away": round(avg_yellow_away, 2),
            "average_red_cards_home": round(avg_red_home, 2),
            "average_red_cards_away": round(avg_red_away, 2),
            "home_win_rate": round(home_win_rate, 2),
            "away_win_rate": round(away_win_rate, 2),
            "draw_rate": round(draw_rate, 2),
        }
        return Response(data, status=status.HTTP_200_OK)

class DynamicLeagueStandings(APIView):
    def get(self, request):
        date_str = request.query_params.get('date', None)
        if not date_str:
            return Response({"detail": "Date parameter is required in format dd/mm/yyyy."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            selected_date = datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            return Response({"detail": "Invalid date format. Use dd/mm/yyyy."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            current_season = Season.objects.get(
                start_date__lte=selected_date, end_date__gte=selected_date
            )
        except Season.DoesNotExist:
            return Response({"detail": "No season found for the selected date."},
                            status=status.HTTP_404_NOT_FOUND)

        matches = Match.objects.filter(season=current_season, date__lte=selected_date)
        if not matches.exists():
            return Response({"detail": "No matches found up to this date."},
                            status=status.HTTP_404_NOT_FOUND)

        # Check team count
        unique_home_teams = matches.values_list('home_team__name', flat=True).distinct()
        unique_away_teams = matches.values_list('away_team__name', flat=True).distinct()
        unique_teams = set(unique_home_teams).union(set(unique_away_teams))
        number_of_teams = len(unique_teams)


        # Calculate standings
        standings = defaultdict(lambda: {
            "points": 0,
            "goal_difference": 0,
            "goals_scored": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "goals_conceded": 0
        })

        for match in matches:
            home_team = match.home_team.name
            away_team = match.away_team.name
            home_goals = match.home_goals
            away_goals = match.away_goals
            result = match.full_time_result

            # Update goals scored and conceded
            standings[home_team]["goals_scored"] += home_goals
            standings[home_team]["goals_conceded"] += away_goals
            standings[away_team]["goals_scored"] += away_goals
            standings[away_team]["goals_conceded"] += home_goals

            # Update goal difference
            standings[home_team]["goal_difference"] += (home_goals - away_goals)
            standings[away_team]["goal_difference"] += (away_goals - home_goals)

            # Update points and W/L/D
            if result == 'H':
                standings[home_team]["points"] += 3
                standings[home_team]["wins"] += 1
                standings[away_team]["losses"] += 1
            elif result == 'A':
                standings[away_team]["points"] += 3
                standings[away_team]["wins"] += 1
                standings[home_team]["losses"] += 1
            else:  # Draw
                standings[home_team]["points"] += 1
                standings[away_team]["points"] += 1
                standings[home_team]["draws"] += 1
                standings[away_team]["draws"] += 1

        standings_list = []
        for team, stats in standings.items():
            standings_list.append({
                "team": team,
                "points": stats["points"],
                "goal_difference": stats["goal_difference"],
                "goals_scored": stats["goals_scored"],
                "wins": stats["wins"],
                "losses": stats["losses"],
                "draws": stats["draws"],
                "goals_conceded": stats["goals_conceded"],
            })

        standings_sorted = sorted(
            standings_list,
            key=lambda x: (-x["points"], -x["goal_difference"], -x["goals_scored"])
        )

        for idx, team in enumerate(standings_sorted, start=1):
            team["rank"] = idx

        response_data = {
            "season_id": current_season.id,
            "season_name": current_season.name,
            "season_start_date": current_season.start_date,
            "season_end_date": current_season.end_date,
            "number_of_teams": number_of_teams,
            "standings": standings_sorted
        }
        return Response(response_data, status=status.HTTP_200_OK)

class FiercestRivalries(APIView):
    def get(self, request):
        # Aggregate rivalry data
        all_matches = Match.objects.all()
        rivalry_dict = {}

        for match in all_matches:
            teams = sorted([match.home_team.name, match.away_team.name])
            key = f"{teams[0]} vs {teams[1]}"
            if key not in rivalry_dict:
                rivalry_dict[key] = {"yellow_cards": 0, "red_cards": 0}
            rivalry_dict[key]["yellow_cards"] += (match.home_yellow_cards + match.away_yellow_cards)
            rivalry_dict[key]["red_cards"] += (match.home_red_cards + match.away_red_cards)

        rivalry_list = []
        for rivalry, cards in rivalry_dict.items():
            intensity_score = cards["yellow_cards"] + 2 * cards["red_cards"]
            rivalry_list.append({
                "rivalry": rivalry,
                "total_yellow_cards": cards["yellow_cards"],
                "total_red_cards": cards["red_cards"],
                "intensity_score": intensity_score
            })

        rivalry_sorted = sorted(rivalry_list, key=lambda x: -x["intensity_score"])

        # Apply the limit parameter if provided
        limit = request.query_params.get('limit', None)
        if limit:
            try:
                limit = int(limit)
                rivalry_sorted = rivalry_sorted[:limit]
            except ValueError:
                return Response({"detail": "Limit must be an integer."},
                                status=status.HTTP_400_BAD_REQUEST)

        return Response(rivalry_sorted, status=status.HTTP_200_OK)


class ComebackKings(APIView):
    def get(self, request):
        # Filter matches that had a comeback
        matches = Match.objects.filter(
            ~Q(half_time_result='D') & ~Q(full_time_result='D') &
            (
                (Q(half_time_result='A') & Q(full_time_result='H')) |
                (Q(half_time_result='H') & Q(full_time_result='A'))
            )
        )
        comebacks = defaultdict(int)
        for match in matches:
            if match.half_time_result == 'A' and match.full_time_result == 'H':
                comebacks[match.home_team.name] += 1
            elif match.half_time_result == 'H' and match.full_time_result == 'A':
                comebacks[match.away_team.name] += 1

        comeback_list = [
            {"team": team, "comebacks": count} for team, count in comebacks.items()
        ]
        comeback_sorted = sorted(comeback_list, key=lambda x: -x["comebacks"])

        # Apply the limit parameter if provided
        limit = request.query_params.get('limit', None)
        if limit:
            try:
                limit = int(limit)
                comeback_sorted = comeback_sorted[:limit]
            except ValueError:
                return Response({"detail": "Limit must be an integer."},
                                status=status.HTTP_400_BAD_REQUEST)

        return Response(comeback_sorted, status=status.HTTP_200_OK)


class AddMatchRecord(APIView):
    def post(self, request):
        serializer = MatchCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# -----------------------------
# Search Endpoints (Autocomplete)
# -----------------------------

def search_teams(request):
    query = request.GET.get('search', '').lower()
    if not query:
        return JsonResponse({"results": []})

    # Fetch all team names
    all_teams = list(Team.objects.values_list('name', flat=True))

    # Use fuzzy matching to find top 10
    matched_teams = process.extract(query, all_teams, limit=10)
    # Only return matches with a score >= 60
    results = [team for team, score in matched_teams if score >= 60]
    return JsonResponse({"results": results})

def search_referees(request):
    query = request.GET.get('search', '').lower()
    if not query:
        return JsonResponse({"results": []})

    # Fetch all referee names
    all_referees = list(Referee.objects.values_list('name', flat=True))

    # Use fuzzy matching to find top 10
    matched_refs = process.extract(query, all_referees, limit=10)
    results = [ref for ref, score in matched_refs if score >= 60]
    return JsonResponse({"results": results})

def search_seasons(request):
    query = request.GET.get('search', '').lower()
    if not query:
        return JsonResponse({"results": []})

    # Fetch all season names
    all_seasons = list(Season.objects.values_list('name', flat=True))

    # Use fuzzy matching to find top 10
    matched_seasons = process.extract(query, all_seasons, limit=10)
    # Only return matches with a score >= 60
    results = [season for season, score in matched_seasons if score >= 60]
    return JsonResponse({"results": results})

# -----------------------------
# Homepage View
# -----------------------------

def homepage(request):
    min_date_str = ""
    max_date_str = ""

    oldest_match = Match.objects.order_by('date').first()
    newest_match = Match.objects.order_by('-date').first()

    if oldest_match and newest_match:
        min_date_str = oldest_match.date.strftime('%Y-%m-%d')
        max_date_str = newest_match.date.strftime('%Y-%m-%d')

    # Fetch all seasons to populate the dropdown in the form
    seasons = Season.objects.all().order_by('start_date')

    endpoints = [
        {
            "name": "Swagger Documentation",
            "url": "/swagger/",
            "description": "Interactive API documentation generated using Swagger UI.",
            "method": "GET",
            "parameters": [],
            "sample_request": "GET /swagger/",
            "sample_response": "Displays the Swagger UI."
        },
        {
            "name": "Head-to-Head Historical Statistics",
            "url": "/api/teams/<team1>/vs/<team2>/history",
            "description": "Analysis of matches between two teams.",
            "method": "GET",
            "parameters": [
                {
                    "name": "team1",
                    "type": "path",
                    "required": True,
                    "description": "Name of the first team."
                },
                {
                    "name": "team2",
                    "type": "path",
                    "required": True,
                    "description": "Name of the second team."
                },
            ],
            "sample_request": "GET /api/teams/Liverpool/vs/Manchester%20United/history",
            "sample_response": """{
    "team1": "Liverpool",
    "team2": "Man United",
    "total_matches": 63,
    "team1_wins": 20,
    "team2_wins": 28,
    "draws": 15,
    "total_goals_team1": 86,
    "total_goals_team2": 79,
    "average_goals_team1": 1.37,
    "average_goals_team2": 1.25
}"""
        },
        {
            "name": "Referee Impact Analysis",
            "url": "/api/referees/<referee>/impact",
            "description": "Analyzes the influence of a referee on match outcomes.",
            "method": "GET",
            "parameters": [
                {
                    "name": "referee",
                    "type": "path",
                    "required": True,
                    "description": "Name of the referee."
                },
            ],
            "sample_request": "GET /api/referees/Mark%20Clattenburg/impact",
            "sample_response": """{
    "referee": "M Clattenburg",
    "average_yellow_cards_home": 1.48,
    "average_yellow_cards_away": 1.77,
    "average_red_cards_home": 0.1,
    "average_red_cards_away": 0.06,
    "home_win_rate": 47.1,
    "away_win_rate": 26.96,
    "draw_rate": 25.94
}"""
        },
        {
            "name": "Dynamic League Standings",
            "url": "/api/standings?date=<date>",
            "description": "Fetches league standings as of a specific date.",
            "method": "GET",
            "parameters": [
                {
                    "name": "date",
                    "type": "query",
                    "required": True,
                    "description": "Date in dd/mm/yyyy format."
                },
            ],
            "sample_request": "GET /api/standings?date=11/12/2024",
            "sample_response": """{
    "season_id": 21,
    "season_name": "2024/2025",
    "season_start_date": "2024-08-16",
    "season_end_date": "2024-12-26",
    "number_of_teams": 22,
    "standings": [
        {
            "team": "Liverpool",
            "points": 34,
            "goal_difference": 18,
            "goals_scored": 26,
            "wins": 10,
            "losses": 5,
            "draws": 3,
            "goals_conceded": 8,
            "rank": 1
        },
        {
            "team": "Arsenal",
            "points": 25,
            "goal_difference": 12,
            "goals_scored": 26,
            "wins": 7,
            "losses": 6,
            "draws": 4,
            "goals_conceded": 14,
            "rank": 2
        },
    ...
}"""
        },
        {
            "name": "Fiercest Rivalries",
            "url": "/api/rivalries?limit=<limit>",
            "description": "Identifies the most intense rivalries.",
            "method": "GET",
            "parameters": [
                {
                    "name": "limit",
                    "type": "query",
                    "required": False,
                    "description": "Max number of results to show."
                }
            ],
            "sample_request": "GET /api/rivalries?limit=5",
            "sample_response": """[
    {
        "rivalry": "Chelsea vs Man United",
        "total_yellow_cards": 237,
        "total_red_cards": 8,
        "intensity_score": 253
    },
    {
        "rivalry": "Everton vs Liverpool",
        "total_yellow_cards": 199,
        "total_red_cards": 18,
        "intensity_score": 235
    },
    ...
]"""
        },
        {
            "name": "Comeback Kings / Clutch Teams",
            "url": "/api/teams/comebacks?limit=<limit>",
            "description": "Teams with the most come-from-behind victories.",
            "method": "GET",
            "parameters": [
                {
                    "name": "limit",
                    "type": "query",
                    "required": False,
                    "description": "Max number of results to show."
                }
            ],
            "sample_request": "GET /api/teams/comebacks?limit=5",
            "sample_response": """[
    {
        "team": "Tottenham",
        "comebacks": 39
    },
    {
        "team": "Man United",
        "comebacks": 39
    },
    ...
]"""
        },
        {
            "name": "Add Match Record",
            "url": "/api/add-match/",
            "description": "Creates a new match record in the database.",
            "method": "POST",
            "parameters": [
                {
                    "name": "date",
                    "type": "body",
                    "required": True,
                    "description": "Date of the match in dd/mm/yyyy format."
                },
                {
                    "name": "home_team",
                    "type": "body",
                    "required": True,
                    "description": "Name of the home team."
                },
                {
                    "name": "away_team",
                    "type": "body",
                    "required": True,
                    "description": "Name of the away team."
                },
                {
                    "name": "referee",
                    "type": "body",
                    "required": True,
                    "description": "Name of the referee."
                },
                {
                    "name": "full_time_result",
                    "type": "body",
                    "required": True,
                    "description": "Full-time result: 'H' for home win, 'A' for away win, 'D' for draw."
                },
                {
                    "name": "half_time_result",
                    "type": "body",
                    "required": False,
                    "description": "Half-time result: 'H' for home leading, 'A' for away leading, 'D' for draw."
                },
                {
                    "name": "home_goals",
                    "type": "body",
                    "required": True,
                    "description": "Number of goals scored by the home team."
                },
                {
                    "name": "away_goals",
                    "type": "body",
                    "required": True,
                    "description": "Number of goals scored by the away team."
                },
                {
                    "name": "home_yellow_cards",
                    "type": "body",
                    "required": False,
                    "description": "Number of yellow cards for the home team."
                },
                {
                    "name": "away_yellow_cards",
                    "type": "body",
                    "required": False,
                    "description": "Number of yellow cards for the away team."
                },
                {
                    "name": "home_red_cards",
                    "type": "body",
                    "required": False,
                    "description": "Number of red cards for the home team."
                },
                {
                    "name": "away_red_cards",
                    "type": "body",
                    "required": False,
                    "description": "Number of red cards for the away team."
                },
                {
                    "name": "season",
                    "type": "body",
                    "required": True,
                    "description": "Season identifier (e.g., '2024/2025')."
                },
                {
                    "name": "season_start_date",
                    "type": "body",
                    "required": False,
                    "description": "Start date of the season in yyyy-mm-dd format. Required if creating a new season."
                },
                {
                    "name": "season_end_date",
                    "type": "body",
                    "required": False,
                    "description": "End date of the season in yyyy-mm-dd format. Required if creating a new season."
                },
            ],
            "sample_request": "POST /api/add-match/",
            "sample_response": """{
    "id": 1234,
    "date": "2024-11-23",
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "referee": "Mark Clattenburg",
    "full_time_result": "H",
    "half_time_result": "A",
    "home_goals": 3,
    "away_goals": 2,
    "home_yellow_cards": 2,
    "away_yellow_cards": 3,
    "home_red_cards": 0,
    "away_red_cards": 1,
    "season": "2024/2025",
    "season_start_date": "2024-08-16",
    "season_end_date": "2024-12-26"
}"""
        },
    ]

    return render(
        request,
        'homepage.html',
        {
            "endpoints": endpoints,
            "min_date_str": min_date_str,
            "max_date_str": max_date_str,
            "seasons": seasons,
        }
    )
