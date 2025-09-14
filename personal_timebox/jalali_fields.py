from django import forms
from django.utils.translation import get_language, gettext_lazy as _
import jdatetime
from datetime import datetime
from django.utils import timezone


class JalaliDateWidget(forms.TextInput):
    """
    Custom widget for Jalali date input with Persian calendar support.
    Uses text input with placeholder in Persian format.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'placeholder': _('۱۴۰۳/۰۶/۱۵ ۱۴:۳۰'),
            'class': 'form-control jalali-date-input',
            'dir': 'rtl',
            'lang': 'fa',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    class Media:
        css = {
            'all': ('css/jalali-datepicker.css',)
        }
        js = ('js/jalali-datepicker.js',)


class JalaliDateTimeField(forms.DateTimeField):
    """
    Custom field that handles Jalali date input and converts to Gregorian for storage.
    """
    
    widget = JalaliDateWidget
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_formats = [
            '%Y/%m/%d %H:%M',    # 1403/06/15 14:30
            '%Y/%m/%d %H:%M:%S', # 1403/06/15 14:30:00
            '%Y-%m-%d %H:%M',    # 1403-06-15 14:30
            '%Y-%m-%d %H:%M:%S', # 1403-06-15 14:30:00
            '%Y/%m/%d',          # 1403/06/15
            '%Y-%m-%d',          # 1403-06-15
        ]
    
    def to_python(self, value):
        """
        Convert Jalali date string to Python datetime object.
        """
        if value in self.empty_values:
            return None
        
        # If it's already a datetime object, return it
        if isinstance(value, datetime):
            return value
        
        # Try to parse with standard datetime formats first (for Gregorian input)
        try:
            return super().to_python(value)
        except (ValueError, TypeError):
            pass
        
        # If standard parsing fails, try Jalali formats
        if isinstance(value, str):
            # Remove any extra whitespace
            value = value.strip()
            
            # Try different Jalali formats
            formats_to_try = [
                ('%Y/%m/%d %H:%M:%S', True),   # With seconds, with time
                ('%Y/%m/%d %H:%M', True),       # Without seconds, with time
                ('%Y-%m-%d %H:%M:%S', True),   # With seconds, with time (dash format)
                ('%Y-%m-%d %H:%M', True),       # Without seconds, with time (dash format)
                ('%Y/%m/%d', False),            # Date only
                ('%Y-%m-%d', False),            # Date only (dash format)
            ]
            
            for fmt, has_time in formats_to_try:
                try:
                    # Parse as Jalali date
                    jalali_date = jdatetime.datetime.strptime(value, fmt)
                    
                    # Convert to Gregorian
                    gregorian_date = jalali_date.togregorian()
                    
                    # If no time component, set to current time
                    if not has_time:
                        now = timezone.now()
                        gregorian_date = gregorian_date.replace(
                            hour=now.hour,
                            minute=now.minute,
                            second=now.second,
                            microsecond=now.microsecond,
                            tzinfo=now.tzinfo
                        )
                    else:
                        # Make timezone aware if needed
                        if timezone.is_aware(timezone.now()):
                            gregorian_date = timezone.make_aware(gregorian_date)
                    
                    return gregorian_date
                except ValueError:
                    continue
        
        # If all parsing attempts fail, raise validation error
        raise forms.ValidationError(
            _('Enter a valid Jalali date/time in format: YYYY/MM/DD HH:MM'),
            code='invalid'
        )
    
    def prepare_value(self, value):
        """
        Convert Python datetime object to Jalali date string for display.
        """
        if value is None:
            return ''
        
        if isinstance(value, datetime):
            # Convert to Jalali
            if timezone.is_aware(value):
                # Convert to local timezone first
                value = timezone.localtime(value)
            
            jalali_date = jdatetime.datetime.fromgregorian(datetime=value)
            
            # Format as Jalali date string
            return jalali_date.strftime('%Y/%m/%d %H:%M')
        
        return str(value)


class JalaliDateField(forms.DateField):
    """
    Custom field for Jalali date input (date only).
    """
    
    widget = JalaliDateWidget
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_formats = [
            '%Y/%m/%d',    # 1403/06/15
            '%Y-%m-%d',    # 1403-06-15
        ]
    
    def to_python(self, value):
        """
        Convert Jalali date string to Python date object.
        """
        if value in self.empty_values:
            return None
        
        # If it's already a date object, return it
        if isinstance(value, datetime):
            return value.date()
        elif hasattr(value, 'date'):
            return value.date()
        
        # Try to parse with standard date formats first (for Gregorian input)
        try:
            return super().to_python(value)
        except (ValueError, TypeError):
            pass
        
        # If standard parsing fails, try Jalali formats
        if isinstance(value, str):
            value = value.strip()
            
            formats_to_try = [
                '%Y/%m/%d',    # 1403/06/15
                '%Y-%m-%d',    # 1403-06-15
            ]
            
            for fmt in formats_to_try:
                try:
                    # Parse as Jalali date
                    jalali_date = jdatetime.date.strptime(value, fmt)
                    
                    # Convert to Gregorian
                    gregorian_date = jalali_date.togregorian()
                    return gregorian_date
                except ValueError:
                    continue
        
        # If all parsing attempts fail, raise validation error
        raise forms.ValidationError(
            _('Enter a valid Jalali date in format: YYYY/MM/DD'),
            code='invalid'
        )
    
    def prepare_value(self, value):
        """
        Convert Python date object to Jalali date string for display.
        """
        if value is None:
            return ''
        
        if isinstance(value, datetime):
            value = value.date()
        
        if hasattr(value, 'year'):
            # Convert to Jalali
            jalali_date = jdatetime.date.fromgregorian(date=value)
            
            # Format as Jalali date string
            return jalali_date.strftime('%Y/%m/%d')
        
        return str(value)


def is_persian_language():
    """
    Check if current language is Persian.
    """
    return get_language() == 'fa'


def get_jalali_datetime_field():
    """
    Factory function to return appropriate datetime field based on language.
    """
    if is_persian_language():
        return JalaliDateTimeField
    return forms.DateTimeField


def get_jalali_date_field():
    """
    Factory function to return appropriate date field based on language.
    """
    if is_persian_language():
        return JalaliDateField
    return forms.DateField
