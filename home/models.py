from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL
# Create your models here.
class Curriculum(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Level(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    curriculum = models.ForeignKey(Curriculum,null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, null=True, blank=True)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'level')
        ordering = ['name']

    def __str__(self):
        return self.name
    
class MySubject(models.Model):
    subject = models.ManyToManyField(Subject)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user}"

class Counties(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



class Constituencies(models.Model):
    name = models.CharField(max_length=255)
    county = models.ForeignKey(Counties, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Wards(models.Model):
    name = models.CharField(max_length=255)
    constituency = models.ForeignKey(Constituencies, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Schools(models.Model):
    Boarding = (
        ('Day', 'Day'),
        ('Boarding', 'Boarding'),
        ('Day and Boarding', 'Day and Boarding'),
    )
    Gender = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Mixed', 'Mixed'),
    )
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=255, choices=Gender)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    boarding = models.CharField(max_length=255, choices=Boarding)
    curriculum = models.ForeignKey(Curriculum, on_delete=models.CASCADE)
    postal_code = models.CharField(max_length=255)
    ward = models.ForeignKey(Wards, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_hardship = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Swaps(models.Model):
    Gender = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Mixed', 'Mixed'),
        ('Any', 'Any'),
    )
    Boarding = (
        ('Day', 'Day'),
        ('Boarding', 'Boarding'),
        ('Day and Boarding', 'Day and Boarding'),
        ('Any', 'Any'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    gender = models.CharField(max_length=255, choices=Gender)
    boarding = models.CharField(max_length=255, choices=Boarding)   
    constituency = models.ForeignKey(Constituencies,null=True, blank=True, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties,null=True, blank=True, on_delete=models.CASCADE)
    ward = models.ForeignKey(Wards,null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.user}"

class SwapRequests(models.Model):
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_swap_requests')
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_swap_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    accepted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = [['requester', 'target']]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.requester} -> {self.target}"


class SwapPreference(models.Model):
    Hardship = (
        ('Yes', 'Yes'),
        ('No', 'No'),
        ('Any', 'Any')
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    desired_county = models.ForeignKey(Counties, null=True, on_delete=models.SET_NULL, related_name='desired_swaps')
    desired_constituency = models.ForeignKey(Constituencies, null=True, on_delete=models.SET_NULL, blank=True)
    desired_ward = models.ForeignKey(Wards, null=True, on_delete=models.SET_NULL, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    open_to_all = models.ManyToManyField(Counties, related_name='open_to_all')
    is_hardship = models.CharField(max_length=255, choices=Hardship, default='Any')
    def __str__(self):
        return f"Preferences for {self.user}"

    class Meta:
        verbose_name = "Swap Preference"
        verbose_name_plural = "Swap Preferences"

class FastSwap(models.Model):
    names = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    school = models.ForeignKey(Schools, on_delete=models.CASCADE, null=True, blank=True)
    most_preferred = models.ForeignKey(Counties, on_delete=models.CASCADE, null=True, blank=True, related_name='fastswap_preferred')
    current_county = models.ForeignKey(Counties, on_delete=models.CASCADE, null=True, blank=True, related_name='fastswap_current')
    current_constituency = models.ForeignKey(Constituencies, on_delete=models.CASCADE, null=True, blank=True, related_name='fastswap_constituency')
    current_ward = models.ForeignKey(Wards, on_delete=models.CASCADE, null=True, blank=True, related_name='fastswap_ward')
    acceptable_county = models.ManyToManyField(Counties, related_name='acceptable_county')
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(Subject)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.names


class Bookmark(models.Model):
    """
    Model to store user bookmarks/wishlist for swaps and fast swaps.
    A user can bookmark either a Swap or a FastSwap.
    """
    BOOKMARK_TYPES = (
        ('swap', 'Regular Swap'),
        ('fastswap', 'Fast Swap'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    swap = models.ForeignKey(Swaps, on_delete=models.CASCADE, null=True, blank=True, related_name='bookmarks')
    fast_swap = models.ForeignKey(FastSwap, on_delete=models.CASCADE, null=True, blank=True, related_name='bookmarks')
    bookmark_type = models.CharField(max_length=20, choices=BOOKMARK_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Ensure a user can only bookmark the same item once
        unique_together = [
            ('user', 'swap'),
            ('user', 'fast_swap'),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        if self.bookmark_type == 'swap' and self.swap:
            return f"{self.user} bookmarked swap #{self.swap.id}"
        elif self.bookmark_type == 'fastswap' and self.fast_swap:
            return f"{self.user} bookmarked fastswap #{self.fast_swap.id}"
        return f"{self.user} bookmark"


class ErrorLog(models.Model):
    """
    Model to store error logs for debugging and monitoring.
    Captures user, error time, page/URL, and error details.
    """
    ERROR_TYPES = (
        ('server_error', 'Server Error (500)'),
        ('not_found', 'Not Found (404)'),
        ('forbidden', 'Forbidden (403)'),
        ('bad_request', 'Bad Request (400)'),
        ('exception', 'Unhandled Exception'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='error_logs',
        help_text='User who encountered the error (null for anonymous users)'
    )
    error_type = models.CharField(
        max_length=20, 
        choices=ERROR_TYPES, 
        default='exception',
        help_text='Type of error that occurred'
    )
    error_message = models.TextField(
        help_text='Error message or exception details'
    )
    page_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text='URL/page where the error occurred'
    )
    request_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='Request path where error occurred'
    )
    request_method = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='HTTP method (GET, POST, etc.)'
    )
    status_code = models.IntegerField(
        null=True,
        blank=True,
        help_text='HTTP status code'
    )
    exception_type = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Type of exception (e.g., ValueError, AttributeError)'
    )
    traceback = models.TextField(
        null=True,
        blank=True,
        help_text='Full traceback for debugging (only in development)'
    )
    user_agent = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='User agent/browser information'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the user'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the error occurred'
    )
    resolved = models.BooleanField(
        default=False,
        help_text='Whether this error has been resolved'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the error was marked as resolved'
    )
    notes = models.TextField(
        null=True,
        blank=True,
        help_text='Admin notes about this error'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Error Log'
        verbose_name_plural = 'Error Logs'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['error_type']),
            models.Index(fields=['resolved']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        user_str = self.user.email if self.user else 'Anonymous'
        return f"{self.error_type} - {user_str} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def mark_resolved(self):
        """Mark this error as resolved."""
        self.resolved = True
        self.resolved_at = timezone.now()
        self.save(update_fields=['resolved', 'resolved_at'])
