from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views, views_schools
from .api_views import ConstituencyAPIView, WardAPIView

app_name = 'home'

urlpatterns = [
    # Regular views
    path("", views.landing_page, name="home"),
    path("mysubject/new/", login_required(views.create_mysubject), name="create_mysubject"),
    path("swap/new/", login_required(views.create_swap), name="create_swap"),
    path("swaps/", views.all_swaps, name="all_swaps"),
    path("swaps/mine/", login_required(views.my_swaps), name="my_swaps"),
    path("swaps/<int:swap_id>/", views.swap_detail, name="swap_detail"),
    path("swaps/<int:swap_id>/request/", login_required(views.request_swap), name="request_swap"),
    path("swaps/<int:swap_id>/toggle-status/", login_required(views.toggle_swap_status), name="toggle_swap_status"),
    path("swaps/<int:swap_id>/archive/", login_required(views.archive_swap), name="archive_swap"),
    path("swap-requests/<int:request_id>/accept/", login_required(views.accept_swap_request), name="accept_swap_request"),
    path("swap-requests/<int:request_id>/reject/", login_required(views.reject_swap_request), name="reject_swap_request"),
    
    # User swap requests
    path("my-swap-requests/", login_required(views.my_swap_requests), name="my_swap_requests"),
    
    # API endpoints
    path("api/constituencies/", ConstituencyAPIView.as_view(), name="api_constituencies"),
    path("api/wards/", WardAPIView.as_view(), name="api_wards"),
    
    # Swap preferences
    
    # User preferences
    path("preferences/", login_required(views.swap_preferences), name="swap_preferences"),
    
    # School management
    path("schools/", views.all_schools, name="all_schools"),
    path("schools/new/", login_required(views.create_school), name="create_school"),
    path("schools/search/", login_required(views_schools.SchoolSearchView.as_view()), name="school_search"),
    path("schools/attach/", login_required(views_schools.AttachSchoolView.as_view()), name="attach_school"),
    path("schools/get-constituencies/", views.get_constituencies, name="get_constituencies"),
    path("schools/get-wards/", views.get_wards, name="get_wards"),
    path("schools/<int:school_id>/edit/", login_required(views.edit_school), name="edit_school"),
    path("schools/<int:school_id>/delete/", login_required(views.delete_school), name="delete_school"),
]


