from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import *

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'goals', GoalViewSet, basename='goal')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-stats/', dashboard_stats_api, name='dashboard_stats_api'),
    path('quick-stats/', quick_stats_api, name='quick_stats_api'),
    path('analytics-stats/', analytics_stats_api, name='analytics_stats_api'),
]