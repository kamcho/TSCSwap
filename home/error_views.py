"""
Custom error handlers for TSCSwap application.
"""
from django.shortcuts import render
from django.http import HttpResponseServerError, HttpResponseNotFound, HttpResponseForbidden
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def error_page(request, error_type='server_error', exception=None):
    """
    Generic error page handler.
    
    Args:
        request: The HTTP request
        error_type: Type of error ('server_error', 'not_found', 'forbidden', 'bad_request')
        exception: The exception that occurred (optional)
    """
    error_messages = {
        'server_error': {
            'title': 'Server Error',
            'message': 'We are having a problem processing your request. Please try again later.',
            'status_code': 500
        },
        'not_found': {
            'title': 'Page Not Found',
            'message': 'The page you are looking for could not be found.',
            'status_code': 404
        },
        'forbidden': {
            'title': 'Access Forbidden',
            'message': 'You do not have permission to access this resource.',
            'status_code': 403
        },
        'bad_request': {
            'title': 'Bad Request',
            'message': 'Your request could not be processed. Please check your input and try again.',
            'status_code': 400
        }
    }
    
    error_info = error_messages.get(error_type, error_messages['server_error'])
    
    # Log the error for debugging (but don't expose to user)
    if exception:
        logger.error(f"{error_info['title']}: {str(exception)}", exc_info=True)
    
    # Save error to database
    try:
        from home.models import ErrorLog
        import traceback
        
        # Get user (may be AnonymousUser)
        user = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
        
        # Get exception details
        exception_type = None
        exception_message = str(exception) if exception else error_info['message']
        exception_traceback = None
        
        if exception:
            exception_type = type(exception).__name__
            try:
                exception_traceback = traceback.format_exc()
            except:
                pass
        
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
            error_type=error_type,
            error_message=exception_message[:1000] if len(exception_message) > 1000 else exception_message,
            page_url=request.build_absolute_uri()[:500] if hasattr(request, 'build_absolute_uri') else None,
            request_path=request.path[:500] if hasattr(request, 'path') else None,
            request_method=request.method if hasattr(request, 'method') else None,
            status_code=error_info['status_code'],
            exception_type=exception_type,
            traceback=exception_traceback[:5000] if exception_traceback and len(exception_traceback) > 5000 else exception_traceback,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    except Exception as e:
        # If saving error log fails, just log it (don't break error page)
        logger.error(f"Failed to save error log: {str(e)}")
    
    context = {
        'error_title': error_info['title'],
        'error_message': error_info['message'],
        'status_code': error_info['status_code'],
        'user': user if 'user' in locals() else (request.user if hasattr(request, 'user') else None),
    }
    
    return render(request, 'home/error_page.html', context, status=error_info['status_code'])


def handler500(request, exception=None):
    """Handler for 500 server errors."""
    return error_page(request, 'server_error', exception)


def handler404(request, exception=None):
    """Handler for 404 not found errors."""
    return error_page(request, 'not_found', exception)


def handler403(request, exception=None):
    """Handler for 403 forbidden errors."""
    return error_page(request, 'forbidden', exception)


def handler400(request, exception=None):
    """Handler for 400 bad request errors."""
    return error_page(request, 'bad_request', exception)

