# league_app/models.py

from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class Referee(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
    
class Season(models.Model):
    name = models.CharField(max_length=9)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name



class Match(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    date = models.DateField()
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE)
    full_time_result = models.CharField(max_length=1)  # 'H', 'A', 'D'
    half_time_result = models.CharField(max_length=1, null=True, blank=True)
    home_goals = models.IntegerField()
    away_goals = models.IntegerField()
    referee = models.ForeignKey(Referee, on_delete=models.SET_NULL, null=True)
    home_yellow_cards = models.IntegerField(default=0)
    away_yellow_cards = models.IntegerField(default=0)
    home_red_cards = models.IntegerField(default=0)
    away_red_cards = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} on {self.date}"
