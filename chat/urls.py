from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('send/', views.chat_view, name='send_message'),
]
