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
        
        # Save error to database (error_page will handle this, but we can also do it here for middleware exceptions)
        try:
            from home.models import ErrorLog
            import traceback
            
            # Get user (may be AnonymousUser)
            user = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user
            
            # Get IP address
            ip_address = None
            if hasattr(request, 'META'):
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0].strip()
                else:
                    ip_address = request.META.get('REMOTE_ADDR')
            
            # Get user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if hasattr(request, 'META') else ''
            
            # Create error log entry
            ErrorLog.objects.create(
                user=user,
                error_type='exception',
                error_message=str(exception)[:1000],
                page_url=request.build_absolute_uri()[:500] if hasattr(request, 'build_absolute_uri') else None,
                request_path=request.path[:500] if hasattr(request, 'path') else None,
                request_method=request.method if hasattr(request, 'method') else None,
                status_code=500,
                exception_type=type(exception).__name__,
                traceback=traceback.format_exc()[:5000],
                user_agent=user_agent,
                ip_address=ip_address,
            )
        except Exception as e:
            # If saving error log fails, just log it (don't break error handling)
            logger.error(f"Failed to save error log in middleware: {str(e)}")
        
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

