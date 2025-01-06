# league_app/urls.py

from django.urls import path
from .views import (
    HeadToHeadHistory,
    RefereeImpactAnalysis,
    DynamicLeagueStandings,
    FiercestRivalries,
    ComebackKings,
    AddMatchRecord,
    search_teams,
    search_referees,
    search_seasons,
)

urlpatterns = [
    path('teams/search/', search_teams, name='search-teams'),
    path('referees/search/', search_referees, name='search-referees'),
    path('season/search/', search_seasons, name='search-seasons'),
    path('teams/<str:team1>/vs/<str:team2>/history/', HeadToHeadHistory.as_view(), name='head-to-head-history'),
    path('referees/<str:referee>/impact/', RefereeImpactAnalysis.as_view(), name='referee-impact'),
    path('standings/', DynamicLeagueStandings.as_view(), name='dynamic-league-standings'),
    path('rivalries/', FiercestRivalries.as_view(), name='fiercest-rivalries'),
    path('teams/comebacks/', ComebackKings.as_view(), name='comeback-kings'),
    path('add-match/', AddMatchRecord.as_view(), name='add-match'),
]
