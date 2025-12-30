from django.urls import path
from .views_admin import user_management, user_potential_matches

app_name = 'users_admin'

urlpatterns = [
    path('users/', user_management, name='user_management'),
    path('users/<int:user_id>/potential-matches/', user_potential_matches, name='user_potential_matches'),
]
