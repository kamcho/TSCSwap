from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    MySubject, Subject, Level, Curriculum, Counties, Constituencies, 
    Wards, Swaps, SwapRequests, Schools, SwapPreference, ErrorLog
)


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    """Admin interface for ErrorLog model."""
    list_display = [
        'id', 'error_type', 'user_display', 'status_code', 'request_path_short', 
        'created_at', 'resolved', 'ip_address'
    ]
    list_filter = [
        'error_type', 'status_code', 'resolved', 'created_at', 'request_method'
    ]
    search_fields = [
        'error_message', 'request_path', 'page_url', 'user__email', 
        'user__username', 'exception_type', 'ip_address'
    ]
    readonly_fields = [
        'user', 'error_type', 'error_message', 'page_url', 'request_path', 
        'request_method', 'status_code', 'exception_type', 'traceback', 
        'user_agent', 'ip_address', 'created_at', 'resolved_at'
    ]
    fieldsets = (
        ('Error Information', {
            'fields': ('error_type', 'status_code', 'error_message', 'exception_type')
        }),
        ('Request Details', {
            'fields': ('user', 'request_path', 'page_url', 'request_method', 'user_agent', 'ip_address')
        }),
        ('Technical Details', {
            'fields': ('traceback',),
            'classes': ('collapse',)
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolved_at', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions = ['mark_as_resolved', 'mark_as_unresolved']
    
    def user_display(self, obj):
        """Display user with link to user admin."""
        if obj.user:
            url = reverse('admin:users_myuser_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return format_html('<span style="color: #999;">Anonymous</span>')
    user_display.short_description = 'User'
    
    def request_path_short(self, obj):
        """Display shortened request path."""
        if obj.request_path:
            if len(obj.request_path) > 50:
                return obj.request_path[:47] + '...'
            return obj.request_path
        return '-'
    request_path_short.short_description = 'Request Path'
    
    def mark_as_resolved(self, request, queryset):
        """Mark selected errors as resolved."""
        updated = queryset.update(resolved=True, resolved_at=timezone.now())
        self.message_user(request, f'{updated} error(s) marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected errors as resolved'
    
    def mark_as_unresolved(self, request, queryset):
        """Mark selected errors as unresolved."""
        updated = queryset.update(resolved=False, resolved_at=None)
        self.message_user(request, f'{updated} error(s) marked as unresolved.')
    mark_as_unresolved.short_description = 'Mark selected errors as unresolved'
    
    def has_add_permission(self, request):
        """Disable manual creation of error logs."""
        return False


admin.site.register(MySubject)
admin.site.register(Subject)
admin.site.register(Level)
admin.site.register(Curriculum)
admin.site.register(Counties)
admin.site.register(Constituencies)
admin.site.register(Wards)
admin.site.register(SwapRequests)
admin.site.register(Swaps)
admin.site.register(Schools)
admin.site.register(SwapPreference)