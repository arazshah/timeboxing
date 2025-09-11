from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from .models import *
from .serializers import *

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PersonalTask.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PersonalTimeboxSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PersonalCategory.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PersonalGoal.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics"""
    today = timezone.now().date()
    
    today_sessions = PersonalTimeboxSession.objects.filter(
        user=request.user, start_time__date=today
    )
    
    stats = {
        'today': {
            'sessions': today_sessions.count(),
            'minutes': today_sessions.aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0,
            'avg_focus': today_sessions.aggregate(Avg('focus_rating'))['focus_rating__avg'] or 0,
        },
        'pending_tasks': PersonalTask.objects.filter(
            user=request.user, is_completed=False
        ).count(),
        'active_goals': PersonalGoal.objects.filter(
            user=request.user, status='active'
        ).count(),
    }
    
    return Response(stats)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_stats_api(request):
    """Return analytics metrics for a given period as JSON for live updates."""
    period = request.GET.get('period', '30')
    try:
        days = int(period)
        if days <= 0:
            days = 30
    except ValueError:
        days = 30

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)

    cache_key = f"analytics:{request.user.id}:{days}:{start_date}:{end_date}"
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    sessions = PersonalTimeboxSession.objects.filter(
        user=request.user,
        start_time__date__range=[start_date, end_date]
    ).select_related('task', 'task__category')

    total_sessions = sessions.count()
    total_minutes = sessions.aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0
    avg_focus = sessions.aggregate(Avg('focus_rating'))['focus_rating__avg'] or 0
    avg_session_length = sessions.aggregate(Avg('actual_minutes'))['actual_minutes__avg'] or 0

    # Daily series
    daily = []
    current = start_date
    while current <= end_date:
        day_qs = sessions.filter(start_time__date=current)
        daily.append({
            'date': current.strftime('%Y-%m-%d'),
            'sessions': day_qs.count(),
            'minutes': day_qs.aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0,
            'avg_focus': day_qs.aggregate(Avg('focus_rating'))['focus_rating__avg'] or 0,
        })
        current += timedelta(days=1)

    # Categories
    cat_qs = PersonalCategory.objects.filter(
        user=request.user,
        personaltask__personaltimeboxsession__in=sessions
    ).annotate(
        total_minutes=Sum('personaltask__personaltimeboxsession__actual_minutes'),
        session_count=Count('personaltask__personaltimeboxsession')
    ).order_by('-total_minutes')

    categories = [
        {
            'id': c.id,
            'name': c.name,
            'color': c.color,
            'icon': c.icon,
            'total_minutes': c.total_minutes or 0,
            'session_count': c.session_count or 0,
        }
        for c in cat_qs
    ]

    payload = {
        'period': str(days),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'totals': {
            'sessions': total_sessions,
            'minutes': total_minutes,
            'hours': round(total_minutes / 60, 1),
            'avg_focus': round(avg_focus or 0, 1),
            'avg_session_length': round(avg_session_length or 0, 0),
        },
        'daily': daily,
        'categories': categories,
    }

    cache.set(cache_key, payload, timeout=5)
    return Response(payload)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def quick_stats_api(request):
    """Quick stats for real-time updates"""
    today = timezone.now().date()
    
    stats = {
        'today_sessions': PersonalTimeboxSession.objects.filter(
            user=request.user, start_time__date=today
        ).count(),
        'active_session': PersonalTimeboxSession.objects.filter(
            user=request.user, end_time__isnull=True
        ).exists(),
        'pending_tasks': PersonalTask.objects.filter(
            user=request.user, is_completed=False
        ).count(),
    }
    
    return Response(stats)