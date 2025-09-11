from django.utils import timezone
from datetime import timedelta
from .models import UserPreferences, PersonalTimeboxSession

def get_productivity_insights(user, days=30):
    """Generate productivity insights for a user"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    sessions = PersonalTimeboxSession.objects.filter(
        user=user,
        start_time__date__range=[start_date, end_date]
    )
    
    insights = {
        'total_sessions': sessions.count(),
        'total_hours': (sessions.aggregate(models.Sum('actual_minutes'))['actual_minutes__sum'] or 0) / 60,
        'avg_focus_rating': sessions.aggregate(models.Avg('focus_rating'))['focus_rating__avg'] or 0,
        'most_productive_hour': get_most_productive_hour(sessions),
        'best_focus_day': get_best_focus_day(sessions),
        'completion_rate': calculate_completion_rate(sessions),
    }
    
    return insights

def get_most_productive_hour(sessions):
    """Find the hour with highest average focus rating"""
    from django.db.models import Avg
    
    hourly_focus = {}
    for hour in range(24):
        hour_sessions = sessions.filter(start_time__hour=hour)
        if hour_sessions.exists():
            avg_focus = hour_sessions.aggregate(Avg('focus_rating'))['focus_rating__avg']
            hourly_focus[hour] = avg_focus or 0
    
    if hourly_focus:
        best_hour = max(hourly_focus, key=hourly_focus.get)
        return f"{best_hour:02d}:00"
    return "No data"

def get_best_focus_day(sessions):
    """Find the day of week with highest average focus"""
    from django.db.models import Avg
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_focus = {}
    
    for i, day in enumerate(days):
        day_sessions = sessions.filter(start_time__week_day=i+2)  # Django week_day starts from 1=Sunday
        if day_sessions.exists():
            avg_focus = day_sessions.aggregate(Avg('focus_rating'))['focus_rating__avg']
            daily_focus[day] = avg_focus or 0
    
    if daily_focus:
        return max(daily_focus, key=daily_focus.get)
    return "No data"

def calculate_completion_rate(sessions):
    """Calculate percentage of successfully completed sessions"""
    if not sessions.exists():
        return 0
    
    completed = sessions.filter(outcome='completed').count()
    total = sessions.count()
    return (completed / total) * 100

def calculate_break_duration(user, session):
    """Calculate appropriate break duration based on session and user preferences"""
    try:
        preferences = UserPreferences.objects.get(user=user)
        
        # Base break duration
        base_break = preferences.default_break_duration
        
        # Adjust based on session length
        if session.actual_minutes > 60:
            break_duration = preferences.long_break_duration
        else:
            break_duration = base_break
        
        # Adjust based on focus rating
        if session.focus_rating:
            if session.focus_rating >= 4:
                break_duration = max(3, break_duration - 2)  # Shorter break for high focus
            elif session.focus_rating <= 2:
                break_duration += 3  # Longer break for low focus
        
        return max(3, min(30, break_duration))  # Between 3-30 minutes
        
    except UserPreferences.DoesNotExist:
        return 5  # Default 5 minutes

def get_session_streak(user):
    """Calculate current daily session streak"""
    from django.db.models import Count
    
    current_date = timezone.now().date()
    streak = 0
    
    while True:
        day_sessions = PersonalTimeboxSession.objects.filter(
            user=user,
            start_time__date=current_date
        ).count()
        
        if day_sessions > 0:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    return streak

def format_duration(minutes):
    """Format minutes into human readable duration"""
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes == 0:
        return f"{hours}h"
    else:
        return f"{hours}h {remaining_minutes}m"

def get_productivity_score(session):
    """Calculate a comprehensive productivity score for a session"""
    if not session.focus_rating:
        return 0
    
    # Base score from focus rating (0-40 points)
    focus_score = (session.focus_rating / 5) * 40
    
    # Time efficiency score (0-30 points)
    if session.actual_minutes and session.planned_minutes:
        efficiency = min(1.0, session.planned_minutes / session.actual_minutes)
        efficiency_score = efficiency * 30
    else:
        efficiency_score = 0
    
    # Outcome score (0-30 points)
    outcome_scores = {
        'completed': 30,
        'partial': 20,
        'interrupted': 10,
        'abandoned': 0
    }
    outcome_score = outcome_scores.get(session.outcome, 0)
    
    total_score = focus_score + efficiency_score + outcome_score
    return min(100, max(0, total_score))

def get_weekly_summary(user, week_start=None):
    """Generate weekly productivity summary"""
    if not week_start:
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
    
    week_end = week_start + timedelta(days=6)
    
    sessions = PersonalTimeboxSession.objects.filter(
        user=user,
        start_time__date__range=[week_start, week_end]
    )
    
    summary = {
        'week_start': week_start,
        'week_end': week_end,
        'total_sessions': sessions.count(),
        'total_minutes': sessions.aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0,
        'avg_focus': sessions.aggregate(Avg('focus_rating'))['focus_rating__avg'] or 0,
        'completion_rate': calculate_completion_rate(sessions),
        'daily_breakdown': []
    }
    
    # Daily breakdown
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_sessions = sessions.filter(start_time__date=day)
        summary['daily_breakdown'].append({
            'date': day,
            'sessions': day_sessions.count(),
            'minutes': day_sessions.aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0,
            'avg_focus': day_sessions.aggregate(Avg('focus_rating'))['focus_rating__avg'] or 0,
        })
    
    return summary

def suggest_optimal_session_length(user, task=None):
    """Suggest optimal session length based on historical data"""
    from django.db.models import Avg, Q
    
    # Get user's historical sessions
    sessions = PersonalTimeboxSession.objects.filter(
        user=user,
        focus_rating__gte=4,  # Only high-focus sessions
        outcome='completed'
    )
    
    # Filter by task category if provided
    if task and task.category:
        sessions = sessions.filter(task__category=task.category)
    
    # Filter by energy level if provided
    if task and task.energy_level:
        energy_mapping = {'low': [1, 2], 'medium': [3], 'high': [4, 5]}
        energy_range = energy_mapping.get(task.energy_level, [3])
        sessions = sessions.filter(energy_before__in=energy_range)
    
    if sessions.exists():
        avg_duration = sessions.aggregate(Avg('actual_minutes'))['actual_minutes__avg']
        # Round to nearest 5 minutes
        suggested = round(avg_duration / 5) * 5
        return max(15, min(120, suggested))  # Between 15-120 minutes
    
    # Default suggestions based on task energy level
    if task:
        defaults = {'low': 45, 'medium': 25, 'high': 60}
        return defaults.get(task.energy_level, 25)
    
    return 25  # Default pomodoro length

def get_distraction_patterns(user, days=30):
    """Analyze common distraction patterns"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    sessions = PersonalTimeboxSession.objects.filter(
        user=user,
        start_time__date__range=[start_date, end_date],
        distractions__isnull=False
    ).exclude(distractions='')
    
    # Common distraction keywords
    distraction_keywords = [
        'phone', 'notification', 'email', 'social media', 'noise',
        'interruption', 'meeting', 'call', 'message', 'hungry',
        'tired', 'thoughts', 'worry', 'procrastination'
    ]
    
    distraction_counts = {}
    for keyword in distraction_keywords:
        count = sessions.filter(
            distractions__icontains=keyword
        ).count()
        if count > 0:
            distraction_counts[keyword] = count
    
    # Sort by frequency
    sorted_distractions = sorted(
        distraction_counts.items(), 
        key=lambda x: x[1], 
        reverse=True
    )
    
    return sorted_distractions[:5]  # Top 5 distractions

def generate_productivity_tips(user):
    """Generate personalized productivity tips based on user data"""
    insights = get_productivity_insights(user, days=14)
    tips = []
    
    # Low focus rating tips
    if insights['avg_focus_rating'] < 3:
        tips.append({
            'type': 'focus',
            'title': 'Improve Your Focus',
            'message': 'Your average focus rating is below 3. Try eliminating distractions before starting sessions.',
            'action': 'Turn off notifications and find a quiet workspace.'
        })
    
    # Session frequency tips
    if insights['total_sessions'] < 20:  # Less than ~1.5 sessions per day
        tips.append({
            'type': 'frequency',
            'title': 'Increase Session Frequency',
            'message': 'You could benefit from more regular timeboxing sessions.',
            'action': 'Try to complete at least 2-3 focused sessions per day.'
        })
    
    # Break reminders
    user_prefs = getattr(user, 'userpreferences', None)
    if user_prefs and not user_prefs.break_reminders:
        tips.append({
            'type': 'breaks',
            'title': 'Enable Break Reminders',
            'message': 'Regular breaks can improve your overall productivity.',
            'action': 'Enable break reminders in your preferences.'
        })
    
    # Goal setting
    active_goals = user.personalgoal_set.filter(status='active').count()
    if active_goals == 0:
        tips.append({
            'type': 'goals',
            'title': 'Set Some Goals',
            'message': 'Having clear goals can increase motivation and focus.',
            'action': 'Create 1-2 specific, measurable goals for this week.'
        })
    
    return tips[:3]  # Return top 3 tips

def calculate_energy_patterns(user, days=30):
    """Analyze energy level patterns throughout the day"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    sessions = PersonalTimeboxSession.objects.filter(
        user=user,
        start_time__date__range=[start_date, end_date],
        energy_before__isnull=False
    )
    
    hourly_energy = {}
    for hour in range(24):
        hour_sessions = sessions.filter(start_time__hour=hour)
        if hour_sessions.exists():
            avg_energy = hour_sessions.aggregate(
                Avg('energy_before')
            )['energy_before__avg']
            hourly_energy[hour] = round(avg_energy, 1)
    
    # Find peak energy hours
    if hourly_energy:
        peak_hours = [
            hour for hour, energy in hourly_energy.items() 
            if energy >= max(hourly_energy.values()) - 0.5
        ]
        return {
            'hourly_energy': hourly_energy,
            'peak_hours': peak_hours,
            'best_time': f"{min(peak_hours):02d}:00-{max(peak_hours)+1:02d}:00" if peak_hours else "No data"
        }
    
    return {'hourly_energy': {}, 'peak_hours': [], 'best_time': 'No data'}