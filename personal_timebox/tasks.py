from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@shared_task
def update_overdue_tasks():
    """
    Scheduled task to update overdue tasks and send notifications.
    This task runs every 60 minutes as configured in CELERY_BEAT_SCHEDULE.
    """
    try:
        # Call the management command to update overdue tasks
        call_command('update_overdue_tasks')
        
        # Cache the last run time
        cache.set('last_overdue_update', timezone.now(), timeout=3600)
        
        logger.info('Overdue tasks update completed successfully')
        return {'status': 'success', 'message': 'Overdue tasks updated successfully'}
        
    except Exception as e:
        logger.error(f'Error updating overdue tasks: {str(e)}')
        return {'status': 'error', 'message': str(e)}

@shared_task
def send_overdue_reminders():
    """
    Additional task to send reminders for tasks that are overdue for more than 24 hours.
    This can be run daily to send more urgent reminders.
    """
    try:
        from django.contrib.auth.models import User
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        from .models import PersonalTask, UserPreferences
        
        # Find tasks that have been overdue for more than 24 hours
        overdue_threshold = timezone.now() - timezone.timedelta(hours=24)
        
        tasks = PersonalTask.objects.filter(
            due_date__lt=overdue_threshold,
            is_completed=False
        ).select_related('user', 'category')
        
        if not tasks.exists():
            logger.info('No long-overdue tasks found for reminders')
            return {'status': 'success', 'message': 'No long-overdue tasks found'}
        
        # Group by user
        users_with_long_overdue = {}
        for task in tasks:
            user_id = task.user.id
            if user_id not in users_with_long_overdue:
                users_with_long_overdue[user_id] = {
                    'user': task.user,
                    'tasks': [],
                    'preferences': None
                }
            users_with_long_overdue[user_id]['tasks'].append(task)
        
        # Send urgent reminders
        reminder_count = 0
        for user_id, user_data in users_with_long_overdue.items():
            user = user_data['user']
            tasks = user_data['tasks']
            
            # Get user preferences
            try:
                preferences = UserPreferences.objects.get(user=user)
                if not preferences.enable_notifications:
                    continue
            except UserPreferences.DoesNotExist:
                continue
            
            # Send urgent reminder email
            subject = f'URGENT: {len(tasks)} task(s) overdue for more than 24 hours'
            
            context = {
                'user': user,
                'tasks': tasks,
                'task_count': len(tasks),
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
                'is_urgent': True,
            }
            
            html_content = render_to_string(
                'personal_timebox/email/overdue_tasks.html',
                context
            )
            text_content = render_to_string(
                'personal_timebox/email/overdue_tasks.txt',
                context
            )
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@timebox.com'),
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False
            )
            
            reminder_count += 1
            logger.info(f'Sent urgent reminder to {user.email}')
        
        logger.info(f'Sent {reminder_count} urgent overdue reminders')
        return {
            'status': 'success', 
            'message': f'Sent {reminder_count} urgent overdue reminders'
        }
        
    except Exception as e:
        logger.error(f'Error sending overdue reminders: {str(e)}')
        return {'status': 'error', 'message': str(e)}

@shared_task
def cleanup_old_completed_tasks():
    """
    Clean up old completed tasks (older than 90 days) to improve performance.
    This can be run weekly or monthly.
    """
    try:
        from .models import PersonalTask
        
        # Find completed tasks older than 90 days
        cutoff_date = timezone.now() - timezone.timedelta(days=90)
        
        old_tasks = PersonalTask.objects.filter(
            is_completed=True,
            completed_at__lt=cutoff_date
        )
        
        count = old_tasks.count()
        
        if count > 0:
            old_tasks.delete()
            logger.info(f'Cleaned up {count} old completed tasks')
        else:
            logger.info('No old completed tasks to clean up')
        
        return {
            'status': 'success', 
            'message': f'Cleaned up {count} old completed tasks'
        }
        
    except Exception as e:
        logger.error(f'Error cleaning up old tasks: {str(e)}')
        return {'status': 'error', 'message': str(e)}
