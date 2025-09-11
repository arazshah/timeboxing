from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from personal_timebox.models import PersonalTask, UserPreferences
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update overdue tasks and send notifications'

    def handle(self, *args, **options):
        self.stdout.write('Starting overdue task update...')
        
        # Get current time
        now = timezone.now()
        
        # Find all overdue tasks that haven't been processed
        overdue_tasks = PersonalTask.objects.filter(
            due_date__lt=now,
            is_completed=False
        ).select_related('user', 'category')
        
        if not overdue_tasks.exists():
            self.stdout.write(self.style.SUCCESS('No overdue tasks found.'))
            return
        
        self.stdout.write(f'Found {overdue_tasks.count()} overdue tasks.')
        
        # Group tasks by user for batch processing
        users_with_overdue_tasks = {}
        
        for task in overdue_tasks:
            user_id = task.user.id
            if user_id not in users_with_overdue_tasks:
                users_with_overdue_tasks[user_id] = {
                    'user': task.user,
                    'tasks': [],
                    'preferences': None
                }
            users_with_overdue_tasks[user_id]['tasks'].append(task)
        
        # Process each user's overdue tasks
        processed_count = 0
        notification_count = 0
        
        for user_id, user_data in users_with_overdue_tasks.items():
            user = user_data['user']
            tasks = user_data['tasks']
            
            # Get user preferences
            try:
                preferences = UserPreferences.objects.get(user=user)
                user_data['preferences'] = preferences
            except UserPreferences.DoesNotExist:
                preferences = None
            
            # Update task priority for overdue tasks
            for task in tasks:
                # Auto-adjust priority for overdue tasks
                if task.priority > 1:  # If not already critical
                    old_priority = task.priority
                    task.priority = max(1, task.priority - 1)  # Increase priority
                    task.save()
                    processed_count += 1
                    
                    self.stdout.write(
                        f'Updated task "{task.title}" priority from {old_priority} to {task.priority}'
                    )
            
            # Send notification if enabled
            if preferences and preferences.enable_notifications:
                self.send_overdue_notification(user, tasks, preferences)
                notification_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {processed_count} overdue tasks and sent {notification_count} notifications.'
            )
        )

    def send_overdue_notification(self, user, tasks, preferences):
        """Send email notification for overdue tasks"""
        try:
            # Build email content
            subject = f'You have {len(tasks)} overdue task(s)'
            
            # Create context for email template
            context = {
                'user': user,
                'tasks': tasks,
                'task_count': len(tasks),
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            }
            
            # Render email templates
            html_content = render_to_string(
                'personal_timebox/email/overdue_tasks.html',
                context
            )
            text_content = render_to_string(
                'personal_timebox/email/overdue_tasks.txt',
                context
            )
            
            # Send email
            send_mail(
                subject=subject,
                message=text_content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@timebox.com'),
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False
            )
            
            self.stdout.write(f'Sent overdue notification to {user.email}')
            
        except Exception as e:
            logger.error(f'Failed to send overdue notification to {user.email}: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Failed to send notification to {user.email}: {str(e)}')
            )
