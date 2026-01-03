from collections import namedtuple
from itertools import combinations

from django.contrib import messages
from django.contrib.auth import (authenticate, get_user_model, login, logout,
                               update_session_auth_hash)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import MyUser
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET
from django.http import HttpResponseForbidden

from home.models import (
    Level, Subject, MySubject, Schools, SwapPreference, 
    Counties, Constituencies, Wards, Swaps, SwapRequests
)
from .models import MyUser, PersonalProfile

def get_whatsapp_message(user, completion_data):
    """
    Generate a WhatsApp message based on user's profile completion status.
    
    Args:
        user: The user object
        completion_data: Dictionary containing completion data from get_profile_completion_data()
        
    Returns:
        str: The formatted WhatsApp message
    """
    # Base URL for WhatsApp
    base_message = ""
    
    if completion_data['percentage'] < 100:
        # Incomplete profile message
        base_message = "Hello {name} 👋\n\n"
        base_message += "I hope you're doing well.\n"
        base_message += "My name is Kevin Gitundu, Administrator at Find A Swap.\n\n"
        base_message += "We noticed your profile is about {percentage}% complete. "
        base_message += "Completing it will help us match you with the best possible swap partners more accurately.\n\n"
        base_message += "Kindly update the following details when you have a moment:\n\n"
        
        # Add missing fields with specific guidance
        missing_fields = []
        if not completion_data['has_basic_info']:
            missing_fields.append("Basic information (name, contact details)")
        if not completion_data['has_school_link']:
            missing_fields.append("School information (school name, county, constituency & ward)")
        if not completion_data['has_level']:
            missing_fields.append("Teaching level")
        if completion_data.get('subject_required', False) and not completion_data['has_subjects']:
            missing_fields.append("Teaching subjects: https://www.tscswap.com/mysubject/new/")
        if not completion_data['has_swap_prefs']:
            missing_fields.append("Swap preferences: https://www.tscswap.com/preferences/")
            
        base_message += "• " + "\n• ".join(missing_fields)
        base_message += "\n\nIf you need any help, feel free to message me—I'll be happy to assist 😊\n"
        base_message += "\nThank you for being part of Find A Swap."
    else:
        # Complete profile message
        base_message = "Hello {name} 👋\n\n"
        base_message += "I hope you're doing well.\n"
        base_message += "My name is Kevin Gitundu, Administrator at Find A Swap.\n\n"
        base_message += "Thank you for completing your profile! We're actively searching for the best swap matches for you. "
        base_message += "You'll be the first to know when we find potential matches.\n\n"
        base_message += "You can also check for new matches in your dashboard: {dashboard_url}\n\n"
        base_message += "If you need any assistance or have questions, feel free to message me—I'll be happy to help! 😊\n"
        base_message += "\nThank you for being part of Find A Swap."
    
    # Format the message with user's name and profile URL
    profile_url = f"www.tscswap.com{reverse('users:profile_edit')}"
    dashboard_url = f"www.tscswap.com{reverse('users:dashboard')}"
    
    return base_message.format(
        name=user.get_full_name() or 'there',
        percentage=completion_data['percentage'],
        profile_url=profile_url,
        dashboard_url=dashboard_url
    )
from .templatetags.match_helpers import get_secondary_teacher_matches
from .forms import (
    CustomPasswordChangeForm, MyAuthenticationForm, 
    MyUserCreationForm, ProfileEditForm, UserEditForm,
    SubjectSelectionForm
)

# Define a named tuple to hold matched swap information
MatchedSwap = namedtuple('MatchedSwap', [
    'teacher_a', 
    'teacher_a_swap_pref', 
    'teacher_b', 
    'teacher_b_swap_pref'
])


def staff_required(login_url=None):
    """
    Decorator for views that checks that the user is staff.
    """
    return user_passes_test(lambda u: u.is_staff, login_url=login_url)

# Create your views here.

def login_view(request):
    if request.user.is_authenticated:
        # Check if user has completed their profile
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            if not (profile.first_name and profile.last_name):
                messages.info(request, 'Please complete your profile to continue.')
                return redirect('users:profile_completion')
        next_url = request.GET.get('next') or request.POST.get('next')
        return redirect(next_url or 'home:home')  # Updated to use 'home:home' namespace
    
    if request.method == 'POST':
        form = MyAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # Check if user has completed their profile
                if hasattr(user, 'profile'):
                    profile = user.profile
                    if not (profile.first_name and profile.last_name):
                        messages.info(request, 'Please complete your profile to continue.')
                        return redirect('users:profile_completion')
                
                next_url = request.GET.get('next') or request.POST.get('next')
                return redirect(next_url or 'home:home')  # Updated to use 'home:home' namespace
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MyAuthenticationForm()

    context = {'form': form, 'next': request.GET.get('next')}
    return render(request, 'users/login.html', context)

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home:home')  # Updated to use 'home:home' namespace
    
    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Clear any existing messages and show only this one
            messages.get_messages(request)
            messages.success(request, f'Account created successfully! Please complete your profile.')
            return redirect('users:profile_edit')  # Redirect to profile edit page
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MyUserCreationForm()
    
    return render(request, 'users/signup.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home:home')

@login_required
def profile_view(request, user_id=None):
    """
    View for viewing a user's profile.
    If user_id is provided, show that user's profile. Otherwise, show the logged-in user's profile.
    """
    # If no user_id is provided, default to the logged-in user
    if user_id is None:
        user = request.user
    else:
        try:
            user = MyUser.objects.get(id=user_id)
            # If the requested user is the same as the logged-in user, redirect to their own profile
            if user == request.user:
                return redirect('users:profile')
        except MyUser.DoesNotExist:
            raise Http404("User not found")
    
    # Get the profile for the requested user
    profile = get_object_or_404(PersonalProfile, user=user)
    
    # Get user's school and subjects
    school = profile.school
    my_subjects = MySubject.objects.filter(user=user).first()
    subjects = my_subjects.subject.all() if my_subjects else []
    
    # Build full name from personal profile
    name_parts = []
    if profile.first_name:
        name_parts.append(profile.first_name)
    if profile.surname:
        name_parts.append(profile.surname)
    elif profile.last_name:  # Only use last_name if surname isn't set
        name_parts.append(profile.last_name)
    full_name = ' '.join(name_parts) if name_parts else user.email
    
    # Check if viewing own profile
    is_own_profile = (user == request.user)
    
    context = {
        'profile': profile,
        'school': school,
        'subjects': subjects,
        'full_name': full_name,
        'profile_user': user,  # The user whose profile is being viewed
        'is_own_profile': is_own_profile
    }
    return render(request, 'users/profile.html', context)

@login_required
def profile_edit_view(request):
    # Get or create the user's profile
    profile, created = PersonalProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ProfileEditForm(
            request.POST, 
            request.FILES, 
            instance=profile
        )
        
        if form.is_valid():
            # Save profile - the form's save method handles everything
            profile = form.save(commit=True)
            
            # Update session with new profile picture if it exists
            if hasattr(profile, 'profile_picture') and profile.profile_picture:
                request.session['profile_picture'] = profile.profile_picture.url
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile_edit')
        else:
            messages.error(request, 'Please correct the errors below.')
            # Print form errors for debugging
            print("Form errors:", form.errors)
    else:
        form = ProfileEditForm(
            instance=profile,
            initial={
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'surname': getattr(profile, 'surname', ''),
                'phone': profile.phone,
                'gender': profile.gender,
                'profile_picture': profile.profile_picture if hasattr(profile, 'profile_picture') else None
            }
        )
    
    return render(request, 'users/profile_edit.html', {'form': form})

def parse_name(full_name):
    """Parse full name into first name, last name, and surname.
    
    Rules:
    - First name: First word
    - Last name: Second word (if exists)
    - Surname: All other words combined (if more than 2 names)
    """
    names = full_name.strip().split()
    if not names:
        return '', '', ''
    
    if len(names) == 1:
        return names[0], '', ''  # Only first name
    elif len(names) == 2:
        return names[0], names[1], ''  # First and last name
    else:
        # First name, last name (second word), and surname (all other names)
        return names[0], names[1], ' '.join(names[2:])

@login_required
def profile_completion_view(request):
    if request.method == 'POST':
        # Check if this is the final submission after verification
        if 'verify_kra' in request.POST:
            # Get form data from hidden fields
            id_number = request.POST.get('id_number', '').strip()
            
            # Get the full name from KRA data
            kra_data = request.session.get('kra_data', {})
            full_name = kra_data.get('name', '').strip()
            
            # Parse the full name
            first_name, last_name, surname = parse_name(full_name)
            
            # Check if ID number is already in use by another user
            from django.contrib.auth import get_user_model
            from django.db import IntegrityError
            
            user = request.user
            User = get_user_model()
            
            # Check if ID number is already in use by another user
            if User.objects.exclude(pk=user.pk).filter(id_number=id_number).exists():
                messages.error(request, 'This ID number is already registered with another account. Please contact support if this is an error.')
                return render(request, 'users/profile_completion.html', {
                    'id_number': id_number,
                    'first_name': first_name,
                    'show_verification_modal': True,
                    'kra_data': {
                        'name': kra_data.get('name', ''),
                        'id_number': id_number,
                    }
                })
            
            # Update user model
            try:
                user.id_number = id_number
                user.first_name = first_name
                user.last_name = last_name  # Second name is always the last name
                user.save()
            except IntegrityError:
                messages.error(request, 'This ID number is already registered. Please contact support if this is an error.')
                return render(request, 'users/profile_completion.html', {
                    'id_number': id_number,
                    'first_name': first_name,
                    'show_verification_modal': True,
                    'kra_data': {
                        'name': kra_data.get('name', ''),
                        'id_number': id_number,
                    }
                })
            
            # Update or create personal profile
            profile, created = PersonalProfile.objects.get_or_create(user=user)
            profile.first_name = first_name
            profile.last_name = last_name  # Second name is the last name
            profile.surname = surname      # All other names (if any)
            
            # Store any additional names in other_names field
            if surname:
                profile.other_names = surname
            
            # Save additional KRA data if available
            if 'date_of_birth' in kra_data:
                profile.date_of_birth = kra_data['date_of_birth']
            if 'gender' in kra_data:
                # Ensure gender is a single character (M/F/O)
                gender = str(kra_data['gender']).upper()
                profile.gender = gender[0] if gender else 'O'
                
            profile.save()
            
            # Clean up session data
            if 'kra_data' in request.session:
                del request.session['kra_data']
            
            messages.success(request, 'Profile updated successfully! Please select your teaching level and subjects.')
            return redirect('users:select_teaching_info')
            
        else:
            # Initial form submission - verify KRA details
            id_number = request.POST.get('id_number', '').strip()
            first_name = request.POST.get('first_name', '').strip()

            # Validate required fields
            if not id_number or not first_name:
                messages.error(request, 'Both ID number and first name are required')
                return render(request, 'users/profile_completion.html', {
                    'id_number': id_number,
                    'first_name': first_name
                })

            # Verify KRA details
            kra_verification = verify_kra_details(id_number)

            if not kra_verification['success']:
                messages.error(request, f"TSC verification failed: Name doesnt match with ID Number")
                return render(request, 'users/profile_completion.html', {
                    'id_number': id_number,
                    'first_name': first_name
                })

            # Get KRA name and clean it for comparison
            kra_name = kra_verification['data'].get('name', '')
            kra_first_name = kra_name.split()[0].lower() if kra_name else ''

            # Compare first names (case-insensitive)
            if first_name.lower() != kra_first_name:
                messages.error(
                    request,
                    "The first name you entered doesn't match the one on record with TSC . "
                )
                return render(request, 'users/profile_completion.html', {
                    'id_number': id_number,
                    'first_name': first_name
                })
            
            # Store KRA data in session for the final submission
            request.session['kra_data'] = {
                'name': kra_name,
                'id_number': id_number,
                # Add any other KRA data you want to save
            }
            
            # Prepare context for template
            context = {
                'id_number': id_number,
                'first_name': first_name.capitalize(),
                'kra_data': {
                    'name': kra_name,
                    'id_number': id_number,
                },
                'show_verification_modal': True
            }
            return render(request, 'users/profile_completion.html', context)

    return render(request, 'users/profile_completion.html')

@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'users/password_change.html', {'form': form})

@login_required
def dashboard(request):
    """User dashboard with overview of user's swaps and requests"""
    user = request.user
    
    # Get active swaps created by the user
    active_swaps_queryset = Swaps.objects.filter(user=user, status=True)
    active_swaps_count = active_swaps_queryset.count()
    
    # Get swap requests
    # Requests sent by the user
    sent_requests = SwapRequests.objects.filter(requester=user, is_active=True).select_related(
        'target__profile'
    ).order_by('-created_at')
    
    # Requests received by the user
    received_requests = SwapRequests.objects.filter(
        target=user, 
        is_active=True
    ).select_related(
        'requester__profile'
    ).order_by('-created_at')
    
    # Count of pending requests for the user's swaps
    pending_requests = received_requests.filter(accepted=False).count()
    
    # Check profile completion status
    has_profile = hasattr(user, 'profile') and user.profile is not None
    
    # 1. Personal Information - Check names and phone in PersonalProfile
    personal_info_complete = False
    if has_profile:
        personal_info_complete = all([
            user.profile.first_name,  # First name from PersonalProfile
            user.profile.surname or user.profile.last_name,  # Either surname or last name from PersonalProfile
            user.profile.phone  # Phone from PersonalProfile
        ])
    
    # 2. Teaching Level Information
    teaching_level_complete = has_profile and hasattr(user.profile, 'level') and user.profile.level is not None
    is_secondary_level = False
    
    if teaching_level_complete and hasattr(user.profile.level, 'name'):
        level_name = user.profile.level.name.lower()
        is_secondary_level = 'secondary' in level_name or 'high' in level_name
    
    # 3. School Information
    school_info_complete = bool(has_profile and hasattr(user.profile, 'school') and user.profile.school is not None)
    
    # 4. Swap Preferences - Check using the correct related name
    try:
        # Try both possible related names
        swap_preference = user.swappreference if hasattr(user, 'swappreference') else None
        if swap_preference is None and hasattr(user, 'swap_preferences'):
            swap_preference = user.swap_preferences
        
        preferences_complete = swap_preference is not None
        
        # Debug output
        print("\n=== DEBUG: Profile Completion Status ===")
        print(f"Has profile: {has_profile}")
        print(f"Personal info complete: {personal_info_complete}")
        print(f"Teaching level complete: {teaching_level_complete}")
        print(f"School info complete: {school_info_complete}")
        print(f"Swap preference object: {swap_preference}")
        print(f"Swap preference exists: {swap_preference is not None}")
        print(f"User has swap_preferences attr: {hasattr(user, 'swap_preferences')}")
        print(f"User has swappreference attr: {hasattr(user, 'swappreference')}")
        if hasattr(user, 'swap_preferences'):
            print(f"swap_preferences type: {type(user.swap_preferences)}")
        print("===================================\n")
    except Exception as e:
        print(f"Error checking swap preferences: {e}")
        swap_preference = None
        preferences_complete = False
    
    # Debug information for completion checks
    debug_checks = {
        'has_profile': has_profile,
        'swap_preference_exists': swap_preference is not None,
        'swap_preference_open_to_all': getattr(swap_preference, 'open_to_all', None) if swap_preference else None,
        'swap_preference_desired_county': getattr(swap_preference, 'desired_county', None) if swap_preference else None,
        'preferences_complete': preferences_complete,
        'personal_info_complete': personal_info_complete,
        'teaching_level_complete': teaching_level_complete,
        'school_info_complete': school_info_complete,
        'has_swap_preference': swap_preference is not None,
        'preferences_complete': preferences_complete,
        'user_level': getattr(user.profile, 'level.name', 'No level') if has_profile and hasattr(user.profile, 'level') else 'No level',
        'has_school': has_profile and hasattr(user.profile, 'school') and user.profile.school is not None,
        'has_phone': has_profile and hasattr(user.profile, 'phone') and bool(user.profile.phone),
    }
    
    # Calculate completion percentage (4 sections, 25% each)
    completion_percentage = 0.0
    total_sections = 4  # personal_info, teaching_level, school_info, preferences
    completed_sections = 0

    if personal_info_complete:
        completion_percentage += 25.0
        completed_sections += 1
    if teaching_level_complete:
        completion_percentage += 25.0
        completed_sections += 1
    if school_info_complete:
        completion_percentage += 25.0
        completed_sections += 1
    if preferences_complete:
        completion_percentage += 25.0
        completed_sections += 1

    # Round to 2 decimal places
    completion_percentage = round(completion_percentage, 2)

    # Overall profile complete if all required sections are complete
    profile_complete = all([
        personal_info_complete,
        teaching_level_complete,
        school_info_complete,
        preferences_complete
    ])

    # Ensure completion percentage is 100% when all required sections are complete
    if profile_complete:
        completion_percentage = 100.00

    # Get subscription status
    subscription = getattr(user, 'my_subscription', None)
    has_active_subscription = subscription.is_active if subscription else False
    subscription_status = {
        'has_subscription': subscription is not None,
        'is_active': has_active_subscription,
        'type': subscription.sub_type if subscription else 'None',
        'expiry_date': subscription.expiry_date.strftime('%B %d, %Y') if subscription and subscription.expiry_date else 'N/A',
        'days_remaining': subscription.days_remaining if subscription else 0,
    }
    
    # Initialize potential matches
    potential_matches = []
    show_potential_matches_section = True
    potential_matches_message = None
    has_potential_matches = False
    
    # Only show potential matches if profile is 100% complete
    from users.templatetags.profile_checks import is_profile_complete
    
    if not is_profile_complete(user):
        potential_matches_message = "Complete your profile to see potential matches. Please complete all profile sections to 100%."
        has_potential_matches = False
        show_potential_matches_section = True
    else:
        # Reset the message since profile is complete
        potential_matches_message = None
        # User has a complete profile with school, find actual matches
        is_secondary = hasattr(user.profile.school, 'level') and ('secondary' in user.profile.school.level.name.lower() or 'high' in user.profile.school.level.name.lower())
        
        # Base queryset for potential matches
        from home.matching import find_matches
        matches = find_matches(user)
        
        # Limit to 5 matches for the dashboard
        matches = matches.distinct()[:5]
        
        # Assign directly - template expects User objects for match_card.html
        potential_matches = matches
        
        # Set flags based on whether we found any matches
        has_potential_matches = len(potential_matches) > 0
        show_potential_matches_section = True
        potential_matches_message = None if has_potential_matches else "No potential matches found at this time."

    # Get triangle swaps for this user
    triangle_swaps = []
    user_triangle_swaps = []
    
    if profile_complete and has_profile and user.profile.school:
        from home.triangle_swap_utils import (
            find_triangle_swaps_primary, 
            find_triangle_swaps_secondary,
            get_current_county,
            get_user_subjects
        )
        
        # Determine if user is primary or secondary
        user_school_level = user.profile.school.level
        is_secondary = user_school_level and ('secondary' in user_school_level.name.lower() or 'high' in user_school_level.name.lower())
        
        # Get all teachers at the same level
        teachers = MyUser.objects.filter(
            is_active=True,
            role='Teacher',
            profile__isnull=False,
            profile__school__isnull=False,
            profile__school__level=user_school_level,
            swappreference__isnull=False
        ).select_related(
            'profile__school__ward__constituency__county',
            'swappreference__desired_county',
            'profile__school__level'
        ).prefetch_related(
            'swappreference__open_to_all',
            'mysubject_set__subject'
        ).distinct()
        
        # Find triangle swaps
        if is_secondary:
            all_triangles = find_triangle_swaps_secondary(teachers)
        else:
            all_triangles = find_triangle_swaps_primary(teachers)
        
        # Filter triangles that include the current user
        for teacher_a, teacher_b, teacher_c in all_triangles:
            if user.id in [teacher_a.id, teacher_b.id, teacher_c.id]:
                county_a = get_current_county(teacher_a)
                county_b = get_current_county(teacher_b)
                county_c = get_current_county(teacher_c)
                
                triangle_data = {
                    'teacher_a': {
                        'user': teacher_a,
                        'name': teacher_a.profile.first_name + ' ' + (teacher_a.profile.surname or teacher_a.profile.last_name or '') if teacher_a.profile.first_name else teacher_a.email,
                        'current_location': county_a.name if county_a else 'Unknown',
                        'wants_location': county_b.name if county_b else 'Unknown',
                        'is_current_user': teacher_a.id == user.id,
                    },
                    'teacher_b': {
                        'user': teacher_b,
                        'name': teacher_b.profile.first_name + ' ' + (teacher_b.profile.surname or teacher_b.profile.last_name or '') if teacher_b.profile.first_name else teacher_b.email,
                        'current_location': county_b.name if county_b else 'Unknown',
                        'wants_location': county_c.name if county_c else 'Unknown',
                        'is_current_user': teacher_b.id == user.id,
                    },
                    'teacher_c': {
                        'user': teacher_c,
                        'name': teacher_c.profile.first_name + ' ' + (teacher_c.profile.surname or teacher_c.profile.last_name or '') if teacher_c.profile.first_name else teacher_c.email,
                        'current_location': county_c.name if county_c else 'Unknown',
                        'wants_location': county_a.name if county_a else 'Unknown',
                        'is_current_user': teacher_c.id == user.id,
                    },
                }
                
                if is_secondary:
                    # Add common subjects for secondary
                    subjects_a = get_user_subjects(teacher_a)
                    subjects_b = get_user_subjects(teacher_b)
                    subjects_c = get_user_subjects(teacher_c)
                    common_subjects = subjects_a.intersection(subjects_b).intersection(subjects_c)
                    from home.models import Subject
                    triangle_data['common_subjects'] = [Subject.objects.get(id=sid).name for sid in common_subjects if Subject.objects.filter(id=sid).exists()]
                
                user_triangle_swaps.append(triangle_data)
    
    # Debug information
    debug_info = {
        'profile_complete': is_profile_complete(user),
        'completion_percentage': completion_percentage,
        'has_school': has_profile and hasattr(user.profile, 'school') and user.profile.school is not None,
        'has_level': has_profile and hasattr(user.profile, 'level') and user.profile.level is not None,
        'has_swap_preference': hasattr(user, 'swap_preferences') and user.swap_preferences is not None,
        'has_subjects': hasattr(user, 'mysubject_set') and user.mysubject_set.count() > 0
    }

    # Prepare context with all required variables
    # Ensure we have the latest completion status
    profile_complete_status = all([
        personal_info_complete,
        teaching_level_complete,
        school_info_complete,
        preferences_complete
    ])
    
    context = {
        'user': user,
        'active_swaps': active_swaps_count,
        'active_swaps_queryset': active_swaps_queryset,
        'pending_requests': pending_requests,
        'sent_requests': sent_requests,
        'received_requests': received_requests,
        'profile_complete': profile_complete_status,
        'completion_percentage': int(completion_percentage),
        'is_secondary_level': is_secondary_level,
        'subscription': subscription_status,
        'swap_preference': swap_preference,
        'potential_matches': potential_matches if profile_complete_status else [],
        'has_potential_matches': has_potential_matches if profile_complete_status and 'has_potential_matches' in locals() else False,
        'show_potential_matches_section': True,
        'potential_matches_message': potential_matches_message,
        'debug_info': debug_checks,
        'triangle_swaps': user_triangle_swaps if 'user_triangle_swaps' in locals() else [],
        'has_triangle_swaps': len(user_triangle_swaps) > 0 if 'user_triangle_swaps' in locals() else False,
        
        # Completion status for each section - ensure these are booleans
        'personal_info_complete': bool(personal_info_complete),
        'teaching_level_complete': bool(teaching_level_complete),
        'school_info_complete': bool(school_info_complete),
        'preferences_complete': bool(preferences_complete),  # Force boolean
        
        # Debug info
        'has_profile': has_profile,
        'has_phone': has_profile and hasattr(user.profile, 'phone') and bool(user.profile.phone),
        'has_level': has_profile and hasattr(user.profile, 'level') and user.profile.level is not None,
        'has_school': has_profile and hasattr(user.profile, 'school') and user.profile.school is not None,
        'has_swap_preference': swap_preference is not None,
    }
    
    # Get user's chat history (WhatsApp conversations)
    try:
        from chat.models import UserQuery, AIResponse
        user_chats = UserQuery.objects.filter(user=user).select_related('ai_response').order_by('-created_at')[:20]
        
        # Format chats with responses
        chat_history = []
        for query in user_chats:
            try:
                response = query.ai_response
                chat_history.append({
                    'query': query,
                    'response': response,
                    'created_at': query.created_at,
                })
            except AIResponse.DoesNotExist:
                # Query exists but no response yet
                chat_history.append({
                    'query': query,
                    'response': None,
                    'created_at': query.created_at,
                })
        
        context['chat_history'] = chat_history
        context['has_chat_history'] = len(chat_history) > 0
    except Exception as e:
        print(f"Error fetching chat history: {str(e)}")
        context['chat_history'] = []
        context['has_chat_history'] = False
    
    return render(request, 'users/dashboard.html', context)

@login_required
def select_teaching_info(request):
    """View for selecting teaching level and subjects"""
    # Get or create the user's profile
    profile, created = PersonalProfile.objects.get_or_create(user=request.user)
    
    # Check if the user already has a level set
    has_level = hasattr(profile, 'level') and profile.level is not None
    
    if request.method == 'POST':
        level_id = request.POST.get('level')
        subject_ids = request.POST.getlist('subjects')
        
        if not level_id:
            messages.error(request, 'Please select your teaching level.')
        elif not subject_ids:
            messages.error(request, 'Please select at least one subject you teach.')
        else:
            try:
                # Update user's level in personal profile
                level = get_object_or_404(Level, id=level_id)
                profile.level = level
                profile.save()
                
                # Get or create a single MySubject entry for the user
                # First, check if there are multiple and consolidate them
                existing_subjects = MySubject.objects.filter(user=request.user)
                
                if existing_subjects.exists():
                    # If multiple exist, use the first one and delete others
                    my_subject = existing_subjects.first()
                    # Delete any additional MySubject entries
                    if existing_subjects.count() > 1:
                        existing_subjects.exclude(pk=my_subject.pk).delete()
                else:
                    # Create new if none exists
                    my_subject = MySubject.objects.create(user=request.user)
                
                # Clear existing subjects and add new ones
                my_subject.subject.clear()
                for subject_id in subject_ids:
                    subject = get_object_or_404(Subject, id=subject_id, level=level)
                    my_subject.subject.add(subject)
                
                messages.success(request, 'Your teaching information has been saved! Please complete your profile by adding your phone number and TSC number to start getting swap opportunities.')
                return redirect('users:profile_edit')
                
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
    
    # GET request or form with errors
    levels = Level.objects.all().order_by('name')
    
    # Get the user's current level and subjects if they exist
    current_level = profile.level if hasattr(profile, 'level') and profile.level else None
    current_subjects = []
    
    # Get all subjects from all MySubject entries for the user
    my_subjects = MySubject.objects.filter(user=request.user)
    for my_subject in my_subjects:
        current_subjects.extend(list(my_subject.subject.values_list('id', flat=True)))
    
    # Remove duplicates while preserving order
    seen = set()
    current_subjects = [x for x in current_subjects if not (x in seen or seen.add(x))]
    
    # Get subjects for the current level or all subjects if no level selected
    if current_level:
        subjects = Subject.objects.filter(level=current_level).order_by('name')
    else:
        subjects = Subject.objects.none()
    
    context = {
        'levels': levels,
        'subjects': subjects,
        'current_level': current_level.id if current_level else None,
        'current_subjects': current_subjects,
        'has_level': has_level  # Use the has_level flag we set earlier
    }
    
    return render(request, 'users/teaching_info.html', context)

@login_required
def get_subjects_for_level(request, level_id):
    level = get_object_or_404(Level, id=level_id)
    # Get subjects for the level and format the response
    subjects = list(Subject.objects.filter(level=level).values('id', 'name'))
    return JsonResponse({'subjects': subjects})

def calculate_profile_completion(user, profile):
    """
    Calculate the profile completion percentage for a user.
    Returns a dictionary with completion percentage and status of each section.
    """
    completion_score = 0
    
    # 1. Check if personal profile is set up (25%)
    has_personal_profile = bool(profile and all([
        profile.phone,
        user.id_number,
        user.tsc_number,
        profile.first_name,
        profile.last_name,
        profile.gender
    ]))
    
    # 2. Check if school info is set up (25%)
    has_school_info = bool(profile and all([
        profile.school,
        profile.level,
    ]))
    
    # 3. Check if MySubjects are set up (25%)
    has_subjects = user.mysubject_set.exists()
    
    # 4. Check if swap preferences are set up (25%)
    has_swap_prefs = hasattr(user, 'swappreference') and all([
        user.swappreference.desired_county,
        user.swappreference.desired_constituency,
        user.swappreference.desired_ward
    ])
    
    # Calculate completion percentage (25% for each completed section)
    completion_score = sum([
        25 if has_personal_profile else 0,
        25 if has_school_info else 0,
        25 if has_subjects else 0,
        25 if has_swap_prefs else 0
    ])
    
    return {
        'percentage': completion_score,
        'has_personal_profile': has_personal_profile,
        'has_school_info': has_school_info,
        'has_subjects': has_subjects,
        'has_swap_prefs': has_swap_prefs
    }

def get_profile_completion_data(user, profile):
    """
    Calculate the profile completion data for a user.
    Completion is based on:
    1. Basic info (first name and phone number) - 20%
    2. School link - 20%
    3. Level set in profile - 20%
    4. Swap preferences - 20%
    5. MySubject (if level is secondary/high school) - 20%
    """
    # Initialize all checks as False
    has_basic_info = False
    has_school_link = False
    has_level = False
    has_swap_prefs = False
    has_subjects = False
    
    # 1. Check basic info (20%)
    if profile:
        has_basic_info = all([
            profile.phone and str(profile.phone).strip(),
            profile.first_name and str(profile.first_name).strip(),
        ])
    
    # 2. Check if user is linked to a school (20%)
    if profile and hasattr(profile, 'school'):
        has_school_link = profile.school is not None
    
    # 3. Check if level is set in profile (20%)
    if profile and hasattr(profile, 'level'):
        has_level = profile.level is not None
        
        # 4. Check if MySubject is set (only for secondary/high school) - 20%
        if has_level and profile.level.name.lower() in ['secondary', 'high school']:
            has_subjects = user.mysubject_set.exists()
        else:
            # If not secondary/high school, consider this section complete
            has_subjects = True
    
    # 5. Check swap preferences (20%)
    if hasattr(user, 'swappreference') and user.swappreference:
        swap_pref = user.swappreference
        has_swap_prefs = all([
            bool(swap_pref.desired_county),
        
        ])
    
    # Calculate completion percentage (20% for each completed section)
    completion_score = sum([
        20 if has_basic_info else 0,
        20 if has_school_link else 0,
        20 if has_level else 0,
        20 if has_swap_prefs else 0,
        20 if has_subjects else 0
    ])
    
    return {
        'percentage': completion_score,
        'has_basic_info': has_basic_info,
        'has_school_link': has_school_link,
        'has_level': has_level,
        'has_swap_prefs': has_swap_prefs,
        'has_subjects': has_subjects,
        'subject_required': has_level and profile and hasattr(profile, 'level') and 
                           profile.level.name.lower() in ['secondary', 'high school']
    }

@login_required
def admin_users_view(request):
    if not request.user.is_staff:
        return redirect('home:home')
    
    User = get_user_model()
    users = User.objects.select_related('profile', 'swappreference').prefetch_related('mysubject_set').order_by('-date_joined')
    
    # Get all user profiles in one query
    from users.models import PersonalProfile
    user_profiles = {profile.user_id: profile for profile in PersonalProfile.objects.select_related('school', 'level')}
    
    # Calculate profile completion for each user
    user_data = []
    for user in users:
        profile = user_profiles.get(user.id)
        
        # Use our helper function to get completion data
        completion = get_profile_completion_data(user, profile)
        
        # Generate WhatsApp message
        whatsapp_message = get_whatsapp_message(user, completion)
        # URL encode the message for WhatsApp
        import urllib.parse
        encoded_message = urllib.parse.quote(whatsapp_message)
        
        # Get phone number from profile if available
        phone_number = profile.phone if profile and hasattr(profile, 'phone') and profile.phone else ''
        # Normalize phone number to use Kenya country code 254
        if phone_number:
            # Import normalize function
            from chat.whatsapp_integration import normalize_phone_number
            # Normalize: if starts with 0, replace with 254
            normalized_phone = normalize_phone_number(phone_number)
            # Store normalized phone for display
            phone_number = normalized_phone
        
        # Get user's subscription status
        has_active_subscription = hasattr(user, 'subscription') and user.subscription.is_active
        
        user_data.append({
            'user': user,
            'profile': profile,
            'completion_percentage': completion['percentage'],
            'completion_data': completion,  # Include detailed completion data
            'has_active_subscription': has_active_subscription,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
            'subscription': getattr(user, 'subscription', None),
            'phone_number': phone_number,  # Store normalized phone number
            'whatsapp_url': f'https://wa.me/{phone_number}?text={encoded_message}' if phone_number else None,
            'has_phone': bool(phone_number)
        })
    
    # Calculate statistics
    total_users = len(user_data)
    active_users = sum(1 for u in user_data if u['is_active'])
    staff_users = sum(1 for u in user_data if u['is_staff'])
    active_subscriptions = sum(1 for u in user_data if u['has_active_subscription'])
    avg_completion = sum(u['completion_percentage'] for u in user_data) / total_users if total_users > 0 else 0
    
    context = {
        'users': user_data,
        'total_users': total_users,
        'active_users': active_users,
        'staff_users': staff_users,
        'active_subscriptions': active_subscriptions,
        'avg_completion': round(avg_completion, 1),  # Round to 1 decimal place
        'now': timezone.now(),
        'page_title': 'User Management',
        'active_tab': 'users'
    }
    
    return render(request, 'users/admin_users.html', context)

    


@login_required
def admin_edit_user_view(request, user_id):
    if not request.user.is_staff:
        return redirect('home:home')
    
    user = get_object_or_404(MyUser, id=user_id)
    profile, created = PersonalProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        # Get the name fields directly from the request
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        surname = request.POST.get('surname', '').strip()
        
        # Validate required fields
        if not first_name or not last_name:
            messages.error(request, "First name and last name are required.")
        else:
            try:
                with transaction.atomic():
                    # Update only the name fields
                    profile.first_name = first_name
                    profile.last_name = last_name
                    profile.surname = surname
                    profile.save()
                    
                    messages.success(request, 'User information updated successfully.')
                    return redirect('users:admin_users')
                    
            except Exception as e:
                messages.error(request, f'An error occurred while updating the user: {str(e)}')
    
    # For GET requests or if there was an error, show the form
    context = {
        'user_being_edited': user,
        'profile': profile,
    }
    return render(request, 'users/admin_edit_user.html', context)


@require_GET
@login_required
def get_subjects_for_level(request, level_id):
    """
    AJAX view to get subjects for a specific level
    """
    try:
        # Get teacher_id from query params
        teacher_id = request.GET.get('teacher_id')
        
        # Validate level_id
        if level_id == 0 or level_id == '0':
            subjects = Subject.objects.none()
        else:
            try:
                level = get_object_or_404(Level, id=level_id)
                subjects = Subject.objects.filter(level=level).order_by('name')
            except (ValueError, Level.DoesNotExist):
                return JsonResponse(
                    {'error': 'Invalid level ID'}, 
                    status=400
                )
        
        # Get current subject IDs if teacher_id is provided
        current_subjects = []
        if teacher_id:
            try:
                teacher = MyUser.objects.get(id=teacher_id, role='Teacher')
                my_subject = MySubject.objects.filter(user=teacher).first()
                if my_subject:
                    current_subjects = list(my_subject.subject.values_list('id', flat=True))
            except (MyUser.DoesNotExist, ValueError):
                # If teacher doesn't exist or invalid ID, just continue with empty current_subjects
                pass
        
        # Prepare context for the template
        context = {
            'subjects': subjects,
            'current_subjects': current_subjects,
        }
        
        # Render the subjects partial
        html = render_to_string('users/partials/subject_checkboxes.html', context, request=request)
        
        return JsonResponse({'html': html})
        
    except Exception as e:
        import traceback
        print(f"Error in get_subjects_for_level: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse(
            {'error': 'An error occurred while loading subjects'}, 
            status=500
        )


@login_required
def manage_teacher_subjects(request, user_id):
    """
    View for admin to manage a teacher's subjects and swap preferences.
    """
    # Check if user is staff
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home:home')
    
    try:
        teacher = get_object_or_404(MyUser, id=user_id, role='Teacher')
        
        # Get or create MySubject and SwapPreference for the teacher
        my_subject, created = MySubject.objects.get_or_create(user=teacher)
        swap_pref, created = SwapPreference.objects.get_or_create(user=teacher)
        
        # Get the teacher's current level, subjects, and swap preferences
        current_level = teacher.profile.level if hasattr(teacher, 'profile') and teacher.profile else None
        current_subjects = list(my_subject.subject.all())
        
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # Get selected level and subjects
                    level_id = request.POST.get('level')
                    subject_ids = request.POST.getlist('subjects')
                    
                    # Update teacher's level if changed
                    if level_id and level_id != 'None':
                        level = Level.objects.get(id=level_id)
                        if hasattr(teacher, 'profile'):
                            teacher.profile.level = level
                            teacher.profile.save()
                    
                    # Update teacher's subjects
                    if subject_ids:
                        new_subjects = Subject.objects.filter(id__in=subject_ids)
                        my_subject.subject.set(new_subjects)
                    else:
                        my_subject.subject.clear()
                    
                    # Update school if provided
                    school_id = request.POST.get('school')
                    if hasattr(teacher, 'profile'):
                        if school_id:
                            school = Schools.objects.get(id=school_id)
                            teacher.profile.school = school
                            teacher.profile.save()
                        else:
                            teacher.profile.school = None
                            teacher.profile.save()
                    
                    # Update swap preferences
                    swap_pref.desired_county_id = request.POST.get('desired_county') or None
                    swap_pref.desired_constituency_id = request.POST.get('desired_constituency') or None
                    swap_pref.desired_ward_id = request.POST.get('desired_ward') or None
                    swap_pref.is_hardship = request.POST.get('is_hardship', 'Any')
                    
                    # Update open_to_all counties
                    open_to_all_counties = request.POST.getlist('open_to_all')
                    swap_pref.open_to_all.set(open_to_all_counties)
                    
                    swap_pref.save()
                    
                    messages.success(request, 'Teacher information updated successfully.')
                    return redirect('users:admin_users')
                    
            except Exception as e:
                messages.error(request, f'Error updating teacher information: {str(e)}')
        
        # Get all levels and subjects for the dropdowns
        levels = Level.objects.all().order_by('name')
        subjects = Subject.objects.all()
        if current_level:
            subjects = subjects.filter(level=current_level)
        
        # Get location data for the form
        counties = Counties.objects.all().order_by('name')
        constituencies = Constituencies.objects.all().order_by('name')
        wards = Wards.objects.all().order_by('name')
        
        # Get the current school if it exists
        current_school = teacher.profile.school if hasattr(teacher, 'profile') and teacher.profile else None
        
        # Get schools for the current ward if available
        schools = Schools.objects.all().order_by('name')
        if current_school and current_school.ward:
            schools = schools.filter(ward=current_school.ward)
        
        # Get the IDs of currently selected open_to_all counties
        open_to_all_county_ids = list(swap_pref.open_to_all.values_list('id', flat=True))
        
        context = {
            'teacher': teacher,
            'levels': levels,
            'subjects': subjects.order_by('name'),
            'current_level': current_level,
            'current_subjects': [s.id for s in current_subjects],
            'swap_pref': swap_pref,
            'counties': counties,
            'constituencies': constituencies,
            'wards': wards,
            'schools': schools,
            'current_school': current_school,
            'open_to_all_county_ids': open_to_all_county_ids,
        }
        return render(request, 'users/manage_teacher_subjects.html', context)
        
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('users:admin_users')


@login_required
@staff_required(login_url='users:login')
def primary_matched_swaps(request):
    """
    View to find perfect location swap matches between primary school teachers.
    Matches are based on:
    - Teacher A's current county matches Teacher B's desired county
    - Teacher B's current county matches Teacher A's desired county
    """
    # Debug logging
    print(f"[DEBUG] primary_matched_swaps - User: {request.user}, is_authenticated: {request.user.is_authenticated}, is_staff: {request.user.is_staff}")
    
    # Check if user is staff (double check)
    if not request.user.is_staff:
        print("[DEBUG] User is not staff, will redirect to login")
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path(), login_url='users:login')
    
    print("[DEBUG] User is staff, proceeding with view")
        
    # Get all active teachers with their profiles and swap preferences
    print("[DEBUG] Fetching teachers with profiles, schools, and swap preferences")
    teachers = MyUser.objects.filter(
        is_active=True,
        role='Teacher',
        profile__isnull=False,
        profile__school__isnull=False,
        swappreference__isnull=False  # Only teachers with swap preferences
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county',  # Direct county reference
        'profile__school__level'
    ).prefetch_related(
        'swappreference__open_to_all'
    )
    
    print(f"[DEBUG] Found {teachers.count()} teachers with profiles, schools, and swap preferences")
    
    # Debug: Print first few teachers' school levels
    for i, t in enumerate(teachers[:3]):  # Print first 3 for debugging
        if hasattr(t, 'profile') and hasattr(t.profile, 'school') and t.profile.school:
            level = getattr(t.profile.school, 'level', None)
            print(f"[DEBUG] Teacher {i+1} school level: {level}")
        else:
            print(f"[DEBUG] Teacher {i+1} missing profile or school")
    
    # Get the primary school level object
    try:
        primary_level = Level.objects.get(name__iexact='Primary School')
    except Level.DoesNotExist:
        messages.error(request, "Primary School level not found in the system. Please add it first.")
        return redirect('users:admin_users')
    
    # Filter for primary school teachers
    primary_teachers = []
    for t in teachers:
        try:
            if (hasattr(t, 'profile') and 
                hasattr(t.profile, 'school') and 
                t.profile.school and 
                hasattr(t.profile.school, 'level') and 
                t.profile.school.level and 
                t.profile.school.level.id == primary_level.id):
                primary_teachers.append(t)
        except Exception as e:
            print(f"[DEBUG] Error processing teacher {t.id}: {str(e)}")
    
    print(f"[DEBUG] Found {len(primary_teachers)} primary school teachers with swap preferences")
    
    if not primary_teachers:
        msg = "No primary school teachers with swap preferences found."
        print(f"[DEBUG] {msg}")
        messages.warning(request, msg)
        return render(request, 'users/primary_matched_swaps.html', {
            'matched_pairs': [],
            'total_matches': 0,
            'error_message': msg
        })

    matched_pairs = []
    processed_pairs = set()  # To avoid duplicate matches

    # Convert to list to avoid multiple database queries
    teachers_list = list(teachers)

    # Create a dictionary to store teachers by their current county
    teachers_by_county = {}
    for teacher in teachers_list:
        if not hasattr(teacher, 'profile') or not teacher.profile.school:
            continue
            
        county = teacher.profile.school.ward.constituency.county
        if county:
            teachers_by_county.setdefault(county.id, []).append(teacher)

    # Find matches
    for teacher in teachers_list:
        if not hasattr(teacher, 'profile') or not teacher.profile.school:
            continue
            
        current_county = teacher.profile.school.ward.constituency.county
        swap_pref = getattr(teacher, 'swappreference', None)
        
        if not swap_pref or not swap_pref.desired_ward:
            continue
            
        desired_county = swap_pref.desired_ward.constituency.county
        
        # Find teachers in the desired county who want to come to this teacher's current county
        potential_matches = teachers_by_county.get(desired_county.id, []) if desired_county else []
        
        for match in potential_matches:
            if match == teacher or match.id in processed_pairs:
                continue

@login_required
@staff_required(login_url='users:login')
def primary_triangle_swaps(request):
    """
    View to find triangle swaps for PRIMARY level teachers.
    Triangle swap: Three teachers exchange locations in a circular pattern.
    Only checks location matching (no subject requirement for primary).
    """
    from home.triangle_swap_utils import find_triangle_swaps_primary, get_current_county
    from home.models import Level
    
    # Get the primary school level object
    try:
        primary_level = Level.objects.get(name__iexact='Primary School')
    except Level.DoesNotExist:
        messages.error(request, "Primary School level not found in the system. Please add it first.")
        return redirect('users:admin_users')
    
    # Get all active primary school teachers with profiles, schools, and swap preferences
    teachers = MyUser.objects.filter(
        is_active=True,
        role='Teacher',
        profile__isnull=False,
        profile__school__isnull=False,
        profile__school__level=primary_level,
        swappreference__isnull=False
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county',
        'profile__school__level'
    ).prefetch_related(
        'swappreference__open_to_all'
    ).distinct()
    
    print(f"[DEBUG] Found {teachers.count()} primary teachers for triangle swap detection")
    
    # Find triangle swaps
    triangle_swaps = find_triangle_swaps_primary(teachers)
    
    # Format triangle swaps for display
    formatted_triangles = []
    for teacher_a, teacher_b, teacher_c in triangle_swaps:
        county_a = get_current_county(teacher_a)
        county_b = get_current_county(teacher_b)
        county_c = get_current_county(teacher_c)
        
        formatted_triangles.append({
            'teacher_a': {
                'user': teacher_a,
                'current_location': county_a.name if county_a else 'Unknown',
                'wants_location': county_b.name if county_b else 'Unknown',
            },
            'teacher_b': {
                'user': teacher_b,
                'current_location': county_b.name if county_b else 'Unknown',
                'wants_location': county_c.name if county_c else 'Unknown',
            },
            'teacher_c': {
                'user': teacher_c,
                'current_location': county_c.name if county_c else 'Unknown',
                'wants_location': county_a.name if county_a else 'Unknown',
            },
        })
    
    return render(request, 'users/primary_triangle_swaps.html', {
        'triangle_swaps': formatted_triangles,
        'total_triangles': len(formatted_triangles),
    })

@login_required
@staff_required(login_url='users:login')
def secondary_triangle_swaps(request):
    """
    View to find triangle swaps for SECONDARY level teachers.
    Triangle swap: Three teachers exchange locations in a circular pattern.
    Requires BOTH location AND subject matching (all three must share at least one subject).
    """
    from home.triangle_swap_utils import find_triangle_swaps_secondary, get_current_county, get_user_subjects
    from home.models import Level
    
    # Get the secondary/high school level object
    try:
        secondary_level = Level.objects.get(name__iexact='Secondary/High School')
    except Level.DoesNotExist:
        messages.error(request, "Secondary/High School level not found in the system. Please add it first.")
        return redirect('users:admin_users')
    
    # Get all active secondary school teachers with profiles, schools, swap preferences, and subjects
    teachers = MyUser.objects.filter(
        is_active=True,
        role='Teacher',
        profile__isnull=False,
        profile__school__isnull=False,
        profile__school__level=secondary_level,
        swappreference__isnull=False
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county',
        'profile__school__level'
    ).prefetch_related(
        'swappreference__open_to_all',
        'mysubject_set__subject'
    ).distinct()
    
    print(f"[DEBUG] Found {teachers.count()} secondary teachers for triangle swap detection")
    
    # Find triangle swaps
    triangle_swaps = find_triangle_swaps_secondary(teachers)
    
    # Format triangle swaps for display
    formatted_triangles = []
    for teacher_a, teacher_b, teacher_c in triangle_swaps:
        county_a = get_current_county(teacher_a)
        county_b = get_current_county(teacher_b)
        county_c = get_current_county(teacher_c)
        
        # Get common subjects for display
        subjects_a = get_user_subjects(teacher_a)
        subjects_b = get_user_subjects(teacher_b)
        subjects_c = get_user_subjects(teacher_c)
        common_subjects = subjects_a.intersection(subjects_b).intersection(subjects_c)
        
        formatted_triangles.append({
            'teacher_a': {
                'user': teacher_a,
                'current_location': county_a.name if county_a else 'Unknown',
                'wants_location': county_b.name if county_b else 'Unknown',
            },
            'teacher_b': {
                'user': teacher_b,
                'current_location': county_b.name if county_b else 'Unknown',
                'wants_location': county_c.name if county_c else 'Unknown',
            },
            'teacher_c': {
                'user': teacher_c,
                'current_location': county_c.name if county_c else 'Unknown',
                'wants_location': county_a.name if county_a else 'Unknown',
            },
            'common_subjects': common_subjects,
        })
    
    return render(request, 'users/secondary_triangle_swaps.html', {
        'triangle_swaps': formatted_triangles,
        'total_triangles': len(formatted_triangles),
    })

@staff_required(login_url='users:login')
def high_school_matched_swaps(request):
    """
    View to find perfect location and subject swap matches between high school teachers.
    Matches are based on:
    - Teacher A's current county matches Teacher B's desired county
    - Teacher B's current county matches Teacher A's desired county
    - Both teachers teach at least one common subject
    """
    print(f"[DEBUG] high_school_matched_swaps - User: {request.user}")
    
    # Get the high school level object
    try:
        high_school_level = Level.objects.get(name__iexact='Secondary/High School')
    except Level.DoesNotExist:
        messages.error(request, "Secondary/High School level not found in the system. Please add it first.")
        return redirect('users:admin_users')

    # Get all active high school teachers with their profiles, schools, and subjects
    teachers = MyUser.objects.filter(
        is_active=True,
        role='Teacher',
        profile__isnull=False,
        profile__school__isnull=False,
        profile__school__level=high_school_level,
        swappreference__isnull=False
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county'  # Only need county-level preference
    ).prefetch_related(
        'swappreference__open_to_all',
        'mysubject_set__subject'
    ).distinct()

    matched_pairs = []
    processed_pairs = set()
    teachers_list = list(teachers)
    
    print(f"[DEBUG] Found {len(teachers_list)} high school teachers with swap preferences")

    # Create a dictionary to store teachers by their current county
    teachers_by_county = {}
    for teacher in teachers_list:
        if not hasattr(teacher, 'profile') or not teacher.profile.school:
            continue
            
        county = teacher.profile.school.ward.constituency.county
        if county:
            teachers_by_county.setdefault(county.id, []).append(teacher)

    # Find matches
    print(f"[DEBUG] Starting to find matches among {len(teachers_list)} teachers")
    
    for teacher in teachers_list:
        if not hasattr(teacher, 'profile') or not teacher.profile.school:
            print(f"[DEBUG] Skipping teacher {teacher.id} - missing profile or school")
            continue
            
        current_county = teacher.profile.school.ward.constituency.county
        if not current_county:
            print(f"[DEBUG] Skipping teacher {teacher.id} - school has no county")
            continue
            
        swap_pref = getattr(teacher, 'swappreference', None)
        if not swap_pref:
            print(f"[DEBUG] Skipping teacher {teacher.id} - no swap preferences")
            continue
        
        # Get teacher's desired counties (from direct county preference and open_to_all)
        desired_counties = set()
        
        # 1. Check direct county preference
        if swap_pref.desired_county:
            print(f"[DEBUG] Teacher {teacher.id} has direct county preference: {swap_pref.desired_county.name}")
            desired_counties.add(swap_pref.desired_county.id)
        
        # 2. Add open_to_all counties if any
        if hasattr(swap_pref, 'open_to_all'):
            open_to_all = list(swap_pref.open_to_all.values_list('name', flat=True))
            print(f"[DEBUG] Teacher {teacher.id} open to these counties: {open_to_all}")
            desired_counties.update(swap_pref.open_to_all.values_list('id', flat=True))
        
        if not desired_counties:
            print(f"[DEBUG] Skipping teacher {teacher.id} - no desired counties specified")
            continue  # Skip if no desired counties specified
        
        # Find teachers in the desired county who want to come to this teacher's current county
        for desired_county_id in desired_counties:
            potential_matches = teachers_by_county.get(desired_county_id, [])
            
            for match in potential_matches:
                if match == teacher or match.id in processed_pairs:
                    continue
                    
                match_pref = getattr(match, 'swappreference', None)
                if not match_pref or not match_pref.desired_county:
                    continue
                    
                # Check if the match wants to come to this teacher's current county
                match_wants_current_county = (
                    # Direct county match
                    (match_pref.desired_county and match_pref.desired_county == current_county) or
                    # Or in open_to_all counties
                    (hasattr(match_pref, 'open_to_all') and match_pref.open_to_all.filter(id=current_county.id).exists())
                )
                
                if not match_wants_current_county:
                    continue
                    
                # Get teacher's subjects
                teacher_subjects = set()
                for my_subject in teacher.mysubject_set.all():
                    teacher_subjects.update(s.id for s in my_subject.subject.all())
                
                if not teacher_subjects:
                    continue  # Skip teachers with no subjects
                
                # Get match's subjects
                match_subjects = set()
                for my_subject in match.mysubject_set.all():
                    match_subjects.update(s.id for s in my_subject.subject.all())
                
                # Check for subject overlap
                common_subjects = teacher_subjects.intersection(match_subjects)
                if not common_subjects:
                    continue  # Skip if no common subjects
                
                # Create a unique pair ID to avoid duplicates (smaller ID first)
                pair_id = tuple(sorted([teacher.id, match.id]))
                if pair_id in processed_pairs:
                    continue
                    
                processed_pairs.add(pair_id)
                
                # Get common subject names
                common_subject_names = Subject.objects.filter(
                    id__in=common_subjects
                ).values_list('name', flat=True)
                
                # Found a perfect match!
                print(f"[DEBUG] Found match between {teacher.id} and {match.id}")
                print(f"[DEBUG] Common subjects: {list(common_subject_names)}")
                
                matched_pairs.append({
                    'teacher_a': teacher,
                    'teacher_b': match,
                    'match_score': 100,  # Perfect match
                    'current_county_a': current_county.name,
                    'desired_county_a': desired_county.name,
                    'current_county_b': match.profile.school.ward.constituency.county.name if hasattr(match, 'profile') and hasattr(match.profile, 'school') else 'Unknown',
                    'desired_county_b': current_county.name,  # They're swapping
                    'teacher_a_school': teacher.profile.school.name,
                    'teacher_b_school': match.profile.school.name,
                    'common_subjects': list(common_subject_names)
                })

    return render(request, 'users/high_school_matched_swaps.html', {
        'matched_pairs': matched_pairs,
        'total_matches': len(matched_pairs)
    })


@login_required
@login_required
def find_secondary_matches(request):
    """
    View to display all secondary level teacher matches for the current user.
    """
    # Get the user's profile and verify they are a secondary teacher
    if not hasattr(request.user, 'profile') or not request.user.profile.school:
        messages.error(request, "Please complete your profile to find matches.")
        return redirect('users:profile_completion')
    
    # Check if user is a secondary teacher
    is_secondary = request.user.profile.school and hasattr(request.user.profile.school, 'level') and \
                  ('secondary' in request.user.profile.school.level.name.lower() or 
                   'high' in request.user.profile.school.level.name.lower())
    
    if not is_secondary:
        messages.error(request, "This page is only available for secondary school teachers.")
        return redirect('users:dashboard')
    
    # Get matches using the existing template tag function
    perfect_matches, partial_matches = get_secondary_teacher_matches(request.user)
    
    return render(request, 'users/secondary_matches.html', {
        'perfect_matches': perfect_matches,
        'partial_matches': partial_matches,
        'is_secondary': True
    })


@login_required
def initiate_swap(request, user_id):
    """
    Initiate a swap request with another user.
    """
    # Get the target user using the custom user model
    target_user = get_object_or_404(MyUser, id=user_id)
    
    # Prevent users from swapping with themselves
    if target_user == request.user:
        messages.error(request, "You cannot initiate a swap with yourself.")
        return redirect('users:dashboard')
    
    # Check if the target user has a profile and school
    if not hasattr(target_user, 'profile') or not target_user.profile.school:
        messages.error(request, "The selected user does not have a complete profile.")
        return redirect('users:dashboard')
    
    # Check if a swap request already exists between these users in either direction
    # Check for exact match first (requester -> target)
    existing_exact = SwapRequests.objects.filter(
        requester=request.user,
        target=target_user
    ).first()
    
    # Check for reverse match (target -> requester)
    existing_reverse = SwapRequests.objects.filter(
        requester=target_user,
        target=request.user
    ).first()
    
    if existing_exact:
        if existing_exact.is_active:
            messages.info(request, f"You already have a pending swap request with {target_user.get_full_name() or target_user.email}.")
        else:
            # Reactivate the existing request
            existing_exact.is_active = True
            existing_exact.accepted = False
            existing_exact.save()
            messages.info(request, f"Swap request reactivated with {target_user.get_full_name() or target_user.email}.")
        return redirect('users:dashboard')
    
    if existing_reverse:
        if existing_reverse.is_active:
            # Check if this is a mutual swap - if so, auto-accept the existing request
            is_mutual = False
            if hasattr(request.user, 'profile') and request.user.profile.school and hasattr(request.user, 'swappreference') and \
               hasattr(target_user, 'profile') and target_user.profile.school and hasattr(target_user, 'swappreference'):
                from home.triangle_swap_utils import get_current_county, wants_county
                
                requester_county = get_current_county(request.user)
                target_county = get_current_county(target_user)
                
                if requester_county and target_county:
                    requester_wants_target = wants_county(request.user, target_county)
                    target_wants_requester = wants_county(target_user, requester_county)
                    is_mutual = requester_wants_target and target_wants_requester
            
            if is_mutual and not existing_reverse.accepted:
                # Auto-accept the existing reverse request since it's mutual
                existing_reverse.accepted = True
                existing_reverse.save()
                messages.success(request, f"🎉 Mutual swap detected! You and {target_user.get_full_name() or target_user.email} both want each other's locations. Swap automatically accepted!")
            else:
                messages.info(request, f"{target_user.get_full_name() or target_user.email} has already sent you a swap request. Please check your received requests.")
        else:
            # Reactivate the reverse request
            existing_reverse.is_active = True
            existing_reverse.accepted = False
            existing_reverse.save()
            messages.info(request, f"Swap request from {target_user.get_full_name() or target_user.email} has been reactivated.")
        return redirect('users:dashboard')
    
    # Check for mutual/2-way swap interest
    is_mutual_swap = False
    if hasattr(request.user, 'profile') and request.user.profile.school and hasattr(request.user, 'swappreference') and \
       hasattr(target_user, 'profile') and target_user.profile.school and hasattr(target_user, 'swappreference'):
        from home.triangle_swap_utils import get_current_county, wants_county
        
        # Get current counties
        requester_county = get_current_county(request.user)
        target_county = get_current_county(target_user)
        
        if requester_county and target_county:
            # Check if requester wants target's location AND target wants requester's location
            requester_wants_target = wants_county(request.user, target_county)
            target_wants_requester = wants_county(target_user, requester_county)
            
            is_mutual_swap = requester_wants_target and target_wants_requester
    
    try:
        with transaction.atomic():
            # Create a swap request
            swap_request = SwapRequests.objects.create(
                requester=request.user,
                target=target_user,
                is_active=True,
                accepted=is_mutual_swap  # Auto-accept if mutual
            )
            
            if is_mutual_swap:
                messages.success(request, f"🎉 Mutual swap detected! Swap request automatically accepted with {target_user.get_full_name() or target_user.email}.")
            else:
                messages.success(request, f"Swap request sent to {target_user.get_full_name() or target_user.email} successfully!")
            
    except Exception as e:
        messages.error(request, f"An error occurred while initiating the swap: {str(e)}")
        if settings.DEBUG:
            raise e
    
    return redirect('users:dashboard')


def admin_delete_user_view(request, user_id):
    """
    View to delete a user account (admin only).
    """
    if not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    user_to_delete = get_object_or_404(MyUser, id=user_id)
    
    # Prevent deleting superusers or staff members
    if user_to_delete.is_superuser or user_to_delete.is_staff:
        messages.error(request, 'Cannot delete admin or staff accounts.')
        return redirect('users:admin_users')
    
    if request.method == 'POST':
        # Soft delete the user
        user_to_delete.is_active = False
        user_to_delete.save()
        
        # Log the action
        messages.success(request, f'User {user_to_delete.email} has been deactivated.')
        return redirect('users:admin_users')
    
    context = {
        'user_to_delete': user_to_delete,
    }
    return render(request, 'users/admin/confirm_delete_user.html', context)

@login_required
def accept_swap_request(request, request_id):
    """
    View to accept a swap request.
    Also checks if this is a mutual/2-way swap.
    """
    swap_request = get_object_or_404(SwapRequests, id=request_id, target=request.user, is_active=True, accepted=False)
    
    # Check if this is a mutual/2-way swap
    is_mutual_swap = False
    if hasattr(swap_request.requester, 'profile') and swap_request.requester.profile.school and hasattr(swap_request.requester, 'swappreference') and \
       hasattr(swap_request.target, 'profile') and swap_request.target.profile.school and hasattr(swap_request.target, 'swappreference'):
        from home.triangle_swap_utils import get_current_county, wants_county
        
        # Get current counties
        requester_county = get_current_county(swap_request.requester)
        target_county = get_current_county(swap_request.target)
        
        if requester_county and target_county:
            # Check if requester wants target's location AND target wants requester's location
            requester_wants_target = wants_county(swap_request.requester, target_county)
            target_wants_requester = wants_county(swap_request.target, requester_county)
            
            is_mutual_swap = requester_wants_target and target_wants_requester
    
    with transaction.atomic():
        # Mark the request as accepted
        swap_request.accepted = True
        swap_request.is_active = True  # Keep it active
        swap_request.save()
        
        # Deactivate all other pending requests between these users
        SwapRequests.objects.filter(
            Q(requester=swap_request.requester, target=swap_request.target) |
            Q(requester=swap_request.target, target=swap_request.requester),
            is_active=True,
            accepted=False
        ).exclude(id=request_id).update(is_active=False)
        
        # Send notification
        if is_mutual_swap:
            messages.success(request, f'🎉 Mutual swap confirmed! You and {swap_request.requester.get_full_name() or swap_request.requester.email} both want each other\'s locations.')
        else:
            messages.success(request, f'You have accepted the swap request from {swap_request.requester.get_full_name() or swap_request.requester.email}.')
    
    return redirect('users:dashboard')

@login_required
def reject_swap_request(request, request_id):
    """
    View to reject a swap request.
    """
    swap_request = get_object_or_404(SwapRequests, id=request_id, target=request.user, is_active=True, accepted=False)
    
    with transaction.atomic():
        # Mark the request as inactive
        swap_request.is_active = False
        swap_request.save()
        
        messages.info(request, f'You have rejected the swap request from {swap_request.requester.get_full_name() or swap_request.requester.email}.')
    
    return redirect('users:dashboard')

@login_required
def cancel_swap_request(request, request_id):
    """
    View to cancel a swap request sent by the current user.
    """
    swap_request = get_object_or_404(SwapRequests, id=request_id, requester=request.user, is_active=True, accepted=False)
    
    with transaction.atomic():
        # Mark the request as inactive
        swap_request.is_active = False
        swap_request.save()
        
        messages.info(request, f'You have cancelled the swap request to {swap_request.target.get_full_name() or swap_request.target.email}.')
    
    return redirect('users:dashboard')

@login_required
def swap_requests(request):
    """
    View to show all swap requests (sent and received).
    """
    # Get all active swap requests sent by the user
    sent_requests = SwapRequests.objects.filter(
        requester=request.user, 
        is_active=True
    ).select_related(
        'target__profile'
    ).order_by('-created_at')
    
    # Get all active swap requests received by the user
    received_requests = SwapRequests.objects.filter(
        target=request.user, 
        is_active=True
    ).select_related(
        'requester__profile'
    ).order_by('-created_at')
    
    context = {
        'sent_requests': sent_requests,
        'received_requests': received_requests,
    }
    
    return render(request, 'users/swap_requests.html', context)