#!/usr/bin/env python
"""
Test script for overdue task functionality.
This script creates test tasks and demonstrates the overdue task system.
"""

import os
import sys
from datetime import datetime, timedelta

# Setup Django BEFORE any Django imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timebox_project.settings')
import django
django.setup()

# Now import Django modules after setup
from django.utils import timezone
from django.contrib.auth.models import User
from personal_timebox.models import PersonalTask, PersonalCategory, UserPreferences

def create_test_user():
    """Create a test user if it doesn't exist"""
    username = 'testuser_overdue'
    email = 'test@example.com'
    
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: {username}")
    else:
        print(f"Using existing test user: {username}")
    
    return user

def create_test_category(user):
    """Create a test category"""
    category, created = PersonalCategory.objects.get_or_create(
        user=user,
        name='Test Tasks',
        defaults={
            'category_type': 'work',
            'color': '#3498db',
            'icon': '🧪'
        }
    )
    
    if created:
        print(f"Created test category: {category.name}")
    else:
        print(f"Using existing category: {category.name}")
    
    return category

def create_test_tasks(user, category):
    """Create various test tasks with different due dates"""
    now = timezone.now()
    
    test_tasks = [
        {
            'title': 'Task Due Yesterday',
            'description': 'This task is already overdue',
            'due_date': now - timedelta(days=1),
            'priority': 3,
            'estimated_minutes': 30
        },
        {
            'title': 'Task Due 2 Hours Ago',
            'description': 'This task is overdue by 2 hours',
            'due_date': now - timedelta(hours=2),
            'priority': 2,
            'estimated_minutes': 45
        },
        {
            'title': 'Task Due Tomorrow',
            'description': 'This task is not yet overdue',
            'due_date': now + timedelta(days=1),
            'priority': 3,
            'estimated_minutes': 60
        },
        {
            'title': 'Task Due in 1 Hour',
            'description': 'This task is due soon but not overdue',
            'due_date': now + timedelta(hours=1),
            'priority': 4,
            'estimated_minutes': 25
        },
        {
            'title': 'Task Due 3 Days Ago (High Priority)',
            'description': 'This task is very overdue',
            'due_date': now - timedelta(days=3),
            'priority': 1,
            'estimated_minutes': 90
        }
    ]
    
    created_tasks = []
    
    for task_data in test_tasks:
        task, created = PersonalTask.objects.get_or_create(
            user=user,
            title=task_data['title'],
            defaults={
                'description': task_data['description'],
                'category': category,
                'priority': task_data['priority'],
                'estimated_minutes': task_data['estimated_minutes'],
                'due_date': task_data['due_date'],
                'is_completed': False
            }
        )
        
        if created:
            print(f"Created task: {task.title} (Due: {task.due_date})")
        else:
            # Update existing task to ensure it's not completed and has correct due date
            task.is_completed = False
            task.due_date = task_data['due_date']
            task.priority = task_data['priority']
            task.save()
            print(f"Updated existing task: {task.title}")
        
        created_tasks.append(task)
    
    return created_tasks

def test_overdue_functionality():
    """Test the overdue task functionality"""
    print("\n" + "="*50)
    print("TESTING OVERDUE TASK FUNCTIONALITY")
    print("="*50)
    
    # Create test data
    user = create_test_user()
    category = create_test_category(user)
    tasks = create_test_tasks(user, category)
    
    print(f"\nCreated {len(tasks)} test tasks")
    
    # Test 1: Check overdue status using model methods
    print("\n" + "-"*30)
    print("TEST 1: Checking overdue status")
    print("-"*30)
    
    overdue_count = 0
    for task in tasks:
        is_overdue = task.is_overdue()
        status = task.status
        print(f"Task: {task.title}")
        print(f"  Due: {task.due_date}")
        print(f"  Is Overdue: {is_overdue}")
        print(f"  Status: {status}")
        print(f"  Priority: {task.get_priority_display()}")
        
        if is_overdue:
            overdue_count += 1
        print()
    
    print(f"Total overdue tasks: {overdue_count}")
    
    # Test 2: Run the management command
    print("\n" + "-"*30)
    print("TEST 2: Running management command")
    print("-"*30)
    
    from django.core.management import call_command
    call_command('update_overdue_tasks')
    
    # Test 3: Check if priorities were updated
    print("\n" + "-"*30)
    print("TEST 3: Checking priority updates")
    print("-"*30)
    
    for task in tasks:
        task.refresh_from_db()
        print(f"Task: {task.title}")
        print(f"  Current Priority: {task.get_priority_display()} ({task.priority})")
        print(f"  Is Overdue: {task.is_overdue()}")
        print()
    
    # Test 4: Test filtering in views
    print("\n" + "-"*30)
    print("TEST 4: Testing view filters")
    print("-"*30)
    
    from django.utils import timezone
    
    # Test overdue filter (same as in views.py)
    overdue_tasks = PersonalTask.objects.filter(
        user=user,
        due_date__lt=timezone.now(),
        is_completed=False
    )
    
    print(f"Overdue tasks found by filter: {overdue_tasks.count()}")
    for task in overdue_tasks:
        print(f"  - {task.title} (Due: {task.due_date})")
    
    print("\n" + "="*50)
    print("TESTING COMPLETE")
    print("="*50)
    
    # Cleanup instructions
    print(f"\nTo clean up test data, run:")
    print(f"User.objects.filter(username='testuser_overdue').delete()")
    print(f"PersonalCategory.objects.filter(user__username='testuser_overdue', name='Test Tasks').delete()")

if __name__ == '__main__':
    test_overdue_functionality()
