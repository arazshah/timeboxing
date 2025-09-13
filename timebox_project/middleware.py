from django.conf import settings
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.http import HttpResponseRedirect
from django.contrib.sites.shortcuts import get_current_site

class DomainLanguageMiddleware(MiddlewareMixin):
    """
    Middleware to set language based on domain name.
    - time2box.ir -> Persian (fa)
    - timebox.click -> English (en)
    - localhost:8000/fa/ -> Persian (fa) for local development
    - localhost:8000/en/ -> English (en) for local development
    """
    
    def process_request(self, request):
        # Get the current domain
        domain = get_current_site(request).domain
        
        # Check for language in URL path first (for local development)
        path = request.path_info
        if path.startswith('/fa/'):
            language = 'fa'
            self._activate_language(request, language)
            return self.get_response(request)
        elif path.startswith('/en/'):
            language = 'en'
            self._activate_language(request, language)
            return self.get_response(request)
        
        # Check for language in session
        if 'django_language' in request.session:
            language = request.session['django_language']
            self._activate_language(request, language)
            return self.get_response(request)
        
        # Map domains to languages
        domain_language_map = {
            'time2box.ir': 'fa',
            'timebox.click': 'en',
            # Add localhost mapping for Persian testing
            'localhost:8000': 'fa',
            '127.0.0.1:8000': 'fa',
        }
        
        # Check if the domain is in our mapping
        if domain in domain_language_map:
            language = domain_language_map[domain]
            self._activate_language(request, language)
            return self.get_response(request)
        
        # If domain not found, continue with default behavior
        return self.get_response(request)
    
    def _activate_language(self, request, language):
        """Helper method to activate language and set session/cookie"""
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
        
        # Store language in session for consistency
        request.session['django_language'] = language
        
        # Set language cookie for future requests
        response = self.get_response(request)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
        return response
