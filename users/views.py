from django.contrib import messages
from django.contrib.auth import (authenticate, get_user_model, login, logout,
                                 update_session_auth_hash)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from home.models import (Level, MySubject, Subject, SwapPreference,
                         SwapRequests, Swaps)
from home.utils import verify_kra_details

from .forms import (CustomPasswordChangeForm, MyAuthenticationForm,
                    MyUserCreationForm, ProfileEditForm)
from .models import PersonalProfile

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
def profile_view(request):
    # Get or create the user's profile
    profile, created = PersonalProfile.objects.get_or_create(user=request.user)
    
    # Get user's school and subjects
    school = profile.school
    my_subjects = MySubject.objects.filter(user=request.user).first()
    subjects = my_subjects.subject.all() if my_subjects else []
    
    context = {
        'profile': profile,
        'school': school,
        'subjects': subjects
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
            instance=request.user,
            initial={'phone': profile.phone, 'gender': profile.gender}
        )
        
        if form.is_valid():
            user = form.save(commit=False)
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
            # Handle profile picture clear
            elif form.cleaned_data.get('profile_picture-clear'):
                profile.profile_picture.delete(save=False)
            
            # Update profile fields
            profile.phone = form.cleaned_data.get('phone')
            profile.gender = form.cleaned_data.get('gender')
            
            # Save both user and profile
            user.save()
            profile.save()
            
            # Update session with new profile picture if it exists
            if hasattr(profile, 'profile_picture') and profile.profile_picture:
                request.session['profile_picture'] = profile.profile_picture.url
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile_edit')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileEditForm(
            instance=request.user,
            initial={
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

def dashboard(request):
    """User dashboard with overview of user's swaps and requests"""
    user = request.user
    
    # Get active swaps created by the user
    active_swaps_queryset = Swaps.objects.filter(user=user, status=True)
    active_swaps_count = active_swaps_queryset.count()
    
    # Get pending swap requests for the user's swaps
    pending_requests = SwapRequests.objects.filter(swap__user=user, accepted=False, is_active=True).count()
    
    # Check profile completion status
    has_profile = hasattr(user, 'profile') and user.profile is not None
    
    # Personal Information - Core fields only (name, phone, gender)
    # first_name and last_name are on the User model, phone and gender on Profile
    personal_info_complete = False
    if has_profile:
        personal_info_complete = all([
            user.first_name,  # On User model
            user.last_name,   # On User model
            user.profile.phone,
            user.profile.gender,
        ])
    
    # Teaching Information - Different requirements based on level
    teaching_info_complete = False
    is_secondary_level = False
    if has_profile and user.profile.level:
        user_level = user.profile.level
        
        # Check if user is Secondary/High School level
        if user_level.name == "Secondary/High School":
            is_secondary_level = True
            # Secondary teachers need: level, school, AND subjects
            teaching_info_complete = all([
                user.profile.level,
                user.profile.school,
                user.mysubject_set.exists()
            ])
        else:
            # Primary teachers only need: level and school (no subjects required)
            teaching_info_complete = all([
                user.profile.level,
                user.profile.school
            ])
    
    # Profile Picture
    profile_picture_complete = has_profile and bool(user.profile.profile_picture)
    
    # Swap Preferences
    swap_preference = None
    try:
        swap_preference = SwapPreference.objects.get(user=request.user)
    except SwapPreference.DoesNotExist:
        pass
    
    # Preferences complete if exists AND has at least county or is open_to_all
    preferences_complete = swap_preference is not None and (
        swap_preference.open_to_all or swap_preference.desired_county is not None
    )
    
    # Calculate completion percentage (4 sections, 25% each)
    completion_percentage = 0
    if personal_info_complete:
        completion_percentage += 25
    if teaching_info_complete:
        completion_percentage += 25
    if profile_picture_complete:
        completion_percentage += 25
    if preferences_complete:
        completion_percentage += 25
        
    # Overall profile complete if all sections are complete
    profile_complete = all([personal_info_complete, teaching_info_complete, profile_picture_complete, preferences_complete])
    
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
    
    context = {
        'user': user,
        'active_swaps': active_swaps_count,
        'active_swaps_queryset': active_swaps_queryset,
        'pending_requests': pending_requests,
        'profile_complete': profile_complete,
        'completion_percentage': int(completion_percentage),
        'personal_info_complete': personal_info_complete,
        'teaching_info_complete': teaching_info_complete,
        'profile_picture_complete': profile_picture_complete,
        'preferences_complete': preferences_complete,
        'is_secondary_level': is_secondary_level,
        'subscription': subscription_status,
        'swap_preference': swap_preference,
        'preferences_complete': preferences_complete,
    }
    
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

@login_required
def admin_users_view(request):
    if not request.user.is_staff:
        return redirect('home:home')
    
    User = get_user_model()
    users = User.objects.select_related('profile', 'swappreference').prefetch_related('mysubject_set').order_by('-date_joined')
    
    # Get all user profiles in one query
    from users.models import PersonalProfile
    user_profiles = {profile.user_id: profile for profile in PersonalProfile.objects.select_related('school', 'level')}
    
    # Calculate profile completion percentage for each user
    user_data = []
    for user in users:
        completion_score = 0
        total_checks = 4  # Total number of completion checks
        
        # 1. Check if personal profile is set up (25%)
        profile = user_profiles.get(user.id)
        has_personal_profile = bool(profile and all([
            profile.phone,
            user.id_number,
            # kra_pin might not exist in the model
            user.tsc_number,
            # bank details might not be in the profile
            profile.first_name,
            profile.last_name,
            profile.gender
        ]))
        if has_personal_profile:
            completion_score += 25
        
        # 2. Check if school info is set up (25%)
        has_school_info = bool(profile and all([
            profile.school,
            profile.level,
            # These fields might not exist in the profile model
            # Add any other school-related fields that should be checked
        ]))
        if has_school_info:
            completion_score += 25
        
        # 3. Check if MySubjects are set up (25%)
        has_subjects = user.mysubject_set.exists()
        if has_subjects:
            completion_score += 25
        
        # 4. Check if swap preferences are set up (25%)
        has_swap_prefs = hasattr(user, 'swappreference') and all([
            user.swappreference.desired_county,
            user.swappreference.desired_constituency,
            # preferred_school_type might not exist, check for other relevant fields
            user.swappreference.desired_ward
        ])
        if has_swap_prefs:
            completion_score += 25
        
        user_data.append({
            'user': user,
            'completion_percentage': completion_score,
            'has_active_subscription': hasattr(user, 'subscription') and user.subscription.is_active,
            'has_personal_profile': has_personal_profile,
            'has_school_info': has_school_info,
            'has_subjects': has_subjects,
            'has_swap_prefs': has_swap_prefs
        })
    
    context = {
        'users': user_data,
        'total_users': users.count(),
        'active_subscriptions': sum(1 for u in user_data if u['has_active_subscription']),
        'avg_completion': sum(u['completion_percentage'] for u in user_data) / len(user_data) if user_data else 0
    }
    
    return render(request, 'users/admin_users.html', context)