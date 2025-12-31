"""
Custom error handlers for TSCSwap application.
"""
from django.shortcuts import render
from django.http import HttpResponseServerError, HttpResponseNotFound, HttpResponseForbidden
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
    
    context = {
        'error_title': error_info['title'],
        'error_message': error_info['message'],
        'status_code': error_info['status_code'],
        'user': request.user if hasattr(request, 'user') else None,
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

