# league_app/serializers.py

from rest_framework import serializers
from .models import Match, Team, Referee, Season

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name']

class RefereeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referee
        fields = ['id', 'name']

class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ['id', 'name', 'start_date', 'end_date']

class MatchSerializer(serializers.ModelSerializer):
    home_team = TeamSerializer()
    away_team = TeamSerializer()
    referee = RefereeSerializer()
    season = SeasonSerializer()

    class Meta:
        model = Match
        fields = '__all__'

class MatchCreateSerializer(serializers.ModelSerializer):
    home_team = serializers.CharField()
    away_team = serializers.CharField()
    referee = serializers.CharField()
    season = serializers.CharField()
    season_start_date = serializers.DateField(required=False)
    season_end_date = serializers.DateField(required=False)

    class Meta:
        model = Match
        fields = [
            'id',
            'date',
            'home_team',
            'away_team',
            'referee',
            'full_time_result',
            'half_time_result',
            'home_goals',
            'away_goals',
            'home_yellow_cards',
            'away_yellow_cards',
            'home_red_cards',
            'away_red_cards',
            'season',
            'season_start_date',
            'season_end_date',
        ]

    def validate(self, data):
        season_name = data.get('season')
        if not Season.objects.filter(name=season_name).exists():
            if not data.get('season_start_date') or not data.get('season_end_date'):
                raise serializers.ValidationError({
                    'season_start_date': 'This field is required when creating a new season.',
                    'season_end_date': 'This field is required when creating a new season.'
                })
        return data

    def create(self, validated_data):
        home_team_name = validated_data.pop('home_team')
        away_team_name = validated_data.pop('away_team')
        referee_name = validated_data.pop('referee')
        season_name = validated_data.pop('season')
        season_start_date = validated_data.pop('season_start_date', None)
        season_end_date = validated_data.pop('season_end_date', None)

        # Get or create Home Team
        home_team, created = Team.objects.get_or_create(name=home_team_name)

        # Get or create Away Team
        away_team, created = Team.objects.get_or_create(name=away_team_name)

        # Get or create Referee
        referee, created = Referee.objects.get_or_create(name=referee_name)

        # Get or create Season
        season, created = Season.objects.get_or_create(
            name=season_name,
            defaults={
                'start_date': season_start_date,
                'end_date': season_end_date,
            }
        )

        # Create Match
        match = Match.objects.create(
            home_team=home_team,
            away_team=away_team,
            referee=referee,
            season=season,
            **validated_data
        )

        return match
