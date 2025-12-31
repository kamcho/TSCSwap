"""
Custom middleware to catch exceptions and redirect to error page.
"""
import logging
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseServerError

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware:
    """
    Middleware to catch exceptions and redirect to error page.
    Only active when DEBUG=False (production mode).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """
        Process any exception that occurs during request handling.
        """
        from django.conf import settings
        
        # Only handle exceptions in production (when DEBUG=False)
        # In development, let Django show the debug page
        if settings.DEBUG:
            return None  # Let Django handle it with debug page
        
        # Log the exception
        logger.error(
            f"Unhandled exception: {str(exception)}",
            exc_info=True,
            extra={
                'request_path': request.path,
                'request_method': request.method,
                'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
            }
        )
        
        # Redirect to error page
        try:
            from django.shortcuts import render
            from home.error_views import error_page
            return error_page(request, 'server_error', exception)
        except Exception as e:
            # If error page itself fails, return a simple error response
            logger.critical(f"Error page failed to render: {str(e)}")
            return HttpResponseServerError(
                "<h1>Server Error</h1><p>We are having a problem processing your request. Please try again later.</p>"
            )

