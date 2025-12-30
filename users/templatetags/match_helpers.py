from django import template
from django.db.models import Q
from django.template.loader import render_to_string

register = template.Library()


def get_primary_teacher_matches(user):
    """
    Get potential matches for primary level teachers only.
    Returns a tuple of (perfect_matches, partial_matches)
    """
    from users.models import MyUser
    
    if not hasattr(user, 'profile') or not hasattr(user, 'swappreference'):
        return [], []
    
    # Check if user's school is primary level
    is_primary = user.profile.school and hasattr(user.profile.school, 'level') and \
                 ('primary' in user.profile.school.level.name.lower())
    
    if not is_primary:
        return [], []
    
    # Get user's current location and preferences
    user_county = user.profile.school.ward.constituency.county if hasattr(user.profile.school, 'ward') else None
    user_pref = user.swappreference
    
    # Base query for potential primary level matches
    matches = MyUser.objects.filter(
        ~Q(id=user.id),  # Exclude self
        is_active=True,
        profile__isnull=False,
        profile__school__isnull=False,
        profile__school__level__name__icontains='primary',
        swappreference__isnull=False
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county',
        'profile__school__level'
    ).prefetch_related(
        'swappreference__open_to_all'
    ).distinct()
    
    perfect_matches = []
    partial_matches = []
    
    for match in matches:
        try:
            match_county = match.profile.school.ward.constituency.county if hasattr(match.profile.school, 'ward') else None
            match_pref = match.swappreference
            
            # Check condition 1: User's current location in match's preferences
            condition2 = False
            if user_county:
                if match_pref.desired_county == user_county or \
                   user_county in match_pref.open_to_all.all():
                    condition2 = True
            
            # Check condition 2: Match's current location in user's preferences
            condition3 = False
            if match_county:
                if user_pref.desired_county == match_county or \
                   match_county in user_pref.open_to_all.all():
                    condition3 = True
            
            # Classify the match
            if condition2 and condition3:
                perfect_matches.append(match)
            elif condition2 or condition3:
                partial_matches.append(match)
                
        except Exception as e:
            continue
    
    return perfect_matches, partial_matches


def get_secondary_teacher_matches(user):
    """
    Get potential matches for secondary/high school teachers only.
    Returns a tuple of (perfect_matches, partial_matches)
    """
    from users.models import MyUser
    
    if not hasattr(user, 'profile') or not hasattr(user, 'swappreference') or not hasattr(user, 'mysubject_set'):
        return [], []
    
    # Check if user's school is secondary/high school level
    is_secondary = user.profile.school and hasattr(user.profile.school, 'level') and \
                  ('secondary' in user.profile.school.level.name.lower() or 
                   'high' in user.profile.school.level.name.lower())
    
    if not is_secondary:
        return [], []
    
    # Get user's current location, preferences, and subjects
    user_county = user.profile.school.ward.constituency.county if hasattr(user.profile.school, 'ward') else None
    user_pref = user.swappreference
    user_subjects = set(user.mysubject_set.values_list('subject__id', flat=True))
    
    # Base query for potential secondary level matches
    matches = MyUser.objects.filter(
        ~Q(id=user.id),  # Exclude self
        is_active=True,
        profile__isnull=False,
        profile__school__isnull=False,
        profile__school__level__name__icontains='secondary',
        swappreference__isnull=False,
        mysubject__isnull=False
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county',
        'profile__school__level'
    ).prefetch_related(
        'swappreference__open_to_all',
        'mysubject_set__subject'
    ).distinct()
    
    perfect_matches = []
    partial_matches = []
    
    for match in matches:
        try:
            match_county = match.profile.school.ward.constituency.county if hasattr(match.profile.school, 'ward') else None
            match_pref = match.swappreference
            
            # Get match's subjects
            match_subjects = set(match.mysubject_set.values_list('subject__id', flat=True))
            
            # Check condition 1: Shared subjects
            shared_subjects = user_subjects & match_subjects
            condition1 = bool(shared_subjects)
            
            if not condition1:
                continue  # Skip if no shared subjects
            
            # Check condition 2: User's current location in match's preferences
            condition2 = False
            if user_county:
                if match_pref.desired_county == user_county or \
                   user_county in match_pref.open_to_all.all():
                    condition2 = True
            
            # Check condition 3: Match's current location in user's preferences
            condition3 = False
            if match_county:
                if user_pref.desired_county == match_county or \
                   match_county in user_pref.open_to_all.all():
                    condition3 = True
            
            # Classify the match
            if condition1 and condition2 and condition3:
                perfect_matches.append(match)
            elif condition1 and (condition2 or condition3):
                partial_matches.append(match)
                
        except Exception as e:
            continue
    
    return perfect_matches, partial_matches




@register.inclusion_tag('users/partials/primary_matches_section.html', takes_context=True)
def get_user_primary_match(context):
    """
    Template tag to get primary level teacher matches for the current user.
    Usage: {% get_user_primary_match %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'perfect_matches': [], 'partial_matches': []}
    
    perfect_matches, partial_matches = get_primary_teacher_matches(request.user)
    return {
        'perfect_matches': perfect_matches,
        'partial_matches': partial_matches,
        'profile_complete': context.get('profile_complete', False),
        'completion_percentage': context.get('completion_percentage', 0)
    }


@register.inclusion_tag('users/partials/secondary_matches_section.html', takes_context=True)
def get_user_secondary_match(context):
    """
    Template tag to get secondary/high school teacher matches for the current user.
    Usage: {% get_user_secondary_match %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'perfect_matches': [], 'partial_matches': []}
    
    perfect_matches, partial_matches = get_secondary_teacher_matches(request.user)
    return {
        'perfect_matches': perfect_matches,
        'partial_matches': partial_matches,
        'profile_complete': context.get('profile_complete', False),
        'completion_percentage': context.get('completion_percentage', 0)
    }
