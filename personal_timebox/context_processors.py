from .models import UserPreferences

def user_preferences(request):
    """Add user preferences to template context"""
    if request.user.is_authenticated:
        try:
            preferences = UserPreferences.objects.get(user=request.user)
            return {'user_preferences': preferences}
        except UserPreferences.DoesNotExist:
            return {'user_preferences': None}
    return {'user_preferences': None}