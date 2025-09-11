from django.urls import path
from . import views

app_name = 'personal_timebox'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/add/', views.add_task, name='add_task'),
    path('tasks/<int:task_id>/edit/', views.edit_task, name='edit_task'),
    path('analytics/', views.analytics, name='analytics'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/manage/', views.manage_categories, name='manage_categories'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    # Added routes to support templates
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('tasks/<int:task_id>/toggle/', views.toggle_task_completion, name='toggle_task_completion'),
    path('tasks/<int:task_id>/start/', views.start_task, name='start_task'),
    path('tasks/<int:task_id>/progress/', views.task_progress, name='task_progress'),
    # Goals
    path('goals/', views.goals_list, name='goals_list'),
    path('goals/add/', views.add_goal, name='add_goal'),
    path('goals/<int:goal_id>/edit/', views.edit_goal, name='edit_goal'),
    path('goals/<int:goal_id>/delete/', views.delete_goal, name='delete_goal'),
    # Static pages
    path('about/', views.about_page, name='about'),
    path('docs/', views.docs_page, name='docs'),
    path('privacy/', views.privacy_page, name='privacy'),
    # Export functionality
    path('export/sessions/csv/', views.export_csv, name='export_sessions_csv'),
    path('export/sessions/json/', views.export_sessions_json, name='export_sessions_json'),
    path('export/tasks/csv/', views.export_tasks_csv, name='export_tasks_csv'),
    path('export/tasks/json/', views.export_tasks_json, name='export_tasks_json'),
    path('export/categories/csv/', views.export_categories_csv, name='export_categories_csv'),
    path('export/categories/json/', views.export_categories_json, name='export_categories_json'),
    path('export/goals/csv/', views.export_goals_csv, name='export_goals_csv'),
    path('export/goals/json/', views.export_goals_json, name='export_goals_json'),
    path('export/habits/csv/', views.export_habits_csv, name='export_habits_csv'),
    path('export/habits/json/', views.export_habits_json, name='export_habits_json'),
    path('export/reflections/csv/', views.export_reflections_csv, name='export_reflections_csv'),
    path('export/reflections/json/', views.export_reflections_json, name='export_reflections_json'),
    path('export/all/csv/', views.export_all_csv, name='export_all_csv'),
    path('export/all/json/', views.export_all_json, name='export_all_json'),
]