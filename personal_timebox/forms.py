from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import *
from .jalali_fields import get_jalali_datetime_field, get_jalali_date_field

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text=_('Optional: for password reset'))
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
        # Customize placeholders
        self.fields['username'].widget.attrs.update({
            'placeholder': _('Choose a unique username'),
            'autocomplete': 'username'
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': _('your@email.com (optional)'),
            'autocomplete': 'email'
        })
        self.fields['first_name'].widget.attrs['placeholder'] = _('First name')
        self.fields['last_name'].widget.attrs['placeholder'] = _('Last name')
        self.fields['password1'].widget.attrs.update({
            'placeholder': _('Create a strong password'),
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': _('Confirm your password'),
            'autocomplete': 'new-password'
        })

class PersonalTaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['category'].queryset = PersonalCategory.objects.filter(user=user, is_active=True)
            self.fields['goal'].queryset = PersonalGoal.objects.filter(user=user, status='active')
        
        self.fields['goal'].empty_label = _("No specific goal")
        self.fields['due_date'].required = False
        
        # Use dynamic field types based on language
        from django.utils.translation import get_language
        if get_language() == 'fa':
            # Use Jalali datetime field for Persian
            self.fields['due_date'] = get_jalali_datetime_field()(required=False)
        else:
            # Use standard datetime field for other languages
            self.fields['due_date'] = forms.DateTimeField(
                required=False,
                widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
            )
    
    class Meta:
        model = PersonalTask
        fields = ['title', 'description', 'category', 'goal', 'priority', 'energy_level', 'estimated_minutes', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('What do you need to work on?')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Add more details about this task...')}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'goal': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'energy_level': forms.Select(attrs={'class': 'form-select'}),
            'estimated_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 480, 'step': 5}),
        }

class PersonalCategoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # capture user for unique-per-user validation
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Checkbox style for is_active if present
        if 'is_active' in self.fields:
            self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})

    class Meta:
        model = PersonalCategory
        fields = ['name', 'category_type', 'description', 'color', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Category name')}),
            'category_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Brief description...')}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('📋 (emoji or icon class)')}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            return name
        # Validate uniqueness per user
        if self.user is not None:
            qs = PersonalCategory.objects.filter(user=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_('You already have a category with this name.'))
        return name

class PersonalGoalForm(forms.ModelForm):
    class Meta:
        model = PersonalGoal
        fields = ['title', 'description', 'category', 'target_hours_per_period', 'period', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('What do you want to achieve?')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Describe your goal in detail...')}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'target_hours_per_period': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.5, 'min': 0.5}),
            'period': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['category'].queryset = PersonalCategory.objects.filter(user=user, is_active=True)
        
        self.fields['end_date'].required = False

class DailyReflectionForm(forms.ModelForm):
    class Meta:
        model = DailyReflection
        fields = ['overall_productivity', 'energy_level', 'mood', 'stress_level', 'wins', 'challenges', 'improvements', 'tomorrow_focus', 'gratitude']
        widgets = {
            'overall_productivity': forms.Select(choices=[(i, f'{i}/5 {"⭐" * i}') for i in range(1, 6)], attrs={'class': 'form-select'}),
            'energy_level': forms.Select(choices=[(i, f'{i}/5') for i in range(1, 6)], attrs={'class': 'form-select'}),
            'mood': forms.Select(choices=[(i, f'{i}/5') for i in range(1, 6)], attrs={'class': 'form-select'}),
            'stress_level': forms.Select(choices=[(i, f'{i}/5') for i in range(1, 6)], attrs={'class': 'form-select'}),
            'wins': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('What went well today?')}),
            'challenges': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('What were the main challenges?')}),
            'improvements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('What could be improved?')}),
            'tomorrow_focus': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Top 3 priorities for tomorrow')}),
            'gratitude': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('What are you grateful for?')}),
        }

class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = [
            'default_work_duration', 'default_break_duration', 'long_break_duration',
            'sessions_before_long_break', 'daily_goal_sessions', 'weekly_goal_hours',
            'enable_notifications', 'notification_sound', 'session_reminders', 'break_reminders',
            'theme', 'show_analytics_dashboard', 'compact_task_view', 'share_anonymous_stats'
        ]
        widgets = {
            'default_work_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 120}),
            'default_break_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
            'long_break_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 60}),
            'sessions_before_long_break': forms.NumberInput(attrs={'class': 'form-control', 'min': 2, 'max': 10}),
            'daily_goal_sessions': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'weekly_goal_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': 0.5, 'min': 1}),
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'enable_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notification_sound': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'session_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'break_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_analytics_dashboard': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'compact_task_view': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'share_anonymous_stats': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class PersonalHabitForm(forms.ModelForm):
    class Meta:
        model = PersonalHabit
        fields = ['name', 'description', 'category', 'frequency', 'target_per_period']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Habit name')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Describe this habit...')}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'target_per_period': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['category'].queryset = PersonalCategory.objects.filter(user=user, is_active=True)