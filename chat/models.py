from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class UserQuery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_queries')
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username}'s query at {self.created_at}"

class AIResponse(models.Model):
    query = models.OneToOneField(UserQuery, on_delete=models.CASCADE, related_name='ai_response')
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Response to {self.query.id} at {self.created_at}"
