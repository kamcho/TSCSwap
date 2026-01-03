from django.db.models import Q
from users.models import MyUser
from .models import MySubject

def find_matches(user):
    """
    Finds matching teachers for a swap based on:
    1. Level (Primary vs Secondary)
    2. Location Preferences (Two-way match)
    3. Subject Preferences (Exact match for Secondary)
    """
    # Defensive checks
    if not hasattr(user, 'profile') or not user.profile:
        return MyUser.objects.none()
    
    if not user.profile.school:
        return MyUser.objects.none()
    
    try:
        user_prefs = user.swappreference
    except:
        return MyUser.objects.none()

    # User's current details
    user_school = user.profile.school
    user_level = user_school.level
    
    # Check ward/constituency/county exist
    if not user_school.ward:
        return MyUser.objects.none()
    if not user_school.ward.constituency:
        return MyUser.objects.none()
    if not user_school.ward.constituency.county:
        return MyUser.objects.none()
    
    user_county = user_school.ward.constituency.county
    
    # User's preferences
    user_desired_county = user_prefs.desired_county
    user_open_to_all = user_prefs.open_to_all.all()
    
    # User must want to go SOMEWHERE
    if not user_desired_county and not user_open_to_all.exists():
        return MyUser.objects.none()
    
    # 1. Base Filter: Active teachers, same level, with complete data
    potential_matches = MyUser.objects.filter(
        ~Q(id=user.id),
        is_active=True,
        profile__isnull=False,
        profile__school__isnull=False,
        profile__school__level=user_level,
        profile__school__ward__isnull=False,
        profile__school__ward__constituency__isnull=False,
        profile__school__ward__constituency__county__isnull=False,
        swappreference__isnull=False
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county',
        'profile__school__level'
    ).prefetch_related(
        'swappreference__open_to_all'
    )

    # 2. Location Match (Two-Way)
    
    # Condition A: They want to come to MY county
    # Their desired_county == My current county OR My current county in Their open_to_all
    they_want_me = Q(swappreference__desired_county=user_county) | Q(swappreference__open_to_all=user_county)
    
    # Condition B: I want to go to THEIR county
    # Build list of counties I'm willing to go to
    my_target_counties = []
    if user_desired_county:
        my_target_counties.append(user_desired_county.id)
    if user_open_to_all.exists():
        my_target_counties.extend(list(user_open_to_all.values_list('id', flat=True)))
        
    if not my_target_counties:
        return MyUser.objects.none()
        
    i_want_them = Q(profile__school__ward__constituency__county__id__in=my_target_counties)
    
    potential_matches = potential_matches.filter(they_want_me & i_want_them)

    # 3. Secondary Subject Match (Exact Match)
    is_secondary = 'secondary' in user_level.name.lower() or 'high' in user_level.name.lower()
    
    if is_secondary:
        # Get my subjects IDs
        my_subject_ids = set(MySubject.objects.filter(user=user).values_list('subject__id', flat=True))
        
        if not my_subject_ids:
            # Secondary teacher with no subjects - can't match
            return MyUser.objects.none()
        
        matches_with_correct_subjects = []
        for match in potential_matches:
            match_subject_ids = set(MySubject.objects.filter(user=match).values_list('subject__id', flat=True))
            
            if my_subject_ids == match_subject_ids:
                matches_with_correct_subjects.append(match.id)
                
        potential_matches = potential_matches.filter(id__in=matches_with_correct_subjects)

    return potential_matches.distinct()
