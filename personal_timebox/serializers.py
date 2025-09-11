from rest_framework import serializers
from .models import *

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalCategory
        fields = ['id', 'name', 'category_type', 'color', 'icon', 'is_active']

class TaskSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    
    class Meta:
        model = PersonalTask
        fields = [
            'id', 'title', 'description', 'category', 'category_name', 'category_icon',
            'priority', 'energy_level', 'estimated_minutes', 'is_completed',
            'due_date', 'created_at'
        ]

class SessionSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)
    duration_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = PersonalTimeboxSession
        fields = [
            'id', 'task', 'task_title', 'start_time', 'end_time',
            'planned_minutes', 'actual_minutes', 'outcome', 'focus_rating',
            'energy_before', 'energy_after', 'notes', 'duration_display'
        ]

class GoalSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = PersonalGoal
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'target_hours_per_period', 'period', 'status', 'progress'
        ]
    
    def get_progress(self, obj):
        return obj.current_period_progress()