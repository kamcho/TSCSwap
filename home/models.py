from django.db import models
from django.conf import settings
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    curriculum = models.ForeignKey(Curriculum, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    swap = models.ForeignKey(Swaps, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    accepted = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.user} - {self.swap}"


class SwapPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    desired_county = models.ForeignKey(Counties, null=True, on_delete=models.SET_NULL, related_name='desired_swaps')
    desired_constituency = models.ForeignKey(Constituencies, null=True, on_delete=models.SET_NULL)
    desired_ward = models.ForeignKey(Wards, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user}"

    class Meta:
        verbose_name = "Swap Preference"
        verbose_name_plural = "Swap Preferences"