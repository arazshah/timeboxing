from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone, translation
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.conf import settings
from datetime import datetime, timedelta, date
import json
import csv
from .models import *
from .forms import *

def set_language_view(request):
    """Set language and redirect back to the same page"""
    if request.method == 'GET':
        language = request.GET.get('language', 'en')
        next_url = request.GET.get('next', '/')
        
        # Validate language
        if language not in ['en', 'fa']:
            language = 'en'
        
        # Activate the language
        translation.activate(language)
        request.session['django_language'] = language
        request.LANGUAGE_CODE = language
        
        # Handle next_url to ensure proper language prefix
        if next_url == '/':
            # If going to root, redirect to language-specific root
            next_url = f'/{language}/'
        elif not next_url.startswith(f'/{language}/') and next_url != '/':
            # If next_url doesn't have the correct language prefix, add it
            # Remove any existing language prefix first
            if next_url.startswith('/en/') or next_url.startswith('/fa/'):
                next_url = next_url[3:]  # Remove /en/ or /fa/
            next_url = f'/{language}{next_url}'
        
        # Set language cookie
        response = redirect(next_url)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language, max_age=365*24*60*60)  # 1 year
        return response
    
    return redirect('/')

def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            create_default_user_data(user)
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created successfully.')
            return redirect('personal_timebox:dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def create_default_user_data(user):
    """Create default categories and preferences for new users"""
    default_categories = [
        ('Work & Career', 'work', '#3498db', '💼'),
        ('Health & Fitness', 'health', '#e74c3c', '💪'),
        ('Learning & Development', 'learning', '#f39c12', '📚'),
        ('Personal Life', 'personal', '#2ecc71', '🏠'),
        ('Hobbies & Interests', 'hobbies', '#9b59b6', '🎨'),
    ]
    
    for name, cat_type, color, icon in default_categories:
        PersonalCategory.objects.get_or_create(
            user=user, name=name,
            defaults={'category_type': cat_type, 'color': color, 'icon': icon}
        )
    
    UserPreferences.objects.get_or_create(
        user=user,
        defaults={
            'default_work_duration': 25,
            'default_break_duration': 5,
            'daily_goal_sessions': 8,
            'enable_notifications': True,
            'theme': 'light'
        }
    )

def home_page(request):
    """Home page view for visitors - shows login/register options"""
    if request.user.is_authenticated:
        return redirect('personal_timebox:dashboard')
    
    return render(request, 'personal_timebox/home.html')

@login_required
def dashboard(request):
    """Main dashboard view"""
    today = timezone.now().date()
    
    # Get active session
    active_session = PersonalTimeboxSession.objects.filter(
        user=request.user, end_time__isnull=True
    ).first()
    
    # Today's statistics
    today_sessions = PersonalTimeboxSession.objects.filter(
        user=request.user, start_time__date=today
    )
    
    today_stats = {
        'sessions_count': today_sessions.count(),
        'total_minutes': today_sessions.aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0,
        'avg_focus': today_sessions.aggregate(Avg('focus_rating'))['focus_rating__avg'] or 0,
        'completed_tasks': PersonalTask.objects.filter(
            user=request.user, completed_at__date=today
        ).count(),
    }
    
    # Pending tasks
    pending_tasks = PersonalTask.objects.filter(
        user=request.user, is_completed=False
    ).select_related('category', 'goal').order_by('priority', 'due_date')[:5]
    
    # Today's time by category
    category_stats = PersonalCategory.objects.filter(
        user=request.user, is_active=True
    ).annotate(
        today_minutes=Sum(
            'personaltask__personaltimeboxsession__actual_minutes',
            filter=Q(personaltask__personaltimeboxsession__start_time__date=today)
        )
    ).filter(today_minutes__gt=0)
    
    # Active goals
    active_goals = PersonalGoal.objects.filter(
        user=request.user, status='active'
    ).select_related('category')[:3]
    
    # Recent sessions
    recent_sessions = PersonalTimeboxSession.objects.filter(
        user=request.user
    ).select_related('task', 'task__category').order_by('-start_time')[:5]
    
    # User preferences
    preferences, created = UserPreferences.objects.get_or_create(user=request.user)
    
    # Overall stats for dashboard cards and charts
    total_tasks = PersonalTask.objects.filter(user=request.user).count()
    completed_tasks = PersonalTask.objects.filter(user=request.user, is_completed=True).count()
    in_progress_tasks = PersonalTask.objects.filter(user=request.user, is_completed=False).count()
    overdue_tasks = PersonalTask.objects.filter(user=request.user, is_completed=False, due_date__lt=timezone.now()).count()

    # Priority distribution counts
    stats = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'priority_critical': PersonalTask.objects.filter(user=request.user, priority=1, is_completed=False).count(),
        'priority_high': PersonalTask.objects.filter(user=request.user, priority=2, is_completed=False).count(),
        'priority_medium': PersonalTask.objects.filter(user=request.user, priority=3, is_completed=False).count(),
        'priority_low': PersonalTask.objects.filter(user=request.user, priority=4, is_completed=False).count(),
    }

    # Recent priority tasks (exclude completed)
    recent_tasks = PersonalTask.objects.filter(
        user=request.user, is_completed=False
    ).order_by('priority', 'due_date')[:5]

    # Weekly time spent data (last 7 days, ending today)
    last_7_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    # English weekday labels matching the above dates (e.g., Mon, Tue, ...)
    weekday_labels = [d.strftime('%a') for d in last_7_dates]
    weekly_minutes = []
    for d in last_7_dates:
        minutes = PersonalTimeboxSession.objects.filter(
            user=request.user,
            start_time__date=d
        ).aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0
        weekly_minutes.append(minutes)

    context = {
        'active_session': active_session,
        'today_stats': today_stats,
        'pending_tasks': pending_tasks,
        'category_stats': category_stats,
        'active_goals': active_goals,
        'recent_sessions': recent_sessions,
        'preferences': preferences,
        'stats': stats,
        'recent_tasks': recent_tasks,
        'weekly_minutes': json.dumps(weekly_minutes),
        'weekday_labels': json.dumps(weekday_labels),
    }
    
    return render(request, 'personal_timebox/dashboard.html', context)

@login_required
def analytics(request):
    """Analytics and reports view"""
    period = request.GET.get('period', '30')
    days = int(period)
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    # Get sessions in period
    sessions = PersonalTimeboxSession.objects.filter(
        user=request.user,
        start_time__date__range=[start_date, end_date]
    ).select_related('task', 'task__category')
    
    # Basic statistics
    total_sessions = sessions.count()
    total_minutes = sessions.aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0
    avg_focus = sessions.aggregate(Avg('focus_rating'))['focus_rating__avg'] or 0
    avg_session_length = sessions.aggregate(Avg('actual_minutes'))['actual_minutes__avg'] or 0
    
    # Daily data for charts
    daily_data = []
    current_date = start_date
    while current_date <= end_date:
        day_sessions = sessions.filter(start_time__date=current_date)
        daily_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'sessions': day_sessions.count(),
            'minutes': day_sessions.aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0,
            'avg_focus': day_sessions.aggregate(Avg('focus_rating'))['focus_rating__avg'] or 0,
        })
        current_date += timedelta(days=1)
    
    # Category breakdown
    category_stats = PersonalCategory.objects.filter(
        user=request.user,
        personaltask__personaltimeboxsession__in=sessions
    ).annotate(
        total_minutes=Sum('personaltask__personaltimeboxsession__actual_minutes'),
        session_count=Count('personaltask__personaltimeboxsession')
    ).order_by('-total_minutes')
    
    context = {
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'total_sessions': total_sessions,
        'total_hours': round(total_minutes / 60, 1),
        'avg_focus': round(avg_focus, 1),
        'avg_session_length': round(avg_session_length, 0),
        'daily_data': json.dumps(daily_data),
        'category_stats': category_stats,
        'total_minutes': total_minutes,
    }
    
    return render(request, 'personal_timebox/analytics.html', context)

@login_required
def task_list(request):
    """List all tasks with filtering"""
    filter_type = request.GET.get('filter', 'all')
    search_query = request.GET.get('search', '')
    
    tasks = PersonalTask.objects.filter(user=request.user).select_related('category', 'goal')
    
    # Apply filters
    if filter_type == 'pending':
        tasks = tasks.filter(is_completed=False)
    elif filter_type == 'completed':
        tasks = tasks.filter(is_completed=True)
    elif filter_type == 'overdue':
        tasks = tasks.filter(due_date__lt=timezone.now(), is_completed=False)
    elif filter_type == 'today':
        today = timezone.now().date()
        tasks = tasks.filter(due_date__date=today, is_completed=False)
    
    # Apply search
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Order tasks
    tasks = tasks.order_by('is_completed', 'priority', 'due_date', 'created_at')
    
    # Pagination
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Determine if user currently has an active session to hide Start buttons
    active_session = PersonalTimeboxSession.objects.filter(
        user=request.user, end_time__isnull=True
    ).first()

    # Also provide raw tasks (for current page) and categories for filters used by template
    categories = PersonalCategory.objects.filter(user=request.user, is_active=True).order_by('name')
    context = {
        'page_obj': page_obj,
        'tasks': page_obj.object_list,
        'categories': categories,
        'filter_type': filter_type,
        'search_query': search_query,
        'total_tasks': tasks.count(),
        'active_session': active_session,
    }
    
    return render(request, 'personal_timebox/task_list.html', context)

@login_required
def add_task(request):
    """Add new task"""
    if request.method == 'POST':
        form = PersonalTaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, f'Task "{task.title}" has been created successfully.')
            return redirect('personal_timebox:task_list')
    else:
        form = PersonalTaskForm(user=request.user)
    
    return render(request, 'personal_timebox/add_task.html', {'form': form})

@login_required
def edit_task(request, task_id):
    """Edit existing task"""
    task = get_object_or_404(PersonalTask, id=task_id, user=request.user)
    
    if request.method == 'POST':
        form = PersonalTaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            updated_task = form.save(commit=False)
            # Respect explicit completion toggle from the edit form
            mark_completed = request.POST.get('mark_completed')
            if mark_completed is not None:
                # Accept 'true'/'false' values from hidden input
                completed_flag = str(mark_completed).lower() in ['true', '1', 'on', 'yes']
                updated_task.is_completed = completed_flag
                updated_task.completed_at = timezone.now() if completed_flag else None
            updated_task.save()
            messages.success(request, f'Task "{updated_task.title}" has been updated.')
            return redirect('personal_timebox:task_list')
    else:
        form = PersonalTaskForm(instance=task, user=request.user)
    
    return render(request, 'personal_timebox/edit_task.html', {'form': form, 'task': task})

@login_required
@require_http_methods(["POST"])
def delete_task(request, task_id):
    """Delete task"""
    task = get_object_or_404(PersonalTask, id=task_id, user=request.user)
    task_title = task.title
    task.delete()
    # Return JSON for AJAX requests (fetch)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, f'Task "{task_title}" has been deleted.')
    return redirect('personal_timebox:task_list')

@login_required
@require_http_methods(["POST"])
def toggle_task_completion(request, task_id):
    """Toggle task completion status"""
    task = get_object_or_404(PersonalTask, id=task_id, user=request.user)
    
    task.is_completed = not task.is_completed
    if task.is_completed:
        task.completed_at = timezone.now()
        # If there is an active session for this task, close it
        active = PersonalTimeboxSession.objects.filter(user=request.user, task=task, end_time__isnull=True).first()
        if active:
            end_time = timezone.now()
            actual_minutes = int((end_time - active.start_time).total_seconds() / 60)
            if actual_minutes < 1:
                actual_minutes = 1
            active.end_time = end_time
            active.actual_minutes = actual_minutes
            active.outcome = 'completed'
            active.save()
    else:
        task.completed_at = None
    task.save()
    
    status = 'completed' if task.is_completed else 'reopened'
    messages.success(request, f'Task "{task.title}" has been {status}.')
    
    return JsonResponse({'success': True, 'completed': task.is_completed})

@login_required
def task_detail(request, task_id):
    """Task detail page"""
    task = get_object_or_404(PersonalTask, id=task_id, user=request.user)
    sessions = PersonalTimeboxSession.objects.filter(user=request.user, task=task).order_by('-start_time')
    active_session = PersonalTimeboxSession.objects.filter(
        user=request.user,
        end_time__isnull=True,
        task__is_completed=False
    ).select_related('task').first()
    active_for_this_task = bool(active_session and active_session.task_id == task.id)
    return render(request, 'personal_timebox/task_detail.html', {
        'task': task,
        'sessions': sessions,
        'active_session': active_session,
        'active_for_this_task': active_for_this_task,
    })

@login_required
def start_task(request, task_id):
    """Quick start a session for a task via GET or POST, preventing multiple actives"""
    task = get_object_or_404(PersonalTask, id=task_id, user=request.user)
    # Check active session
    active_session = PersonalTimeboxSession.objects.filter(user=request.user, end_time__isnull=True).first()
    if active_session:
        messages.error(request, 'You already have an active session. Please complete or pause it first.')
        return redirect('personal_timebox:task_list')

    preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
    session = PersonalTimeboxSession.objects.create(
        user=request.user,
        task=task,
        planned_minutes=preferences.default_work_duration if preferences else 25,
        start_time=timezone.now(),
    )
    messages.success(request, f'Session started for "{task.title}"')
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('personal_timebox:task_list')

@login_required
@require_http_methods(["POST"])
def start_session(request):
    """Start a new timeboxing session"""
    # Check for existing active session
    active_session = PersonalTimeboxSession.objects.filter(
        user=request.user, end_time__isnull=True
    ).first()
    
    if active_session:
        return JsonResponse({'success': False, 'error': 'You already have an active session'})
    
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        duration = data.get('duration', 25)
        energy_before = data.get('energy_before', 3)
        
        task = get_object_or_404(PersonalTask, id=task_id, user=request.user)
        
        session = PersonalTimeboxSession.objects.create(
            user=request.user,
            task=task,
            planned_minutes=duration,
            energy_before=energy_before,
            start_time=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'message': f'Session started for "{task.title}"'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def complete_session(request, session_id):
    """Complete an active session"""
    session = get_object_or_404(
        PersonalTimeboxSession, 
        id=session_id, 
        user=request.user, 
        end_time__isnull=True
    )
    
    try:
        data = json.loads(request.body)
        
        # Calculate actual duration
        end_time = timezone.now()
        actual_minutes = int((end_time - session.start_time).total_seconds() / 60)
        # Ensure we record at least 1 minute of progress
        if actual_minutes < 1:
            actual_minutes = 1
        
        # Update session
        session.end_time = end_time
        session.actual_minutes = actual_minutes
        session.outcome = data.get('outcome', 'completed')
        session.focus_rating = data.get('focus_rating')
        session.energy_after = data.get('energy_after')
        session.notes = data.get('notes', '')
        session.distractions = data.get('distractions', '')
        session.key_insights = data.get('key_insights', '')
        session.save()
        
        # Update task if completed
        if data.get('task_completed'):
            session.task.is_completed = True
            session.task.completed_at = end_time
            session.task.save()
        
        # Calculate break duration (simple version)
        break_duration = 5  # Default 5 minutes
        if session.actual_minutes > 60:
            break_duration = 15
        elif session.focus_rating and session.focus_rating >= 4:
            break_duration = 3
        
        return JsonResponse({
            'success': True,
            'break_duration': break_duration,
            'message': 'Session completed successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def pause_session(request, session_id):
    """Pause/stop an active session"""
    session = get_object_or_404(
        PersonalTimeboxSession, 
        id=session_id, 
        user=request.user, 
        end_time__isnull=True
    )
    
    # Calculate actual duration
    end_time = timezone.now()
    actual_minutes = int((end_time - session.start_time).total_seconds() / 60)
    if actual_minutes < 1:
        actual_minutes = 1
    
    session.end_time = end_time
    session.actual_minutes = actual_minutes
    session.outcome = 'interrupted'
    session.notes = 'Session paused by user'
    session.save()
    
    return JsonResponse({'success': True, 'message': 'Session paused'})

@login_required
def session_detail(request, session_id):
    """View session details"""
    session = get_object_or_404(PersonalTimeboxSession, id=session_id, user=request.user)
    return render(request, 'personal_timebox/session_detail.html', {'session': session})

@login_required
@require_http_methods(["GET"])
def task_progress(request, task_id):
    """Return live task progress for polling (minutes and percentage)."""
    task = get_object_or_404(PersonalTask, id=task_id, user=request.user)
    total_minutes = task.total_time_spent()
    completion = task.completion_percentage()
    active = PersonalTimeboxSession.objects.filter(user=request.user, task=task, end_time__isnull=True).first()
    has_active = bool(active)
    active_elapsed = 0
    if active:
        active_elapsed = int((timezone.now() - active.start_time).total_seconds() / 60)
        if active_elapsed < 1:
            active_elapsed = 1
    return JsonResponse({
        'success': True,
        'total_minutes': total_minutes,
        'completion_percentage': int(completion),
        'has_active_session': has_active,
        'active_elapsed': active_elapsed,
        'is_completed': task.is_completed,
    })

@login_required
def goals_list(request):
    """List all goals"""
    goals = PersonalGoal.objects.filter(user=request.user).select_related('category').order_by('-created_at')
    
    # Add progress data
    for goal in goals:
        goal.progress = goal.current_period_progress()
    
    context = {'goals': goals}
    return render(request, 'personal_timebox/goals_list.html', context)

@login_required
def add_goal(request):
    """Add new goal"""
    if request.method == 'POST':
        form = PersonalGoalForm(request.POST, user=request.user)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, f'Goal "{goal.title}" has been created.')
            return redirect('personal_timebox:goals_list')
    else:
        form = PersonalGoalForm(user=request.user)
    
    return render(request, 'personal_timebox/add_goal.html', {'form': form})

@login_required
def edit_goal(request, goal_id):
    """Edit existing goal"""
    goal = get_object_or_404(PersonalGoal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        form = PersonalGoalForm(request.POST, instance=goal, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Goal "{goal.title}" has been updated.')
            return redirect('personal_timebox:goals_list')
    else:
        form = PersonalGoalForm(instance=goal, user=request.user)
    
    return render(request, 'personal_timebox/edit_goal.html', {'form': form, 'goal': goal})

@login_required
@require_http_methods(["POST"])
def delete_goal(request, goal_id):
    """Delete goal"""
    goal = get_object_or_404(PersonalGoal, id=goal_id, user=request.user)
    goal_title = goal.title
    goal.delete()
    messages.success(request, f'Goal "{goal_title}" has been deleted.')
    return redirect('personal_timebox:goals_list')

@login_required
def add_category(request):
    if request.method == 'POST':
        form = PersonalCategoryForm(request.POST, user=request.user)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, f'Category "{category.name}" has been added successfully.')
            return redirect('personal_timebox:manage_categories')  # ریدایرکت به لیست مدیریت
    else:
        form = PersonalCategoryForm(user=request.user)
    
    return render(request, 'personal_timebox/add_category.html', {'form': form})

@login_required
def manage_categories(request):
    categories = PersonalCategory.objects.filter(user=request.user).order_by('name')
    return render(request, 'personal_timebox/manage_categories.html', {'categories': categories})

@login_required
def category_list(request):
    categories = PersonalCategory.objects.filter(user=request.user).order_by('name') 
    return render(request, 'personal_timebox/category_list.html', {'categories': categories})

@login_required
def edit_category(request, category_id):
    """Edit existing category"""
    category = get_object_or_404(PersonalCategory, id=category_id, user=request.user)
    
    if request.method == 'POST':
        form = PersonalCategoryForm(request.POST, instance=category, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" has been updated.')
            return redirect('personal_timebox:manage_categories')
    else:
        form = PersonalCategoryForm(instance=category, user=request.user)
    
    return render(request, 'personal_timebox/edit_category.html', {'form': form, 'category': category})

@login_required
@require_http_methods(["POST"])
def delete_category(request, category_id):
    """Delete category"""
    category = get_object_or_404(PersonalCategory, id=category_id, user=request.user)
    
    # Check if category has tasks
    if category.personaltask_set.exists():
        messages.error(request, f'Cannot delete category "{category.name}" because it has associated tasks.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Category has associated tasks.'}, status=400)
        return redirect('personal_timebox:manage_categories')
    
    category_name = category.name
    category.delete()
    # Return JSON for AJAX requests (fetch)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, f'Category "{category_name}" has been deleted.')
    return redirect('personal_timebox:manage_categories')

@login_required
def daily_reflection(request, date=None):
    """Daily reflection view"""
    if date:
        reflection_date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        reflection_date = timezone.now().date()
    
    reflection, created = DailyReflection.objects.get_or_create(
        user=request.user, date=reflection_date
    )
    
    if request.method == 'POST':
        form = DailyReflectionForm(request.POST, instance=reflection)
        if form.is_valid():
            form.save()
            messages.success(request, f'Daily reflection for {reflection_date} has been saved.')
            return redirect('personal_timebox:dashboard')
    else:
        form = DailyReflectionForm(instance=reflection)
    
    # Get day's statistics
    day_sessions = PersonalTimeboxSession.objects.filter(
        user=request.user, start_time__date=reflection_date
    )
    
    day_stats = {
        'sessions_count': day_sessions.count(),
        'total_minutes': day_sessions.aggregate(Sum('actual_minutes'))['actual_minutes__sum'] or 0,
        'avg_focus': day_sessions.aggregate(Avg('focus_rating'))['focus_rating__avg'] or 0,
        'completed_tasks': PersonalTask.objects.filter(
            user=request.user, completed_at__date=reflection_date
        ).count(),
    }
    
    context = {
        'form': form,
        'reflection': reflection,
        'reflection_date': reflection_date,
        'day_stats': day_stats,
        'created': created,
    }
    
    return render(request, 'personal_timebox/daily_reflection.html', context)

@login_required
def preferences(request):
    """User preferences view"""
    preferences, created = UserPreferences.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your preferences have been updated.')
            return redirect('personal_timebox:preferences')
    else:
        form = UserPreferencesForm(instance=preferences)
    
    return render(request, 'personal_timebox/preferences.html', {'form': form})

@login_required
def habits_list(request):
    """List habits"""
    habits = PersonalHabit.objects.filter(user=request.user, is_active=True).select_related('category')
    return render(request, 'personal_timebox/habits_list.html', {'habits': habits})

@login_required
def add_habit(request):
    """Add new habit"""
    if request.method == 'POST':
        form = PersonalHabitForm(request.POST, user=request.user)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            messages.success(request, f'Habit "{habit.name}" has been created.')
            return redirect('personal_timebox:habits_list')
    else:
        form = PersonalHabitForm(user=request.user)
    
    return render(request, 'personal_timebox/add_habit.html', {'form': form})

@login_required
def reports(request):
    """Reports view"""
    return render(request, 'personal_timebox/reports.html')

@login_required
def export_csv(request):
    """Export sessions to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="timebox_sessions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Task', 'Category', 'Duration (min)', 'Focus Rating', 'Outcome', 'Notes'])
    
    sessions = PersonalTimeboxSession.objects.filter(user=request.user).select_related('task', 'task__category')
    for session in sessions:
        writer.writerow([
            session.start_time.date(),
            session.task.title,
            session.task.category.name,
            session.actual_minutes or 0,
            session.focus_rating or '',
            session.get_outcome_display(),
            session.notes
        ])
    
    return response

@login_required
def export_sessions_json(request):
    """Export sessions to JSON"""
    sessions = PersonalTimeboxSession.objects.filter(user=request.user).select_related('task', 'task__category')
    
    data = []
    for session in sessions:
        data.append({
            'id': session.id,
            'date': session.start_time.date().isoformat(),
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'task': session.task.title,
            'category': session.task.category.name,
            'planned_minutes': session.planned_minutes,
            'actual_minutes': session.actual_minutes,
            'focus_rating': session.focus_rating,
            'outcome': session.get_outcome_display(),
            'energy_before': session.energy_before,
            'energy_after': session.energy_after,
            'notes': session.notes,
            'distractions': session.distractions,
            'key_insights': session.key_insights,
            'created_at': session.created_at.isoformat()
        })
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="timebox_sessions.json"'
    return response

@login_required
def export_tasks_csv(request):
    """Export tasks to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="timebox_tasks.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Category', 'Goal', 'Priority', 'Energy Level', 'Estimated Minutes', 'Actual Minutes', 'Status', 'Due Date', 'Created At', 'Completed At'])
    
    tasks = PersonalTask.objects.filter(user=request.user).select_related('category', 'goal')
    for task in tasks:
        writer.writerow([
            task.title,
            task.category.name,
            task.goal.title if task.goal else '',
            task.get_priority_display(),
            task.get_energy_level_display(),
            task.estimated_minutes,
            task.actual_minutes,
            task.get_status_display(),
            task.due_date.isoformat() if task.due_date else '',
            task.created_at.isoformat(),
            task.completed_at.isoformat() if task.completed_at else ''
        ])
    
    return response

@login_required
def export_tasks_json(request):
    """Export tasks to JSON"""
    tasks = PersonalTask.objects.filter(user=request.user).select_related('category', 'goal')
    
    data = []
    for task in tasks:
        data.append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'category': task.category.name,
            'goal': task.goal.title if task.goal else None,
            'priority': task.get_priority_display(),
            'energy_level': task.get_energy_level_display(),
            'estimated_minutes': task.estimated_minutes,
            'actual_minutes': task.actual_minutes,
            'is_completed': task.is_completed,
            'status': task.get_status_display(),
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_at': task.created_at.isoformat(),
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        })
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="timebox_tasks.json"'
    return response

@login_required
def export_categories_csv(request):
    """Export categories to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="timebox_categories.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Type', 'Description', 'Color', 'Icon', 'Is Active', 'Created At'])
    
    categories = PersonalCategory.objects.filter(user=request.user)
    for category in categories:
        writer.writerow([
            category.name,
            category.get_category_type_display(),
            category.description,
            category.color,
            category.icon,
            category.is_active,
            category.created_at.isoformat()
        ])
    
    return response

@login_required
def export_categories_json(request):
    """Export categories to JSON"""
    categories = PersonalCategory.objects.filter(user=request.user)
    
    data = []
    for category in categories:
        data.append({
            'id': category.id,
            'name': category.name,
            'category_type': category.get_category_type_display(),
            'description': category.description,
            'color': category.color,
            'icon': category.icon,
            'is_active': category.is_active,
            'created_at': category.created_at.isoformat()
        })
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="timebox_categories.json"'
    return response

@login_required
def export_goals_csv(request):
    """Export goals to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="timebox_goals.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Category', 'Target Hours', 'Period', 'Status', 'Start Date', 'End Date', 'Created At'])
    
    goals = PersonalGoal.objects.filter(user=request.user).select_related('category')
    for goal in goals:
        writer.writerow([
            goal.title,
            goal.category.name,
            goal.target_hours_per_period,
            goal.get_period_display(),
            goal.get_status_display(),
            goal.start_date.isoformat(),
            goal.end_date.isoformat() if goal.end_date else '',
            goal.created_at.isoformat()
        ])
    
    return response

@login_required
def export_goals_json(request):
    """Export goals to JSON"""
    goals = PersonalGoal.objects.filter(user=request.user).select_related('category')
    
    data = []
    for goal in goals:
        data.append({
            'id': goal.id,
            'title': goal.title,
            'description': goal.description,
            'category': goal.category.name,
            'target_hours_per_period': str(goal.target_hours_per_period),
            'period': goal.get_period_display(),
            'status': goal.get_status_display(),
            'start_date': goal.start_date.isoformat(),
            'end_date': goal.end_date.isoformat() if goal.end_date else None,
            'created_at': goal.created_at.isoformat()
        })
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="timebox_goals.json"'
    return response

@login_required
def export_habits_csv(request):
    """Export habits to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="timebox_habits.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Category', 'Description', 'Frequency', 'Target Per Period', 'Is Active', 'Created At'])
    
    habits = PersonalHabit.objects.filter(user=request.user).select_related('category')
    for habit in habits:
        writer.writerow([
            habit.name,
            habit.category.name,
            habit.description,
            habit.get_frequency_display(),
            habit.target_per_period,
            habit.is_active,
            habit.created_at.isoformat()
        ])
    
    return response

@login_required
def export_habits_json(request):
    """Export habits to JSON"""
    habits = PersonalHabit.objects.filter(user=request.user).select_related('category')
    
    data = []
    for habit in habits:
        data.append({
            'id': habit.id,
            'name': habit.name,
            'description': habit.description,
            'category': habit.category.name,
            'frequency': habit.get_frequency_display(),
            'target_per_period': habit.target_per_period,
            'is_active': habit.is_active,
            'created_at': habit.created_at.isoformat()
        })
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="timebox_habits.json"'
    return response

@login_required
def export_reflections_csv(request):
    """Export daily reflections to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="timebox_reflections.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Productivity', 'Energy Level', 'Mood', 'Stress Level', 'Wins', 'Challenges', 'Improvements', 'Tomorrow Focus', 'Gratitude', 'Created At'])
    
    reflections = DailyReflection.objects.filter(user=request.user)
    for reflection in reflections:
        writer.writerow([
            reflection.date.isoformat(),
            reflection.overall_productivity,
            reflection.energy_level,
            reflection.mood,
            reflection.stress_level,
            reflection.wins,
            reflection.challenges,
            reflection.improvements,
            reflection.tomorrow_focus,
            reflection.gratitude,
            reflection.created_at.isoformat()
        ])
    
    return response

@login_required
def export_reflections_json(request):
    """Export daily reflections to JSON"""
    reflections = DailyReflection.objects.filter(user=request.user)
    
    data = []
    for reflection in reflections:
        data.append({
            'id': reflection.id,
            'date': reflection.date.isoformat(),
            'overall_productivity': reflection.overall_productivity,
            'energy_level': reflection.energy_level,
            'mood': reflection.mood,
            'stress_level': reflection.stress_level,
            'wins': reflection.wins,
            'challenges': reflection.challenges,
            'improvements': reflection.improvements,
            'tomorrow_focus': reflection.tomorrow_focus,
            'gratitude': reflection.gratitude,
            'created_at': reflection.created_at.isoformat()
        })
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="timebox_reflections.json"'
    return response

@login_required
def export_all_csv(request):
    """Export all data to a ZIP file containing CSV files"""
    import zipfile
    import io
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Export sessions
        sessions_data = io.StringIO()
        writer = csv.writer(sessions_data)
        writer.writerow(['Date', 'Task', 'Category', 'Duration (min)', 'Focus Rating', 'Outcome', 'Notes'])
        sessions = PersonalTimeboxSession.objects.filter(user=request.user).select_related('task', 'task__category')
        for session in sessions:
            writer.writerow([
                session.start_time.date(),
                session.task.title,
                session.task.category.name,
                session.actual_minutes or 0,
                session.focus_rating or '',
                session.get_outcome_display(),
                session.notes
            ])
        zip_file.writestr('sessions.csv', sessions_data.getvalue())
        
        # Export tasks
        tasks_data = io.StringIO()
        writer = csv.writer(tasks_data)
        writer.writerow(['Title', 'Category', 'Goal', 'Priority', 'Energy Level', 'Estimated Minutes', 'Actual Minutes', 'Status', 'Due Date', 'Created At', 'Completed At'])
        tasks = PersonalTask.objects.filter(user=request.user).select_related('category', 'goal')
        for task in tasks:
            writer.writerow([
                task.title,
                task.category.name,
                task.goal.title if task.goal else '',
                task.get_priority_display(),
                task.get_energy_level_display(),
                task.estimated_minutes,
                task.actual_minutes,
                task.get_status_display(),
                task.due_date.isoformat() if task.due_date else '',
                task.created_at.isoformat(),
                task.completed_at.isoformat() if task.completed_at else ''
            ])
        zip_file.writestr('tasks.csv', tasks_data.getvalue())
        
        # Export categories
        categories_data = io.StringIO()
        writer = csv.writer(categories_data)
        writer.writerow(['Name', 'Type', 'Description', 'Color', 'Icon', 'Is Active', 'Created At'])
        categories = PersonalCategory.objects.filter(user=request.user)
        for category in categories:
            writer.writerow([
                category.name,
                category.get_category_type_display(),
                category.description,
                category.color,
                category.icon,
                category.is_active,
                category.created_at.isoformat()
            ])
        zip_file.writestr('categories.csv', categories_data.getvalue())
        
        # Export goals
        goals_data = io.StringIO()
        writer = csv.writer(goals_data)
        writer.writerow(['Title', 'Category', 'Target Hours', 'Period', 'Status', 'Start Date', 'End Date', 'Created At'])
        goals = PersonalGoal.objects.filter(user=request.user).select_related('category')
        for goal in goals:
            writer.writerow([
                goal.title,
                goal.category.name,
                goal.target_hours_per_period,
                goal.get_period_display(),
                goal.get_status_display(),
                goal.start_date.isoformat(),
                goal.end_date.isoformat() if goal.end_date else '',
                goal.created_at.isoformat()
            ])
        zip_file.writestr('goals.csv', goals_data.getvalue())
        
        # Export habits
        habits_data = io.StringIO()
        writer = csv.writer(habits_data)
        writer.writerow(['Name', 'Category', 'Description', 'Frequency', 'Target Per Period', 'Is Active', 'Created At'])
        habits = PersonalHabit.objects.filter(user=request.user).select_related('category')
        for habit in habits:
            writer.writerow([
                habit.name,
                habit.category.name,
                habit.description,
                habit.get_frequency_display(),
                habit.target_per_period,
                habit.is_active,
                habit.created_at.isoformat()
            ])
        zip_file.writestr('habits.csv', habits_data.getvalue())
        
        # Export reflections
        reflections_data = io.StringIO()
        writer = csv.writer(reflections_data)
        writer.writerow(['Date', 'Productivity', 'Energy Level', 'Mood', 'Stress Level', 'Wins', 'Challenges', 'Improvements', 'Tomorrow Focus', 'Gratitude', 'Created At'])
        reflections = DailyReflection.objects.filter(user=request.user)
        for reflection in reflections:
            writer.writerow([
                reflection.date.isoformat(),
                reflection.overall_productivity,
                reflection.energy_level,
                reflection.mood,
                reflection.stress_level,
                reflection.wins,
                reflection.challenges,
                reflection.improvements,
                reflection.tomorrow_focus,
                reflection.gratitude,
                reflection.created_at.isoformat()
            ])
        zip_file.writestr('reflections.csv', reflections_data.getvalue())
    
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="timebox_data_export.zip"'
    return response

@login_required
def export_all_json(request):
    """Export all data to JSON"""
    data = {
        'export_date': timezone.now().isoformat(),
        'user': request.user.username,
        'data': {
            'sessions': [],
            'tasks': [],
            'categories': [],
            'goals': [],
            'habits': [],
            'reflections': []
        }
    }
    
    # Export sessions
    sessions = PersonalTimeboxSession.objects.filter(user=request.user).select_related('task', 'task__category')
    for session in sessions:
        data['data']['sessions'].append({
            'id': session.id,
            'date': session.start_time.date().isoformat(),
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'task': session.task.title,
            'category': session.task.category.name,
            'planned_minutes': session.planned_minutes,
            'actual_minutes': session.actual_minutes,
            'focus_rating': session.focus_rating,
            'outcome': session.get_outcome_display(),
            'energy_before': session.energy_before,
            'energy_after': session.energy_after,
            'notes': session.notes,
            'distractions': session.distractions,
            'key_insights': session.key_insights,
            'created_at': session.created_at.isoformat()
        })
    
    # Export tasks
    tasks = PersonalTask.objects.filter(user=request.user).select_related('category', 'goal')
    for task in tasks:
        data['data']['tasks'].append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'category': task.category.name,
            'goal': task.goal.title if task.goal else None,
            'priority': task.get_priority_display(),
            'energy_level': task.get_energy_level_display(),
            'estimated_minutes': task.estimated_minutes,
            'actual_minutes': task.actual_minutes,
            'is_completed': task.is_completed,
            'status': task.get_status_display(),
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_at': task.created_at.isoformat(),
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        })
    
    # Export categories
    categories = PersonalCategory.objects.filter(user=request.user)
    for category in categories:
        data['data']['categories'].append({
            'id': category.id,
            'name': category.name,
            'category_type': category.get_category_type_display(),
            'description': category.description,
            'color': category.color,
            'icon': category.icon,
            'is_active': category.is_active,
            'created_at': category.created_at.isoformat()
        })
    
    # Export goals
    goals = PersonalGoal.objects.filter(user=request.user).select_related('category')
    for goal in goals:
        data['data']['goals'].append({
            'id': goal.id,
            'title': goal.title,
            'description': goal.description,
            'category': goal.category.name,
            'target_hours_per_period': str(goal.target_hours_per_period),
            'period': goal.get_period_display(),
            'status': goal.get_status_display(),
            'start_date': goal.start_date.isoformat(),
            'end_date': goal.end_date.isoformat() if goal.end_date else None,
            'created_at': goal.created_at.isoformat()
        })
    
    # Export habits
    habits = PersonalHabit.objects.filter(user=request.user).select_related('category')
    for habit in habits:
        data['data']['habits'].append({
            'id': habit.id,
            'name': habit.name,
            'description': habit.description,
            'category': habit.category.name,
            'frequency': habit.get_frequency_display(),
            'target_per_period': habit.target_per_period,
            'is_active': habit.is_active,
            'created_at': habit.created_at.isoformat()
        })
    
    # Export reflections
    reflections = DailyReflection.objects.filter(user=request.user)
    for reflection in reflections:
        data['data']['reflections'].append({
            'id': reflection.id,
            'date': reflection.date.isoformat(),
            'overall_productivity': reflection.overall_productivity,
            'energy_level': reflection.energy_level,
            'mood': reflection.mood,
            'stress_level': reflection.stress_level,
            'wins': reflection.wins,
            'challenges': reflection.challenges,
            'improvements': reflection.improvements,
            'tomorrow_focus': reflection.tomorrow_focus,
            'gratitude': reflection.gratitude,
            'created_at': reflection.created_at.isoformat()
        })
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="timebox_all_data.json"'
    return response
    return redirect('personal_timebox:reports')

def about_page(request):
    """About page view"""
    return render(request, 'personal_timebox/about.html')

def docs_page(request):
    """Documentation page view"""
    return render(request, 'personal_timebox/docs.html')

def privacy_page(request):
    """Privacy policy page view"""
    return render(request, 'personal_timebox/privacy.html')