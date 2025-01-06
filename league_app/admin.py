# league_app/admin.py

from django.contrib import admin
from .models import Match, Team, Referee

class MatchInline(admin.TabularInline):
    model = Match
    fk_name = 'home_team'
    extra = 0

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    inlines = [MatchInline]

@admin.register(Referee)
class RefereeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'season',
        'home_team',
        'away_team',
        'full_time_result',
        'home_goals',
        'away_goals',
    )
    list_filter = (
        'season',
        'full_time_result',
    )
