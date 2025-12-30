from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from . import views

app_name = 'users'


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<int:user_id>/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/completion/', views.profile_completion_view, name='profile_completion'),
    path('password/change/', views.password_change_view, name='password_change'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin/users/', views.admin_users_view, name='admin_users'),
    path('admin/users/<int:user_id>/edit/', views.admin_edit_user_view, name='admin_edit_user'),
    path('admin/users/<int:user_id>/delete/', views.admin_delete_user_view, name='admin_delete_user'),
    
    # Django built-in password reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='users/password_reset.html',
        email_template_name='users/password_reset_email.html',
        subject_template_name='users/password_reset_subject.txt'
    ), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Swap functionality
    path('initiate-swap/<int:user_id>/', views.initiate_swap, name='initiate_swap'),
    path('find-secondary-matches/', views.find_secondary_matches, name='find_secondary_matches'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Teaching information
    path('teaching-info/', views.select_teaching_info, name='select_teaching_info'),
    
    # API endpoints
    path('api/levels/<int:level_id>/subjects/', 
         login_required(views.get_subjects_for_level), 
         name='get_subjects_for_level'),
         
    # Teacher management
    path('admin/teachers/<int:user_id>/subjects/', 
         login_required(views.manage_teacher_subjects), 
         name='manage_teacher_subjects'),
    path('admin/primary-matched-swaps/', 
         login_required(views.primary_matched_swaps), 
         name='primary_matched_swaps'),
    path('admin/high-school-matched-swaps/', 
         login_required(views.high_school_matched_swaps), 
         name='high_school_matched_swaps'),
    path('api/levels/<int:level_id>/subjects/', 
         login_required(views.get_subjects_for_level), 
         name='get_subjects_for_level'),
] 