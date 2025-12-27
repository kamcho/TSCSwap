from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse

from .forms import (FastSwapForm, MySubjectForm, SchoolForm, SwapForm,
                    SwapPreferenceForm)
from .models import (Bookmark, Constituencies, Counties, FastSwap, Level, MySubject,
                     Schools, Subject, SwapPreference, SwapRequests, Swaps,
                     User, Wards)


def landing_page(request):
    """
    Landing page where teachers can discover and start swap requests.
    Shows 3 recent swap listings as preview.
    """
    # Fetch 3 most recent swaps for preview (simple query)
    recent_swaps = Swaps.objects.select_related(
        'user',
        'county'
    ).order_by('-created_at')[:3]
    
    # Prepare swap data for display
    swaps_preview = []
    for swap in recent_swaps:
        profile = getattr(swap.user, 'profile', None)
        school = getattr(profile, 'school', None) if profile else None
        level = getattr(profile, 'level', None) if profile else None
        school_ward = getattr(school, 'ward', None) if school else None
        school_county_name = 'N/A'
        if school_ward:
            const = getattr(school_ward, 'constituency', None)
            if const:
                county = getattr(const, 'county', None)
                if county:
                    school_county_name = county.name
        
        swap_data = {
            'id': swap.id,
            'school_name': school.name if school else 'N/A',
            'current_county': school_county_name,
            'target_county': swap.county.name if swap.county else 'Any County',
            'level': level.name if level else 'N/A',
            'created_at': swap.created_at,
        }
        swaps_preview.append(swap_data)
    
    return render(request, "home/landing.html", {
        'swaps_preview': swaps_preview,
    })


@login_required
def create_school(request):
    """
    View for creating a new school.
    Only superusers can add new schools.
    """
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to add schools.")
        return redirect('home:home')

    # Get all counties for the template
    counties = Counties.objects.all().order_by('name')
    
    # Get selected values from POST/GET data for form repopulation
    selected_county = request.POST.get('county')
    selected_constituency = request.POST.get('constituency')
    selected_ward = request.POST.get('ward')
    
    # Initialize form with POST data if available
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        
        if form.is_valid():
            try:
                # Get the ward from the form
                ward = form.cleaned_data.get('ward')
                if not ward:
                    messages.error(request, "Please select a valid ward.")
                else:
                    # Create the school with the selected ward
                    school = form.save(commit=False)
                    school.ward = ward
                    school.save()
                    form.save_m2m()  # Save many-to-many relationships if any
                    messages.success(request, f"School '{school.name}' has been added successfully!")
                    return redirect('home:all_schools')
            except Exception as e:
                messages.error(request, f"An error occurred while saving the school: {str(e)}")
    else:
        # For GET requests, initialize an empty form
        form = SchoolForm()
    
    # Get constituencies and wards based on selected values for form repopulation
    constituencies = Constituencies.objects.none()
    wards = Wards.objects.none()
    
    if selected_county:
        try:
            county_id = int(selected_county)
            constituencies = Constituencies.objects.filter(county_id=county_id).order_by('name')
            
            if selected_constituency:
                try:
                    constituency_id = int(selected_constituency)
                    wards = Wards.objects.filter(constituency_id=constituency_id).order_by('name')
                except (ValueError, TypeError):
                    pass
        except (ValueError, TypeError):
            pass
    
    # Convert selected values to integers for the template
    selected_county_id = int(selected_county) if selected_county and selected_county.isdigit() else None
    selected_constituency_id = int(selected_constituency) if selected_constituency and selected_constituency.isdigit() else None
    selected_ward_id = int(selected_ward) if selected_ward and selected_ward.isdigit() else None
    
    return render(request, 'home/school_form.html', {
        'form': form,
        'counties': counties,
        'constituencies': constituencies,
        'wards': wards,
        'selected_county': selected_county_id,
        'selected_constituency': selected_constituency_id,
        'selected_ward': selected_ward_id,
        'title': 'Add New School',
    })


def get_wards(request):
    """API endpoint to get wards for a given constituency."""
    constituency_id = request.GET.get('constituency_id')
    wards = Wards.objects.filter(constituency_id=constituency_id).order_by('name')
    ward_list = [{'id': ward.id, 'name': ward.name} for ward in wards]
    return JsonResponse({'wards': ward_list})


@login_required
def all_schools(request):
    """View to list all schools."""
    schools = Schools.objects.all().order_by('name')
    return render(request, 'home/school_list.html', {
        'schools': schools,
        'title': 'All Schools',
    })


@login_required
def create_mysubject(request):
    """
    View to handle subject selection for a user.
    Only Secondary/High School teachers can select subjects.
    """
    user = request.user
    success = False
    current_subjects = Subject.objects.none()
    display_name = None
    user_level = None
    level_form = None
    is_secondary_level = False

    # Get user's profile and level
    profile = getattr(user, "profile", None)
    
    # Handle level form submission
    if request.method == "POST" and 'set_level' in request.POST:
        if not profile:
            from users.models import PersonalProfile
            profile = PersonalProfile.objects.create(user=user)
        
        level_id = request.POST.get('level')
        if level_id:
            try:
                level = Level.objects.get(id=level_id)
                profile.level = level
                profile.save()
                messages.success(request, "Your teaching level has been updated successfully!")
                return redirect('home:create_mysubject')
            except Level.DoesNotExist:
                messages.error(request, "Invalid level selected.")
    
    # Get user's current level if exists
    if profile and hasattr(profile, 'level') and profile.level:
        user_level = profile.level
        # Check if user is Secondary/High School level
        is_secondary_level = user_level.name == "Secondary/High School"
    
    # Set display name
    if profile and (profile.first_name or profile.last_name):
        display_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
    else:
        display_name = user.email
    
    # Initialize forms - only for Secondary/High School level
    form = MySubjectForm(request.POST or None, user=user) if user_level and is_secondary_level else None
    
    # Get current user's subjects if level is set and is secondary
    if user_level and is_secondary_level:
        current_subjects = Subject.objects.filter(
            mysubject__user=user
        ).distinct()
    
    # Handle subject form submission - only for Secondary/High School
    if request.method == "POST" and form and form.is_valid() and is_secondary_level:
        # Get selected subjects
        selected_subjects = form.cleaned_data.get('subject', [])
        
        # Get or create the user's MySubject record
        my_subject, created = MySubject.objects.get_or_create(user=user)
        
        # Update the many-to-many relationship using set()
        my_subject.subject.set(selected_subjects)
        
        messages.success(request, "Your subjects have been updated successfully!")
        return redirect('home:create_mysubject')

    # Get all available levels for the level selection dropdown
    levels = Level.objects.all().order_by('name')
    
    return render(
        request,
        "home/mysubject_form.html",
        {
            "form": form,
            "success": success,
            "current_subjects": current_subjects,
            "user": user,
            "display_name": display_name,
            "user_level": user_level,
            "levels": levels,
            "is_secondary_level": is_secondary_level,
        },
    )


@login_required
def create_swap(request):
    """
    Page to create a new Swap record for the logged-in user.
    """
    user = request.user
    form = SwapForm(request.POST or None)
    success = False

    # Use similar display name logic
    profile = getattr(user, "profile", None)
    if profile and (getattr(profile, "first_name", None) or getattr(profile, "last_name", None)):
        first = profile.first_name or ""
        last = profile.last_name or ""
        display_name = f"{first} {last}".strip()
    else:
        display_name = user.email

    if request.method == "POST" and form.is_valid():
        swap = form.save(commit=False)
        swap.user = user
        swap.save()
        success = True

    recent_swaps = Swaps.objects.filter(user=user).order_by("-created_at")[:5]

    return render(
        request,
        "home/swap_form.html",
        {
            "form": form,
            "success": success,
            "user": user,
            "display_name": display_name,
            "recent_swaps": recent_swaps,
        },
    )


def all_swaps(request):
    """
    Public page listing recent active swaps from all users.
    Excludes archived and inactive swaps.
    """
    # Check if user has swap preferences
    has_swap_preferences = False
    if request.user.is_authenticated:
        from home.models import SwapPreference
        has_swap_preferences = SwapPreference.objects.filter(user=request.user).exists()
    
    # Get filter parameters
    selected_county = request.GET.get('county')
    selected_constituency = request.GET.get('constituency')
    selected_ward = request.GET.get('ward')
    
    # Debug print
    print(f"DEBUG - Filters - County: {selected_county}, Constituency: {selected_constituency}, Ward: {selected_ward}")
    
    # Start with base query - exclude archived, inactive, and current user's swaps
    swaps = Swaps.objects.filter(
        archived=False,  # Exclude archived swaps
        status=True,     # Only include active swaps
    )
    
    # Exclude swaps created by the current user if they're logged in
    if request.user.is_authenticated:
        swaps = swaps.exclude(user=request.user)
    
    # Apply filters if provided
    if selected_county and selected_county.isdigit():
        print(f"DEBUG - Filtering by county_id: {selected_county}")
        swaps = swaps.filter(county_id=selected_county)
    
    if selected_constituency and selected_constituency.isdigit():
        print(f"DEBUG - Filtering by constituency_id: {selected_constituency}")
        swaps = swaps.filter(constituency_id=selected_constituency)
    
    if selected_ward and selected_ward.isdigit():
        print(f"DEBUG - Filtering by ward_id: {selected_ward}")
        swaps = swaps.filter(ward_id=selected_ward)
    
    # Order and limit results
    from django.db.models import Prefetch

    # First get all the swaps with related data
    swaps = swaps.select_related(
        "county", 
        "constituency", 
        "ward",
        "user__profile__school"  # Get the user's school
    ).order_by("-created_at")[:50]
    
    # Prefetch the subjects for all users in one query
    from django.db.models import Prefetch

    from home.models import MySubject  # MySubject is defined in the home app

    # Get all user IDs from the swaps
    user_ids = [swap.user_id for swap in swaps]
    
    # Create a dictionary mapping user_id to their subjects
    user_subjects = {}
    # Prefetch the many-to-many relationship
    for mysubject in MySubject.objects.filter(user_id__in=user_ids).prefetch_related('subject'):
        if mysubject.user_id not in user_subjects:
            user_subjects[mysubject.user_id] = []
        # Get all subjects for this MySubject instance
        user_subjects[mysubject.user_id].extend(list(mysubject.subject.all()))
    
    # Get all counties for the filter dropdown
    counties = Counties.objects.all().order_by('name')
    
    # Get selected county and its constituencies if a county is selected
    selected_county_obj = None
    # Initialize as empty querysets instead of empty lists
    constituencies = Constituencies.objects.none()
    wards = Wards.objects.none()
    
    if selected_county and selected_county.isdigit():
        selected_county_obj = Counties.objects.filter(id=selected_county).first()
        if selected_county_obj:
            constituencies = Constituencies.objects.filter(county=selected_county_obj).order_by('name')
    
    # Get selected constituency and its wards if a constituency is selected
    selected_constituency_obj = None
    if selected_constituency and selected_constituency.isdigit():
        selected_constituency_obj = Constituencies.objects.filter(id=selected_constituency).first()
        if selected_constituency_obj:
            wards = Wards.objects.filter(constituency=selected_constituency_obj).order_by('name')
    
    context = {
        'swaps': swaps,
        'counties': counties,
        'constituencies': constituencies,
        'wards': wards,
        'selected_county': int(selected_county) if selected_county and selected_county.isdigit() else '',
        'selected_constituency': int(selected_constituency) if selected_constituency and selected_constituency.isdigit() else '',
        'selected_ward': int(selected_ward) if selected_ward and selected_ward.isdigit() else '',
        'has_swap_preferences': has_swap_preferences,
        'user': request.user if request.user.is_authenticated else None,
    }
    # Get current user's profile, school, and swap preferences if logged in
    current_user = request.user
    current_user_profile = getattr(current_user, 'profile', None) if current_user.is_authenticated else None
    current_user_school = getattr(current_user_profile, 'school', None) if current_user_profile else None
    
    # Get current user's swap preferences
    current_user_prefs = None
    if current_user.is_authenticated:
        current_user_prefs = getattr(current_user, 'swappreference', None)
    
    # Get current user's subjects if logged in
    current_user_subjects = set()
    if current_user.is_authenticated:
        current_user_subjects = set(MySubject.objects.filter(user=current_user).values_list('subject__name', flat=True))
    
    # Prepare the swaps data with match scoring
    swaps_data = []
    for swap in swaps:
        user_profile = getattr(swap.user, 'profile', None)
        school = getattr(user_profile, 'school', None)
        
        # Get swap poster's subjects
        poster_subjects = set(subj.name for subj in user_subjects.get(swap.user_id, []))
        
        # Calculate match score (0-100)
        match_score = 0
        common_subjects = set()
        
        # 1. Subject match (50 points max)
        if current_user.is_authenticated and poster_subjects:
            common_subjects = current_user_subjects.intersection(poster_subjects)
            if common_subjects:
                match_score += 50  # Max 50 points for subject match
        
        # 2. Location match (50 points max)
        location_score = 0
        is_near_perfect_match = False
        
        if current_user_prefs and swap.county and swap.constituency and swap.ward:
            # County match (20 points)
            if current_user_prefs.desired_county and current_user_prefs.desired_county == swap.county:
                location_score += 20
                # Constituency match (20 points)
                if (current_user_prefs.desired_constituency and 
                    current_user_prefs.desired_constituency == swap.constituency):
                    location_score += 20
                    # Ward match (10 points) - only if it matches
                    if (current_user_prefs.desired_ward and 
                        current_user_prefs.desired_ward == swap.ward):
                        location_score += 10
                    # Check for near perfect match (county and constituency match, but not ward)
                    elif (current_user_prefs.desired_ward and 
                          current_user_prefs.desired_ward != swap.ward and
                          common_subjects):
                        is_near_perfect_match = True
            
            match_score += location_score
        
        swaps_data.append({
            'swap': swap,
            'user_school': school,
            'user_subjects': user_subjects.get(swap.user_id, []),
            'match_score': match_score,
            'is_perfect_match': match_score == 100,  # 100% match
            'is_near_perfect_match': is_near_perfect_match,
            'common_subjects': list(common_subjects)[:3]  # Show up to 3 common subjects
        })
    
    # Sort by match score (highest first)
    swaps_data.sort(key=lambda x: x['match_score'], reverse=True)
    
    context = {
        "swaps_data": swaps_data,  # Use the enriched data
        "title": "All Swaps",
        "counties": counties,
        "constituencies": constituencies,
        "wards": wards,
        "selected_county": selected_county,
        "selected_constituency": selected_constituency,
        "selected_ward": selected_ward,
    }
    
    # Convert querysets to lists for template rendering and get counts
    constituencies_list = list(constituencies)
    wards_list = list(wards)
    
    print("DEBUG - Context:", {
        'selected_county': selected_county,
        'selected_constituency': selected_constituency,
        'selected_ward': selected_ward,
        'constituencies_count': len(constituencies_list),
        'wards_count': len(wards_list),
        'swaps_count': len(swaps_data) if isinstance(swaps_data, list) else swaps_data.count()
    })
    
    context = {
        "swaps_data": swaps_data,  # Use the enriched data
        "title": "All Swaps",
        "counties": counties,
        "constituencies": constituencies_list,  # Use the list version
        "wards": wards_list,  # Use the list version
        "selected_county": selected_county,
        "selected_constituency": selected_constituency,
        "selected_ward": selected_ward,
        "has_swap_preferences": has_swap_preferences,
        "user": request.user if request.user.is_authenticated else None,
    }
    
    return render(request, "home/all_swaps.html", context)


def primary_swaps(request):
    """
    Page listing swaps from users whose PersonalProfile level is 'Primary School'.
    Includes matching score calculation for logged-in users.
    
    Matching Logic:
    - Perfect Match: Creator's school location = my desired location AND 
                     Creator's target = my current school location (mutual swap)
    - Excellent Match: County matches both ways, constituency may differ
    - Good Match: At least county matches one direction
    - Normal: No significant location match
    """
    # Check if user has swap preferences and profile setup
    has_swap_preferences = False
    has_level = False
    current_user_prefs = None
    current_user_school = None
    current_user_school_county = None
    current_user_school_constituency = None
    current_user_school_ward = None
    show_setup_modal = False
    missing_items = []
    
    if request.user.is_authenticated:
        has_swap_preferences = SwapPreference.objects.filter(user=request.user).exists()
        current_user_prefs = getattr(request.user, 'swappreference', None)
        current_user_profile = getattr(request.user, 'profile', None)
        
        # Check if user has set their level
        if current_user_profile and current_user_profile.level:
            has_level = True
        else:
            missing_items.append('level')
        
        # Check if user has swap preferences
        if not has_swap_preferences:
            missing_items.append('swap_preference')
        
        if current_user_profile:
            current_user_school = current_user_profile.school
            if current_user_school and current_user_school.ward:
                current_user_school_ward = current_user_school.ward
                current_user_school_constituency = current_user_school.ward.constituency
                current_user_school_county = current_user_school.ward.constituency.county
        
        # Show modal if any required items are missing
        show_setup_modal = len(missing_items) > 0
    
    # Get filter parameters
    selected_county = request.GET.get('county')
    selected_constituency = request.GET.get('constituency')
    selected_ward = request.GET.get('ward')
    
    # Start with base query - filter by Primary School level
    swaps = Swaps.objects.filter(
        archived=False,
        status=True,
        user__profile__level__name="Primary School"  # Filter by Primary School level
    )
    
    # Exclude swaps created by the current user if they're logged in
    if request.user.is_authenticated:
        swaps = swaps.exclude(user=request.user)
    
    # Apply location filters if provided
    if selected_county and selected_county.isdigit():
        swaps = swaps.filter(county_id=selected_county)
    
    if selected_constituency and selected_constituency.isdigit():
        swaps = swaps.filter(constituency_id=selected_constituency)
    
    if selected_ward and selected_ward.isdigit():
        swaps = swaps.filter(ward_id=selected_ward)
    
    # Get swaps with related data including full school location chain
    swaps = swaps.select_related(
        "county", 
        "constituency", 
        "ward",
        "user__profile__school__ward__constituency__county"
    ).order_by("-created_at")[:50]
    
    # Get user subjects
    user_ids = [swap.user_id for swap in swaps]
    user_subjects = {}
    for mysubject in MySubject.objects.filter(user_id__in=user_ids).prefetch_related('subject'):
        if mysubject.user_id not in user_subjects:
            user_subjects[mysubject.user_id] = []
        user_subjects[mysubject.user_id].extend(list(mysubject.subject.all()))
    
    # Get all counties for the filter dropdown
    counties = Counties.objects.all().order_by('name')
    
    # Get constituencies and wards based on selection
    constituencies = Constituencies.objects.none()
    wards = Wards.objects.none()
    
    if selected_county and selected_county.isdigit():
        selected_county_obj = Counties.objects.filter(id=selected_county).first()
        if selected_county_obj:
            constituencies = Constituencies.objects.filter(county=selected_county_obj).order_by('name')
    
    if selected_constituency and selected_constituency.isdigit():
        selected_constituency_obj = Constituencies.objects.filter(id=selected_constituency).first()
        if selected_constituency_obj:
            wards = Wards.objects.filter(constituency=selected_constituency_obj).order_by('name')
    
    # Prepare swaps data with matching scores
    swaps_data = []
    for swap in swaps:
        user_profile = getattr(swap.user, 'profile', None)
        school = getattr(user_profile, 'school', None)
        
        # Get creator's school location
        creator_school_county = None
        creator_school_constituency = None
        creator_school_ward = None
        if school and school.ward:
            creator_school_ward = school.ward
            creator_school_constituency = school.ward.constituency
            creator_school_county = school.ward.constituency.county
        
        # Calculate match score
        match_score = 0
        match_label = "Normal"
        
        if request.user.is_authenticated and current_user_prefs and current_user_school_county:
            # Check Direction 1: Creator's school location matches my desired location
            # (Where the creator IS = Where I WANT to go)
            dir1_county_match = (creator_school_county and 
                                current_user_prefs.desired_county and 
                                creator_school_county.id == current_user_prefs.desired_county.id)
            dir1_constituency_match = (creator_school_constituency and 
                                       current_user_prefs.desired_constituency and 
                                       creator_school_constituency.id == current_user_prefs.desired_constituency.id)
            dir1_ward_match = (creator_school_ward and 
                              current_user_prefs.desired_ward and 
                              creator_school_ward.id == current_user_prefs.desired_ward.id)
            
            # Check Direction 2: Creator's target location matches my current school location
            # (Where the creator WANTS to go = Where I AM)
            dir2_county_match = (swap.county and 
                                current_user_school_county and 
                                swap.county.id == current_user_school_county.id)
            dir2_constituency_match = (swap.constituency and 
                                       current_user_school_constituency and 
                                       swap.constituency.id == current_user_school_constituency.id)
            dir2_ward_match = (swap.ward and 
                              current_user_school_ward and 
                              swap.ward.id == current_user_school_ward.id)
            
            # Calculate score based on matching levels
            # Perfect Match: Both directions match at county level or better
            if dir1_county_match and dir2_county_match:
                if dir1_ward_match and dir2_ward_match:
                    match_score = 100
                    match_label = "Perfect Match"
                elif dir1_constituency_match and dir2_constituency_match:
                    match_score = 95
                    match_label = "Perfect Match"
                elif dir1_county_match and dir2_county_match:
                    match_score = 90
                    match_label = "Perfect Match"
            # Excellent Match: One direction fully matches, other partially
            elif (dir1_county_match and dir2_constituency_match) or (dir1_constituency_match and dir2_county_match):
                match_score = 80
                match_label = "Excellent Match"
            elif dir1_county_match or dir2_county_match:
                # Good Match: At least one direction has county match
                if dir1_constituency_match or dir2_constituency_match:
                    match_score = 70
                    match_label = "Good Match"
                elif dir1_county_match and not dir2_county_match:
                    match_score = 60
                    match_label = "Good Match"
                elif dir2_county_match and not dir1_county_match:
                    match_score = 55
                    match_label = "Good Match"
                else:
                    match_score = 50
                    match_label = "Good Match"
            else:
                match_score = 0
                match_label = "Normal"
        
        swaps_data.append({
            'swap': swap,
            'user_school': school,
            'user_subjects': user_subjects.get(swap.user_id, []),
            'match_score': match_score,
            'match_label': match_label,
            'is_perfect_match': match_label == "Perfect Match",
            'is_excellent_match': match_label == "Excellent Match",
            'is_good_match': match_label == "Good Match",
            'common_subjects': []
        })
    
    # Sort by match score (highest first)
    swaps_data.sort(key=lambda x: x['match_score'], reverse=True)
    
    # Get bookmarked swap IDs for the current user (use list for template compatibility)
    bookmarked_ids = []
    if request.user.is_authenticated:
        bookmarked_ids = list(Bookmark.objects.filter(
            user=request.user,
            bookmark_type='swap'
        ).values_list('swap_id', flat=True))
    
    context = {
        "swaps_data": swaps_data,
        "title": "Primary School Swaps",
        "page_subtitle": "Browse swap requests from Primary School teachers",
        "counties": counties,
        "constituencies": list(constituencies),
        "wards": list(wards),
        "selected_county": selected_county,
        "selected_constituency": selected_constituency,
        "selected_ward": selected_ward,
        "has_swap_preferences": has_swap_preferences,
        "has_level": has_level,
        "show_setup_modal": show_setup_modal,
        "missing_items": missing_items,
        "user": request.user if request.user.is_authenticated else None,
        "level_filter": "primary",
        "bookmarked_ids": bookmarked_ids,
    }
    
    return render(request, "home/level_swaps.html", context)


def secondary_swaps(request):
    """
    Page listing swaps from users whose PersonalProfile level is 'Secondary/High School'.
    Includes matching score calculation based on BOTH location AND subjects.
    
    Matching Logic (requires both location AND subject match):
    - Perfect Match: Location matches both ways AND subjects match
    - Excellent Match: Location matches well AND some subjects match
    - Good Match: Either location or subjects match well
    - Normal: No significant match
    """
    # Check if user has swap preferences, profile setup, and subjects
    has_swap_preferences = False
    has_level = False
    has_subjects = False
    current_user_prefs = None
    current_user_school = None
    current_user_school_county = None
    current_user_school_constituency = None
    current_user_school_ward = None
    current_user_subjects = set()
    show_setup_modal = False
    missing_items = []
    
    if request.user.is_authenticated:
        has_swap_preferences = SwapPreference.objects.filter(user=request.user).exists()
        current_user_prefs = getattr(request.user, 'swappreference', None)
        current_user_profile = getattr(request.user, 'profile', None)
        
        # Check if user has set their level
        if current_user_profile and current_user_profile.level:
            has_level = True
        else:
            missing_items.append('level')
        
        # Check if user has swap preferences
        if not has_swap_preferences:
            missing_items.append('swap_preference')
        
        if current_user_profile:
            current_user_school = current_user_profile.school
            if current_user_school and current_user_school.ward:
                current_user_school_ward = current_user_school.ward
                current_user_school_constituency = current_user_school.ward.constituency
                current_user_school_county = current_user_school.ward.constituency.county
        
        # Get current user's subjects
        current_user_subjects = set(
            MySubject.objects.filter(user=request.user).values_list('subject__id', flat=True)
        )
        
        # Check if user has subjects (required for secondary)
        if len(current_user_subjects) > 0:
            has_subjects = True
        else:
            missing_items.append('subjects')
        
        # Show modal if any required items are missing
        show_setup_modal = len(missing_items) > 0
    
    # Get filter parameters
    selected_county = request.GET.get('county')
    selected_constituency = request.GET.get('constituency')
    selected_ward = request.GET.get('ward')
    
    # Start with base query - filter by Secondary/High School level
    swaps = Swaps.objects.filter(
        archived=False,
        status=True,
        user__profile__level__name="Secondary/High School"  # Filter by Secondary/High School level
    )
    
    # Exclude swaps created by the current user if they're logged in
    if request.user.is_authenticated:
        swaps = swaps.exclude(user=request.user)
    
    # Apply location filters if provided
    if selected_county and selected_county.isdigit():
        swaps = swaps.filter(county_id=selected_county)
    
    if selected_constituency and selected_constituency.isdigit():
        swaps = swaps.filter(constituency_id=selected_constituency)
    
    if selected_ward and selected_ward.isdigit():
        swaps = swaps.filter(ward_id=selected_ward)
    
    # Get swaps with related data including full school location chain
    swaps = swaps.select_related(
        "county", 
        "constituency", 
        "ward",
        "user__profile__school__ward__constituency__county"
    ).order_by("-created_at")[:50]
    
    # Get user subjects for all swap creators
    user_ids = [swap.user_id for swap in swaps]
    user_subjects = {}
    user_subject_ids = {}  # For matching calculation
    for mysubject in MySubject.objects.filter(user_id__in=user_ids).prefetch_related('subject'):
        if mysubject.user_id not in user_subjects:
            user_subjects[mysubject.user_id] = []
            user_subject_ids[mysubject.user_id] = set()
        subjects_list = list(mysubject.subject.all())
        user_subjects[mysubject.user_id].extend(subjects_list)
        user_subject_ids[mysubject.user_id].update(s.id for s in subjects_list)
    
    # Get all counties for the filter dropdown
    counties = Counties.objects.all().order_by('name')
    
    # Get constituencies and wards based on selection
    constituencies = Constituencies.objects.none()
    wards = Wards.objects.none()
    
    if selected_county and selected_county.isdigit():
        selected_county_obj = Counties.objects.filter(id=selected_county).first()
        if selected_county_obj:
            constituencies = Constituencies.objects.filter(county=selected_county_obj).order_by('name')
    
    if selected_constituency and selected_constituency.isdigit():
        selected_constituency_obj = Constituencies.objects.filter(id=selected_constituency).first()
        if selected_constituency_obj:
            wards = Wards.objects.filter(constituency=selected_constituency_obj).order_by('name')
    
    # Prepare swaps data with matching scores
    swaps_data = []
    for swap in swaps:
        user_profile = getattr(swap.user, 'profile', None)
        school = getattr(user_profile, 'school', None)
        
        # Get creator's school location
        creator_school_county = None
        creator_school_constituency = None
        creator_school_ward = None
        if school and school.ward:
            creator_school_ward = school.ward
            creator_school_constituency = school.ward.constituency
            creator_school_county = school.ward.constituency.county
        
        # Get creator's subjects
        creator_subject_ids = user_subject_ids.get(swap.user_id, set())
        
        # Calculate match score
        match_score = 0
        match_label = "Normal"
        location_score = 0
        subject_score = 0
        common_subjects = []
        
        if request.user.is_authenticated:
            # === SUBJECT MATCHING ===
            if current_user_subjects and creator_subject_ids:
                common_subject_ids = current_user_subjects.intersection(creator_subject_ids)
                if common_subject_ids:
                    # Get common subject names for display
                    common_subjects = [s.name for s in user_subjects.get(swap.user_id, []) 
                                       if s.id in common_subject_ids][:3]
                    
                    # Calculate subject match percentage
                    total_subjects = len(current_user_subjects.union(creator_subject_ids))
                    match_percentage = len(common_subject_ids) / total_subjects if total_subjects > 0 else 0
                    
                    if match_percentage >= 0.5:  # 50%+ subjects match
                        subject_score = 50
                    elif match_percentage >= 0.25:  # 25%+ subjects match
                        subject_score = 35
                    elif len(common_subject_ids) >= 1:  # At least 1 subject matches
                        subject_score = 20
            
            # === LOCATION MATCHING ===
            if current_user_prefs and current_user_school_county:
                # Direction 1: Creator's school location matches my desired location
                dir1_county_match = (creator_school_county and 
                                    current_user_prefs.desired_county and 
                                    creator_school_county.id == current_user_prefs.desired_county.id)
                dir1_constituency_match = (creator_school_constituency and 
                                           current_user_prefs.desired_constituency and 
                                           creator_school_constituency.id == current_user_prefs.desired_constituency.id)
                
                # Direction 2: Creator's target matches my current school location
                dir2_county_match = (swap.county and 
                                    current_user_school_county and 
                                    swap.county.id == current_user_school_county.id)
                dir2_constituency_match = (swap.constituency and 
                                           current_user_school_constituency and 
                                           swap.constituency.id == current_user_school_constituency.id)
                
                # Calculate location score
                if dir1_county_match and dir2_county_match:
                    if dir1_constituency_match and dir2_constituency_match:
                        location_score = 50  # Full mutual match
                    else:
                        location_score = 45  # County mutual match
                elif dir1_county_match or dir2_county_match:
                    if dir1_constituency_match or dir2_constituency_match:
                        location_score = 35
                    else:
                        location_score = 25
            
            # === COMBINED SCORE (Location + Subjects both required for secondary) ===
            match_score = location_score + subject_score
            
            # Determine match label based on combined score
            # Perfect Match: Both location AND subjects match well
            if location_score >= 45 and subject_score >= 35:
                match_label = "Perfect Match"
            elif location_score >= 35 and subject_score >= 20:
                match_label = "Excellent Match"
            elif (location_score >= 25 and subject_score >= 20) or (location_score >= 35 and subject_score > 0):
                match_label = "Good Match"
            elif subject_score > 0 or location_score > 0:
                match_label = "Normal"
            else:
                match_label = "Normal"
                match_score = 0
        
        swaps_data.append({
            'swap': swap,
            'user_school': school,
            'user_subjects': user_subjects.get(swap.user_id, []),
            'match_score': match_score,
            'match_label': match_label,
            'is_perfect_match': match_label == "Perfect Match",
            'is_excellent_match': match_label == "Excellent Match",
            'is_good_match': match_label == "Good Match",
            'common_subjects': common_subjects,
            'has_subject_match': len(common_subjects) > 0,
        })
    
    # Sort by match score (highest first)
    swaps_data.sort(key=lambda x: x['match_score'], reverse=True)
    
    # Get bookmarked swap IDs for the current user (use list for template compatibility)
    bookmarked_ids = []
    if request.user.is_authenticated:
        bookmarked_ids = list(Bookmark.objects.filter(
            user=request.user,
            bookmark_type='swap'
        ).values_list('swap_id', flat=True))
    
    context = {
        "swaps_data": swaps_data,
        "title": "Secondary/High School Swaps",
        "page_subtitle": "Browse swap requests from Secondary/High School teachers",
        "counties": counties,
        "constituencies": list(constituencies),
        "wards": list(wards),
        "selected_county": selected_county,
        "selected_constituency": selected_constituency,
        "selected_ward": selected_ward,
        "has_swap_preferences": has_swap_preferences,
        "has_level": has_level,
        "has_subjects": has_subjects,
        "show_setup_modal": show_setup_modal,
        "missing_items": missing_items,
        "user": request.user if request.user.is_authenticated else None,
        "level_filter": "secondary",
        "bookmarked_ids": bookmarked_ids,
    }
    
    return render(request, "home/level_swaps.html", context)


@login_required
def my_swaps(request):
    """
    Page where a user can see swaps they have created.
    """
    user_swaps = Swaps.objects.filter(user=request.user).select_related("county", "constituency", "ward").order_by("-created_at")
    return render(request, "home/my_swaps.html", {"swaps": user_swaps})


def swap_detail(request, swap_id):
    """
    Detailed view of a specific swap.
    """
    swap = get_object_or_404(Swaps, id=swap_id)
    user = request.user
    
    # Check if the current user is the owner of the swap
    is_owner = (user.is_authenticated and user == swap.user)
    
    # Check if the current user has an active subscription
    has_active_subscription = False
    if user.is_authenticated and hasattr(user, 'my_subscription'):
        has_active_subscription = user.my_subscription.is_active  # Remove parentheses as it's a property
    
    # Get the user's profile information if available
    user_profile = None
    if swap.user and hasattr(swap.user, 'profile'):
        phone_number = getattr(swap.user.profile, 'phone', None) or getattr(swap.user.profile, 'phone_number', None)
        # Mask phone number if viewer doesn't have an active subscription and is not the owner
        display_phone = str(phone_number) if (is_owner or has_active_subscription) else None
        user_profile = {
            'first_name': getattr(swap.user.profile, 'first_name', 'Not provided') or 'Not provided',
            'last_name': getattr(swap.user.profile, 'last_name', 'Not provided') or 'Not provided',
            'phone_number': display_phone if display_phone else (f'******{str(phone_number)[-4:]}' if phone_number else 'Not provided'),
            'tsc_number': getattr(swap.user.profile, 'tsc_number', 'Not provided') or 'Not provided',
            'show_contact': is_owner or has_active_subscription
        }
    
    # Check if the current user has already requested this swap
    has_requested = False
    if user.is_authenticated and not is_owner:
        has_requested = SwapRequests.objects.filter(user=user, swap=swap).exists()
    
    # Get all swap requests for this swap
    swap_requests = None
    if is_owner:
        swap_requests = SwapRequests.objects.filter(swap=swap).select_related('user__profile')
    
    context = {
        'swap': swap,
        'is_owner': is_owner,
        'user_profile': user_profile,
        'has_requested': has_requested,
        'swap_requests': swap_requests,
        'has_active_subscription': has_active_subscription,
    }
    
    return render(request, 'home/swap_detail.html', context)


def fast_swap_detail(request, fastswap_id):
    """
    Detailed view of a specific FastSwap entry.
    """
    fast_swap = get_object_or_404(FastSwap, id=fastswap_id)
    user = request.user
    
    # Check if the current user has an active subscription
    has_active_subscription = False
    is_admin = False
    if user.is_authenticated:
        is_admin = user.is_superuser or user.is_staff
        if hasattr(user, 'my_subscription'):
            has_active_subscription = user.my_subscription.is_active
    
    # Mask contact info for non-subscribers
    show_contact = is_admin or has_active_subscription
    if show_contact:
        display_phone = fast_swap.phone
        display_name = fast_swap.names
    else:
        display_phone = f"{fast_swap.phone[:4]}****{fast_swap.phone[-3:]}" if fast_swap.phone and len(fast_swap.phone) > 7 else "Hidden"
        name_parts = fast_swap.names.split()
        if name_parts:
            display_name = f"{name_parts[0]} {'*' * 5}"
        else:
            display_name = "Hidden"
    
    # Get acceptable counties
    acceptable_counties = fast_swap.acceptable_county.all()
    
    # Get subjects
    subjects = fast_swap.subjects.all()
    
    # Check if bookmarked
    is_bookmarked = False
    if user.is_authenticated:
        is_bookmarked = Bookmark.objects.filter(
            user=user,
            fast_swap=fast_swap,
            bookmark_type='fastswap'
        ).exists()
    
    context = {
        'fast_swap': fast_swap,
        'display_name': display_name,
        'display_phone': display_phone,
        'show_contact': show_contact,
        'acceptable_counties': acceptable_counties,
        'subjects': subjects,
        'is_bookmarked': is_bookmarked,
        'has_active_subscription': has_active_subscription,
    }
    
    return render(request, 'home/fast_swap_detail.html', context)


@login_required
def toggle_swap_status(request, swap_id):
    """
    Toggle the status of a swap (active/inactive).
    Only the owner of the swap can perform this action.
    """
    if request.method == 'POST':
        swap = get_object_or_404(Swaps, id=swap_id)
        
        # Check if the current user is the owner of the swap
        if request.user != swap.user:
            return JsonResponse({'error': 'You do not have permission to modify this swap'}, status=403)
        
        # Toggle the status
        swap.status = not swap.status
        swap.save()
        
        return JsonResponse({
            'success': True,
            'new_status': 'active' if swap.status else 'inactive',
            'status_text': 'Active' if swap.status else 'Inactive',
            'button_text': 'Deactivate' if swap.status else 'Activate',
            'status_class': 'bg-green-100 text-green-800' if swap.status else 'bg-red-100 text-red-800'
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def archive_swap(request, swap_id):
    """
    Archive a swap by setting archived=True
    """
    if request.method == 'POST':
        swap = get_object_or_404(Swaps, id=swap_id)
        
        # Check if the current user is the owner of the swap
        if request.user != swap.user:
            return HttpResponseForbidden("You don't have permission to perform this action.")
        
        # Archive the swap
        swap.archived = True
        swap.status = False  # Also set status to False when archiving
        swap.save()
        
        messages.success(request, 'Swap has been archived successfully.')
        return redirect('home:my_swaps')
    
    return HttpResponse('Method not allowed', status=405)

@login_required
def accept_swap_request(request, request_id):
    """
    Handle accepting a swap request.
    """
    swap_request = get_object_or_404(SwapRequests, id=request_id)
    
    # Only the swap owner can accept requests
    if request.user != swap_request.swap.user:
        return HttpResponseForbidden("You don't have permission to perform this action.")
    
    # Mark this request as accepted but keep it active
    swap_request.accepted = True
    swap_request.is_active = True  # Keep the request active
    swap_request.save()
    
    # Mark the swap as completed and keep it active
    swap = swap_request.swap
    swap.completed = True
    swap.status = True  # Keep the swap active
    swap.save()
    
    # Deactivate all other pending requests for this swap
    # but only if they haven't been accepted
    SwapRequests.objects.filter(
        swap=swap, 
        is_active=True,
        accepted=False  # Only deactivate unaccepted requests
    ).exclude(id=request_id).update(is_active=False)
    
    messages.success(request, f"You have accepted the swap request from {swap_request.user.email}")
    return redirect('home:my_swap_requests')

@login_required
def reject_swap_request(request, request_id):
    """
    Handle rejecting a swap request.
    """
    swap_request = get_object_or_404(SwapRequests, id=request_id)
    
    # Only the swap owner can reject requests
    if request.user != swap_request.swap.user:
        return HttpResponseForbidden("You don't have permission to perform this action.")
    
    # Mark the request as inactive (soft delete) instead of hard deleting
    swap_request.is_active = False
    swap_request.accepted = False  # Explicitly mark as not accepted
    swap_request.save()
    
    messages.info(request, f"You have rejected the swap request from {swap_request.user.email}")
    return redirect('home:my_swap_requests')

@login_required
def request_swap(request, swap_id):
    """
    Handle swap request creation.
    """
    swap = get_object_or_404(Swaps, id=swap_id)
    
    # Prevent users from requesting their own swaps
    if request.user == swap.user:
        return HttpResponseForbidden("You cannot request your own swap.")
    
    # Check if user already has an active request for this swap
    existing_request = SwapRequests.objects.filter(
        user=request.user,
        swap=swap,
        is_active=True
    ).exists()
    
    if existing_request:
        messages.warning(request, "You have already requested this swap.")
        return redirect('home:swap_detail', swap_id=swap_id)
    
    if request.method == 'POST':
        SwapRequests.objects.create(
            user=request.user,
            swap=swap,
            is_active=True
        )
        messages.success(request, "Your swap request has been sent!")
        return redirect('home:swap_detail', swap_id=swap_id)
    
    return redirect('home:swap_detail', swap_id=swap_id)


@login_required
def my_swap_requests(request):
    """
    Display all swap requests made by the current user.
    """
    user = request.user
    sent_requests = SwapRequests.objects.filter(user=request.user).select_related('swap', 'swap__user').order_by('-created_at')
    received_requests = SwapRequests.objects.filter(swap__user=user).select_related('swap', 'user').order_by('-created_at')
    
    context = {
        'sent_requests': sent_requests,
        'received_requests': received_requests,
        'title': 'My Swap Requests',
    }
    
    return render(request, 'home/my_swap_requests.html', context)


@login_required
def edit_school(request, school_id):
    """
    View for editing an existing school.
    Only superusers can edit schools.
    """
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to edit schools.")
        return redirect('home:all_schools')
    
    school = get_object_or_404(Schools, pk=school_id)
    
    if request.method == 'POST':
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            try:
                # Get the ward from the form
                ward = form.cleaned_data.get('ward')
                if not ward:
                    messages.error(request, "Please select a valid ward.")
                else:
                    # Update the school with the selected ward
                    updated_school = form.save(commit=False)
                    updated_school.ward = ward
                    updated_school.save()
                    form.save_m2m()
                    messages.success(request, f"School '{updated_school.name}' has been updated successfully!")
                    return redirect('home:all_schools')
            except Exception as e:
                messages.error(request, f"An error occurred while updating the school: {str(e)}")
    else:
        form = SchoolForm(instance=school)
    
    # Get all counties for the template
    counties = Counties.objects.all().order_by('name')
    
    # Set the selected values for the form
    selected_county = school.ward.constituency.county_id if school.ward else None
    selected_constituency = school.ward.constituency_id if school.ward else None
    selected_ward = school.ward_id if school.ward else None
    
    # Get constituencies and wards based on selected values
    constituencies = Constituencies.objects.none()
    wards = Wards.objects.none()
    
    if selected_county:
        constituencies = Constituencies.objects.filter(county_id=selected_county).order_by('name')
        if selected_constituency:
            wards = Wards.objects.filter(constituency_id=selected_constituency).order_by('name')
    
    return render(request, 'home/school_form.html', {
        'form': form,
        'school': school,
        'counties': counties,
        'constituencies': constituencies,
        'wards': wards,
        'selected_county': selected_county,
        'selected_constituency': selected_constituency,
        'selected_ward': selected_ward,
        'title': f'Edit {school.name}',
        'is_edit': True,
    })


@login_required
def delete_school(request, school_id):
    """
    View for deleting a school.
    Only superusers can delete schools.
    """
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    try:
        school = get_object_or_404(Schools, pk=school_id)
        school_name = school.name
        school.delete()
        return JsonResponse({'success': True, 'message': f'School "{school_name}" has been deleted successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_constituencies(request):
    """API endpoint to get constituencies for a given county."""
    county_id = request.GET.get('county')
    if not county_id:
        return JsonResponse({'error': 'County ID is required'}, status=400)
    
    try:
        constituencies = list(Constituencies.objects.filter(
            county_id=county_id
        ).order_by('name').values('id', 'name'))
        return JsonResponse({'constituencies': constituencies})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_wards(request):
    """API endpoint to get wards for a given constituency."""
    constituency_id = request.GET.get('constituency_id')
    if not constituency_id:
        return JsonResponse({'error': 'Constituency ID is required'}, status=400)
    
    try:
        wards = list(Wards.objects.filter(
            constituency_id=constituency_id
        ).order_by('name').values('id', 'name'))
        return JsonResponse({'wards': wards})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def add_fast_swap(request):
    """
    View for adding a new FastSwap entry.
    Only superusers can add new FastSwap entries.
    """
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to add FastSwap entries.")
        return redirect('home:home')

    if request.method == 'POST':
        form = FastSwapForm(request.POST)
        if form.is_valid():
            try:
                fast_swap = form.save(commit=False)
                fast_swap.save()
                form.save_m2m()  # Save many-to-many fields
                messages.success(request, 'FastSwap entry added successfully!')
                return redirect('home:fast_swap_list')
            except Exception as e:
                messages.error(request, f'Error saving FastSwap: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FastSwapForm()
    
    return render(request, 'home/fast_swap_form.html', {
        'form': form,
        'title': 'Add FastSwap Entry'
    })


def fast_swap_list(request):
    """
    View to list all FastSwap entries.
    Accessible to all users (authenticated and unauthenticated).
    Supports filtering by level, county, constituency, and ward.
    """
    fast_swaps = FastSwap.objects.all().select_related(
        'current_county', 'current_constituency', 'current_ward', 
        'most_preferred', 'level'
    ).order_by('-created_at')
    
    # Get filter parameters
    level_filter = request.GET.get('level')
    county_id = request.GET.get('county')
    constituency_id = request.GET.get('constituency')
    ward_id = request.GET.get('ward')
    
    # Apply level filter
    if level_filter:
        if level_filter == 'primary':
            fast_swaps = fast_swaps.filter(level__name__icontains='Primary')
        elif level_filter == 'secondary':
            fast_swaps = fast_swaps.filter(level__name__icontains='Secondary')
    
    # Apply location filters
    if county_id:
        fast_swaps = fast_swaps.filter(current_county_id=county_id)
    if constituency_id:
        fast_swaps = fast_swaps.filter(current_constituency_id=constituency_id)
    if ward_id:
        fast_swaps = fast_swaps.filter(current_ward_id=ward_id)
    
    # Get all counties for the filter dropdown
    counties = Counties.objects.all().order_by('name')
    
    # Get all levels for the filter dropdown
    levels = Level.objects.all().order_by('name')
    
    # Get constituencies and wards if filters are applied
    constituencies = Constituencies.objects.none()
    wards = Wards.objects.none()
    
    if county_id:
        constituencies = Constituencies.objects.filter(county_id=county_id).order_by('name')
    if constituency_id:
        wards = Wards.objects.filter(constituency_id=constituency_id).order_by('name')
    
    # Get bookmarked FastSwap IDs for the current user (use list for template compatibility)
    bookmarked_ids = []
    if request.user.is_authenticated:
        bookmarked_ids = list(Bookmark.objects.filter(
            user=request.user,
            bookmark_type='fastswap'
        ).values_list('fast_swap_id', flat=True))
    
    return render(request, 'home/fast_swap_list.html', {
        'fast_swaps': fast_swaps,
        'title': 'FastSwap Entries',
        'counties': counties,
        'constituencies': constituencies,
        'wards': wards,
        'levels': levels,
        'selected_level': level_filter,
        'selected_county': county_id,
        'selected_constituency': constituency_id,
        'selected_ward': ward_id,
        'bookmarked_ids': bookmarked_ids,
    })


def swap_preferences(request):
    """
    View to handle user's swap preferences.
    Users can set their preferred location for swaps.
    """
    # Get or create the user's swap preferences
    preference, created = SwapPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = SwapPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            preference = form.save(commit=False)
            preference.user = request.user
            preference.save()
            messages.success(request, 'Your swap preferences have been updated successfully!')
            return redirect('home:swap_preferences')
    else:
        form = SwapPreferenceForm(instance=preference)
    
    # Get all counties for the template
    counties = Counties.objects.all().order_by('name')
    
    # Get selected values for form repopulation
    selected_county = preference.desired_county.id if preference.desired_county else None
    selected_constituency = preference.desired_constituency.id if preference.desired_constituency else None
    
    # Get constituencies and wards based on selected values
    constituencies = Constituencies.objects.none()
    if selected_county:
        constituencies = Constituencies.objects.filter(county_id=selected_county).order_by('name')
    
    wards = Wards.objects.none()
    if selected_constituency:
        wards = Wards.objects.filter(constituency_id=selected_constituency).order_by('name')
    
    return render(request, 'home/swap_preferences.html', {
        'form': form,
        'counties': counties,
        'constituencies': constituencies,
        'wards': wards,
        'selected_county': selected_county,
        'selected_constituency': selected_constituency,
        'selected_ward': preference.desired_ward.id if preference.desired_ward else None,
        'open_to_all': preference.open_to_all,
        'is_hardship': preference.is_hardship,
    })


@login_required
def toggle_swap_bookmark(request, swap_id):
    """
    Toggle bookmark for a regular swap.
    Returns JSON response for AJAX calls.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    swap = get_object_or_404(Swaps, id=swap_id)
    
    # Check if bookmark already exists
    existing_bookmark = Bookmark.objects.filter(
        user=request.user,
        swap=swap,
        bookmark_type='swap'
    ).first()
    
    if existing_bookmark:
        # Remove bookmark
        existing_bookmark.delete()
        return JsonResponse({
            'success': True,
            'action': 'removed',
            'message': 'Swap removed from wishlist'
        })
    else:
        # Create bookmark
        Bookmark.objects.create(
            user=request.user,
            swap=swap,
            bookmark_type='swap'
        )
        return JsonResponse({
            'success': True,
            'action': 'added',
            'message': 'Swap added to wishlist'
        })


@login_required
def toggle_fastswap_bookmark(request, fastswap_id):
    """
    Toggle bookmark for a FastSwap.
    Returns JSON response for AJAX calls.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    fast_swap = get_object_or_404(FastSwap, id=fastswap_id)
    
    # Check if bookmark already exists
    existing_bookmark = Bookmark.objects.filter(
        user=request.user,
        fast_swap=fast_swap,
        bookmark_type='fastswap'
    ).first()
    
    if existing_bookmark:
        # Remove bookmark
        existing_bookmark.delete()
        return JsonResponse({
            'success': True,
            'action': 'removed',
            'message': 'FastSwap removed from wishlist'
        })
    else:
        # Create bookmark
        Bookmark.objects.create(
            user=request.user,
            fast_swap=fast_swap,
            bookmark_type='fastswap'
        )
        return JsonResponse({
            'success': True,
            'action': 'added',
            'message': 'FastSwap added to wishlist'
        })


@login_required
def my_bookmarks(request):
    """
    View to display all bookmarked swaps and fast swaps for the current user.
    """
    # Get filter parameter
    filter_type = request.GET.get('type', 'all')
    
    # Get all bookmarks for the user
    bookmarks = Bookmark.objects.filter(user=request.user).select_related(
        'swap__user__profile__school__ward__constituency__county',
        'swap__county',
        'swap__constituency', 
        'swap__ward',
        'fast_swap__current_county',
        'fast_swap__current_constituency',
        'fast_swap__current_ward',
        'fast_swap__most_preferred',
        'fast_swap__level'
    ).prefetch_related(
        'fast_swap__acceptable_county',
        'fast_swap__subjects'
    )
    
    # Apply filter
    if filter_type == 'swap':
        bookmarks = bookmarks.filter(bookmark_type='swap')
    elif filter_type == 'fastswap':
        bookmarks = bookmarks.filter(bookmark_type='fastswap')
    
    # Get user subjects for matching
    user_subjects = set()
    if request.user.is_authenticated:
        user_subjects = set(MySubject.objects.filter(user=request.user).values_list('subject__id', flat=True))
    
    # Prepare bookmark data with additional info
    bookmark_data = []
    for bookmark in bookmarks:
        if bookmark.bookmark_type == 'swap' and bookmark.swap:
            swap = bookmark.swap
            user_profile = getattr(swap.user, 'profile', None)
            school = getattr(user_profile, 'school', None)
            
            # Get swap creator's subjects
            swap_user_subjects = list(MySubject.objects.filter(
                user=swap.user
            ).values_list('subject__name', flat=True))
            
            bookmark_data.append({
                'bookmark': bookmark,
                'type': 'swap',
                'item': swap,
                'user_school': school,
                'user_subjects': swap_user_subjects[:4],
                'level': getattr(user_profile, 'level', None) if user_profile else None,
            })
        elif bookmark.bookmark_type == 'fastswap' and bookmark.fast_swap:
            fast_swap = bookmark.fast_swap
            bookmark_data.append({
                'bookmark': bookmark,
                'type': 'fastswap',
                'item': fast_swap,
                'subjects': list(fast_swap.subjects.all()[:4]),
            })
    
    # Count by type
    swap_count = Bookmark.objects.filter(user=request.user, bookmark_type='swap').count()
    fastswap_count = Bookmark.objects.filter(user=request.user, bookmark_type='fastswap').count()
    
    context = {
        'bookmark_data': bookmark_data,
        'filter_type': filter_type,
        'swap_count': swap_count,
        'fastswap_count': fastswap_count,
        'total_count': swap_count + fastswap_count,
        'title': 'My Wishlist',
    }
    
    return render(request, 'home/my_bookmarks.html', context)

