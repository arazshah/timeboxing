from django import template
from django.utils.translation import get_language
from django.utils import timezone
import jdatetime

register = template.Library()


@register.filter
def jalali_date(value):
    """
    Convert a datetime object to Jalali date string for Persian language.
    Returns the original value for other languages.
    """
    if value is None:
        return ''
    
    # Only convert to Jalali for Persian language
    if get_language() != 'fa':
        return value
    
    try:
        # Handle timezone-aware datetime
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        
        # Always convert from Gregorian to Jalali
        # The database stores dates as Gregorian, so we always need to convert
        jalali_date = jdatetime.date.fromgregorian(year=value.year, month=value.month, day=value.day)
        
        return jalali_date.strftime('%Y/%m/%d')
    except (AttributeError, ValueError, TypeError):
        # If conversion fails, return original value
        return value


@register.filter
def jalali_datetime(value):
    """
    Convert a datetime object to Jalali datetime string for Persian language.
    Returns the original value for other languages.
    """
    if value is None:
        return ''
    
    # Only convert to Jalali for Persian language
    if get_language() != 'fa':
        return value
    
    try:
        # Handle timezone-aware datetime
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        
        # Always convert from Gregorian to Jalali
        # The database stores dates as Gregorian, so we always need to convert
        jalali_datetime = jdatetime.datetime.fromgregorian(
            year=value.year, 
            month=value.month, 
            day=value.day, 
            hour=value.hour, 
            minute=value.minute,
            second=value.second
        )
        
        return jalali_datetime.strftime('%Y/%m/%d %H:%M')
    except (AttributeError, ValueError, TypeError):
        # If conversion fails, return original value
        return value


@register.filter
def jalali_time(value):
    """
    Convert a datetime object to time string for Persian language.
    Returns the original value for other languages.
    """
    if value is None:
        return ''
    
    # Only format time for Persian language (can add Persian digits if needed)
    if get_language() != 'fa':
        return value
    
    try:
        # Handle timezone-aware datetime
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        
        return value.strftime('%H:%M')
    except (AttributeError, ValueError, TypeError):
        # If conversion fails, return original value
        return value


@register.filter
def jalali_date_full(value):
    """
    Convert a datetime object to full Jalali date string with weekday name for Persian language.
    Returns the original value for other languages.
    """
    if value is None:
        return ''
    
    # Only convert to Jalali for Persian language
    if get_language() != 'fa':
        return value
    
    try:
        # Handle timezone-aware datetime
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        
        # Always convert from Gregorian to Jalali
        # The database stores dates as Gregorian, so we always need to convert
        jalali_date = jdatetime.date.fromgregorian(year=value.year, month=value.month, day=value.day)
        
        # Get weekday name in Persian
        persian_weekdays = {
            0: 'شنبه',
            1: 'یکشنبه', 
            2: 'دوشنبه',
            3: 'سه‌شنبه',
            4: 'چهارشنبه',
            5: 'پنجشنبه',
            6: 'جمعه',
        }
        
        weekday_name = persian_weekdays.get(jalali_date.weekday(), '')
        
        # Format: شنبه ۱۴۰۳/۰۶/۱۵
        return f"{weekday_name} {jalali_date.strftime('%Y/%m/%d')}"
    except (AttributeError, ValueError, TypeError):
        # If conversion fails, return original value
        return value


@register.filter
def jalali_datetime_full(value):
    """
    Convert a datetime object to full Jalali datetime string with weekday name for Persian language.
    Returns the original value for other languages.
    """
    if value is None:
        return ''
    
    # Only convert to Jalali for Persian language
    if get_language() != 'fa':
        return value
    
    try:
        # Handle timezone-aware datetime
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        
        # Always convert from Gregorian to Jalali
        # The database stores dates as Gregorian, so we always need to convert
        jalali_datetime = jdatetime.datetime.fromgregorian(
            year=value.year, 
            month=value.month, 
            day=value.day, 
            hour=value.hour, 
            minute=value.minute,
            second=value.second
        )
        
        # Get weekday name in Persian
        persian_weekdays = {
            0: 'شنبه',
            1: 'یکشنبه', 
            2: 'دوشنبه',
            3: 'سه‌شنبه',
            4: 'چهارشنبه',
            5: 'پنجشنبه',
            6: 'جمعه',
        }
        
        weekday_name = persian_weekdays.get(jalali_datetime.weekday(), '')
        
        # Format: شنبه ۱۴۰۳/۰۶/۱۵ ساعت ۱۴:۳۰
        return f"{weekday_name} {jalali_datetime.strftime('%Y/%m/%d')} ساعت {jalali_datetime.strftime('%H:%M')}"
    except (AttributeError, ValueError, TypeError):
        # If conversion fails, return original value
        return value


@register.filter
def persian_digits(value):
    """
    Convert English digits to Persian digits for Persian language.
    Returns the original value for other languages.
    """
    if value is None:
        return ''
    
    # Only convert digits for Persian language
    if get_language() != 'fa':
        return value
    
    try:
        # Convert to string if not already
        value_str = str(value)
        
        # Mapping of English to Persian digits
        digit_mapping = {
            '0': '۰',
            '1': '۱',
            '2': '۲',
            '3': '۳',
            '4': '۴',
            '5': '۵',
            '6': '۶',
            '7': '۷',
            '8': '۸',
            '9': '۹',
        }
        
        # Replace each digit
        for english_digit, persian_digit in digit_mapping.items():
            value_str = value_str.replace(english_digit, persian_digit)
        
        return value_str
    except (AttributeError, ValueError, TypeError):
        # If conversion fails, return original value
        return value


@register.filter
def jalali_relative_time(value):
    """
    Convert a datetime object to relative time string in Persian for Persian language.
    Returns the original value for other languages.
    """
    if value is None:
        return ''
    
    # Only convert for Persian language
    if get_language() != 'fa':
        return value
    
    try:
        now = timezone.now()
        
        # Handle timezone-aware datetime
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        
        # Calculate difference
        diff = now - value
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'همین الان'
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f'{minutes} دقیقه پیش'
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f'{hours} ساعت پیش'
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f'{days} روز پیش'
        elif seconds < 2592000:
            weeks = int(seconds // 604800)
            return f'{weeks} هفته پیش'
        elif seconds < 31536000:
            months = int(seconds // 2592000)
            return f'{months} ماه پیش'
        else:
            years = int(seconds // 31536000)
            return f'{years} سال پیش'
            
    except (AttributeError, ValueError, TypeError):
        # If conversion fails, return original value
        return value
