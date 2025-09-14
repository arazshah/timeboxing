from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
import uuid

class PersonalCategory(models.Model):
    CATEGORY_TYPES = [
        ('work', _('Work & Career')),
        ('health', _('Health & Fitness')),
        ('learning', _('Learning & Development')),
        ('personal', _('Personal Life')),
        ('hobbies', _('Hobbies & Interests')),
        ('finance', _('Finance & Money')),
        ('relationships', _('Relationships')),
        ('spirituality', _('Spirituality & Mindfulness')),
        ('travel', _('Travel & Adventure')),
        ('other', _('Other')),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default='other')
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3498db', help_text='Hex color code')
    icon = models.CharField(max_length=50, default='📋', help_text='Emoji or icon class')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Personal Categories'
        unique_together = ['user', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.icon} {self.name}"
    
    def total_time_today(self):
        today = timezone.now().date()
        return self.personaltask_set.filter(
            personaltimeboxsession__start_time__date=today
        ).aggregate(
            total=models.Sum('personaltimeboxsession__actual_minutes')
        )['total'] or 0
    
    def total_sessions_today(self):
        today = timezone.now().date()
        return self.personaltask_set.filter(
            personaltimeboxsession__start_time__date=today
        ).count()

class PersonalGoal(models.Model):
    PERIOD_CHOICES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('yearly', _('Yearly')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('paused', _('Paused')),
        ('completed', _('Completed')),
        ('abandoned', _('Abandoned')),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(PersonalCategory, on_delete=models.CASCADE)
    target_hours_per_period = models.DecimalField(max_digits=5, decimal_places=1)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='weekly')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def current_period_progress(self):
        """Calculate progress percentage for current period"""
        now = timezone.now()
        
        if self.period == 'daily':
            start_date = now.date()
            end_date = start_date
        elif self.period == 'weekly':
            start_date = now.date() - timedelta(days=now.weekday())
            end_date = start_date + timedelta(days=6)
        elif self.period == 'monthly':
            start_date = now.date().replace(day=1)
            if now.month == 12:
                end_date = start_date.replace(year=now.year + 1, month=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=now.month + 1) - timedelta(days=1)
        else:  # quarterly, yearly
            return 0  # Implement as needed
        
        total_minutes = PersonalTimeboxSession.objects.filter(
            task__category=self.category,
            task__user=self.user,
            start_time__date__range=[start_date, end_date],
            outcome__in=['completed', 'partial']
        ).aggregate(total=models.Sum('actual_minutes'))['total'] or 0
        
        target_minutes = float(self.target_hours_per_period) * 60
        return min(100, (total_minutes / target_minutes) * 100) if target_minutes > 0 else 0

class PersonalTask(models.Model):
    PRIORITY_CHOICES = [
        (1, _('Critical')),
        (2, _('High')),
        (3, _('Medium')),
        (4, _('Low')),
    ]
    
    ENERGY_LEVELS = [
        ('low', _('Low Energy')),
        ('medium', _('Medium Energy')),
        ('high', _('High Energy')),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(PersonalCategory, on_delete=models.CASCADE)
    goal = models.ForeignKey(PersonalGoal, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3)
    energy_level = models.CharField(max_length=10, choices=ENERGY_LEVELS, default='medium')
    estimated_minutes = models.PositiveIntegerField(default=25)
    actual_minutes = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['priority', 'due_date', 'created_at']
    
    def __str__(self):
        return self.title
    
    def total_time_spent(self):
        # Sum completed/paused session minutes
        total = self.personaltimeboxsession_set.aggregate(
            total=models.Sum('actual_minutes')
        )['total'] or 0
        # Add elapsed minutes from an active session if present
        active = self.personaltimeboxsession_set.filter(end_time__isnull=True).first()
        if active:
            elapsed = int((timezone.now() - active.start_time).total_seconds() / 60)
            # show at least 1 minute while session is active so progress visibly increases
            if elapsed <= 0:
                elapsed = 1
            total += elapsed
        return total
    
    def completion_percentage(self):
        if self.is_completed:
            return 100
        total_time = self.total_time_spent()
        if self.estimated_minutes > 0:
            return min(100, (total_time / self.estimated_minutes) * 100)
        return 0
    
    def is_overdue(self):
        if self.due_date:
            return timezone.now() > self.due_date and not self.is_completed
        return False

    @property
    def status(self):
        """Computed status for template filtering: completed, overdue, in_progress/pending"""
        if self.is_completed:
            return 'completed'
        if self.is_overdue():
            return 'overdue'
        # Treat all non-completed, non-overdue as in_progress (or pending)
        return 'in_progress'

    def get_status_display(self):
        mapping = {
            'completed': _('Completed'),
            'overdue': _('Overdue'),
            'in_progress': _('In Progress'),
            'pending': _('Pending'),
        }
        return mapping.get(self.status, _('Pending'))

class PersonalTimeboxSession(models.Model):
    OUTCOME_CHOICES = [
        ('completed', _('Completed Successfully')),
        ('partial', _('Partially Completed')),
        ('interrupted', _('Interrupted')),
        ('abandoned', _('Abandoned')),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(PersonalTask, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    planned_minutes = models.PositiveIntegerField(default=25)
    actual_minutes = models.PositiveIntegerField(null=True, blank=True)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, null=True, blank=True)
    
    # Reflection fields
    focus_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        help_text='Rate your focus level (1-5)'
    )
    energy_before = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        help_text='Energy level before session (1-5)'
    )
    energy_after = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        help_text='Energy level after session (1-5)'
    )
    notes = models.TextField(blank=True, help_text='What was accomplished?')
    distractions = models.TextField(blank=True, help_text='What caused distractions?')
    key_insights = models.TextField(blank=True, help_text='Key learnings or insights')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.task.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    def duration_display(self):
        if self.actual_minutes:
            hours = self.actual_minutes // 60
            minutes = self.actual_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return "0m"
    
    def efficiency_score(self):
        """Calculate efficiency based on planned vs actual time"""
        if not self.actual_minutes or self.planned_minutes == 0:
            return 0
        return min(100, (self.planned_minutes / self.actual_minutes) * 100)
    
    def productivity_score(self):
        """Overall productivity score combining multiple factors"""
        if not self.focus_rating:
            return 0
        
        focus_score = (self.focus_rating / 5) * 40  # 40% weight
        efficiency_score = (self.efficiency_score() / 100) * 30  # 30% weight
        completion_score = 30 if self.outcome == 'completed' else 15 if self.outcome == 'partial' else 0  # 30% weight
        
        return focus_score + efficiency_score + completion_score

class DailyReflection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    
    # Quantitative metrics
    overall_productivity = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Overall productivity rating (1-5)'
    )
    energy_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Average energy level (1-5)'
    )
    mood = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Overall mood (1-5)'
    )
    stress_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Stress level (1-5)'
    )
    
    # Qualitative reflections
    wins = models.TextField(help_text='What went well today?')
    challenges = models.TextField(help_text='What were the main challenges?')
    improvements = models.TextField(help_text='What could be improved tomorrow?')
    tomorrow_focus = models.TextField(help_text='Top 3 priorities for tomorrow')
    gratitude = models.TextField(blank=True, help_text='What are you grateful for?')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"

class PersonalHabit(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(PersonalCategory, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    target_per_period = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class HabitLog(models.Model):
    habit = models.ForeignKey(PersonalHabit, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['habit', 'date']
        ordering = ['-date']

class UserPreferences(models.Model):
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Timebox settings
    default_work_duration = models.PositiveIntegerField(default=25, help_text='Default work session duration in minutes')
    default_break_duration = models.PositiveIntegerField(default=5, help_text='Default break duration in minutes')
    long_break_duration = models.PositiveIntegerField(default=15, help_text='Long break duration in minutes')
    sessions_before_long_break = models.PositiveIntegerField(default=4, help_text='Sessions before long break')
    
    # Goals and targets
    daily_goal_sessions = models.PositiveIntegerField(default=8, help_text='Target sessions per day')
    weekly_goal_hours = models.DecimalField(max_digits=4, decimal_places=1, default=20.0, help_text='Target hours per week')
    
    # Notifications
    enable_notifications = models.BooleanField(default=True)
    notification_sound = models.BooleanField(default=True)
    session_reminders = models.BooleanField(default=True)
    break_reminders = models.BooleanField(default=True)
    
    # Interface
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    show_analytics_dashboard = models.BooleanField(default=True)
    compact_task_view = models.BooleanField(default=False)
    
    # Privacy
    share_anonymous_stats = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} Preferences"

class WeeklyReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    week_start_date = models.DateField()
    
    # Quantitative summary
    total_sessions = models.PositiveIntegerField(default=0)
    total_minutes = models.PositiveIntegerField(default=0)
    average_focus_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    goals_achieved = models.PositiveIntegerField(default=0)
    goals_total = models.PositiveIntegerField(default=0)
    
    # Qualitative review
    biggest_wins = models.TextField(help_text='What were your biggest accomplishments this week?')
    main_challenges = models.TextField(help_text='What were the main obstacles?')
    lessons_learned = models.TextField(help_text='What did you learn about your productivity?')
    next_week_focus = models.TextField(help_text='What will you focus on next week?')
    process_improvements = models.TextField(blank=True, help_text='How can you improve your process?')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'week_start_date']
        ordering = ['-week_start_date']
    
    def __str__(self):
        return f"{self.user.username} - Week of {self.week_start_date}"