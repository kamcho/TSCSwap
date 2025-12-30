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
    import logging
    logger = logging.getLogger(__name__)
    
    # Debug: Log initial checks
    logger.debug(f"=== Starting match process for user: {user.email} ===")
    
    # Check required attributes
    if not hasattr(user, 'profile') or not user.profile:
        logger.debug("No profile found for user")
        return [], []
        
    if not hasattr(user, 'swappreference') or not user.swappreference:
        logger.debug("No swap preferences found for user")
        return [], []
        
    if not hasattr(user, 'mysubject_set'):
        logger.debug("No subject set found for user")
        return []
    
    # Check if user's school is secondary/high school level
    is_secondary = False
    if user.profile.school and hasattr(user.profile.school, 'level') and user.profile.school.level:
        level_name = user.profile.school.level.name.lower()
        is_secondary = 'secondary' in level_name or 'high' in level_name
        logger.debug(f"User school level: {user.profile.school.level.name}, is_secondary: {is_secondary}")
    else:
        logger.debug("User has no school level information")
        return [], []
    
    # Get user's current location, preferences, and subjects
    user_county = None
    if hasattr(user.profile.school, 'ward') and user.profile.school.ward:
        user_county = user.profile.school.ward.constituency.county if user.profile.school.ward.constituency else None
        logger.debug(f"User county: {user_county}" if user_county else "User county not found")
    
    user_pref = user.swappreference
    user_subjects = set(user.mysubject_set.values_list('subject__id', flat=True))
    logger.debug(f"User subjects: {user_subjects}")
    logger.debug(f"User preferences - desired_county: {getattr(user_pref, 'desired_county', None)}, open_to_all: {user_pref.open_to_all.exists() if hasattr(user_pref, 'open_to_all') else 'N/A'}")
    
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
    
    logger.debug(f"Found {matches.count()} potential matches to evaluate")
    
    for match in matches:
        try:
            logger.debug(f"\nEvaluating match: {match.email}")
            
            # Get match's county
            match_county = None
            if hasattr(match.profile.school, 'ward') and match.profile.school.ward:
                if hasattr(match.profile.school.ward, 'constituency') and match.profile.school.ward.constituency:
                    match_county = match.profile.school.ward.constituency.county
            
            logger.debug(f"Match county: {match_county}" if match_county else "No county found for match")
            
            match_pref = match.swappreference
            logger.debug(f"Match preferences - desired_county: {getattr(match_pref, 'desired_county', None)}, open_to_all: {match_pref.open_to_all.exists() if hasattr(match_pref, 'open_to_all') else 'N/A'}")
            
            # Get match's subjects
            match_subjects = set(match.mysubject_set.values_list('subject__id', flat=True))
            logger.debug(f"Match subjects: {match_subjects}")
            
            # Check condition 1: Shared subjects
            shared_subjects = user_subjects & match_subjects
            condition1 = bool(shared_subjects)
            
            if not condition1:
                logger.debug("No shared subjects - skipping")
                continue
            
            logger.debug(f"Shared subjects: {shared_subjects}")
            
            # Check condition 2: User's current location in match's preferences
            condition2 = False
            if user_county:
                if hasattr(match_pref, 'desired_county') and match_pref.desired_county == user_county:
                    condition2 = True
                    logger.debug("Condition 2: User's county matches match's desired county")
                elif user_county in match_pref.open_to_all.all():
                    condition2 = True
                    logger.debug("Condition 2: User's county is in match's open_to_all")
            else:
                logger.debug("Condition 2: User county not available")
            
            # Check condition 3: Match's current location in user's preferences
            condition3 = False
            if match_county:
                if hasattr(user_pref, 'desired_county') and user_pref.desired_county == match_county:
                    condition3 = True
                    logger.debug("Condition 3: Match's county matches user's desired county")
                elif match_county in user_pref.open_to_all.all():
                    condition3 = True
                    logger.debug("Condition 3: Match's county is in user's open_to_all")
            else:
                logger.debug("Condition 3: Match county not available")
            
            # Classify the match
            if condition1 and condition2 and condition3:
                perfect_matches.append(match)
                logger.debug("Added to PERFECT matches")
            elif condition1 and (condition2 or condition3):
                partial_matches.append(match)
                logger.debug("Added to PARTIAL matches")
            else:
                logger.debug("No match conditions met")
                
        except Exception as e:
            logger.error(f"Error processing match {match.email}: {str(e)}", exc_info=True)
            continue
            
    logger.debug(f"Final results - Perfect: {len(perfect_matches)}, Partial: {len(partial_matches)}")
    
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
