from django import template
from django.db.models import Q

register = template.Library()

@register.filter
def is_profile_complete(user):
    """
    Check if a user's profile is 100% complete based on their teaching level.
    
    For Primary Level Teachers:
    - Must be linked to a school
    - Must have a level set on personal profile
    - Must have phone number and names
    - Must have swap preference set
    
    For Secondary Level Teachers:
    - Must be linked to a school
    - Must have a level set on personal profile
    - Must have at least 1 subject in MySubject
    - Must have swap preference set
    """
    # Basic checks for all users
    if not user or not hasattr(user, 'profile') or not user.profile:
        print('profile')
        return False
        
    # Check if user has a school
    if not hasattr(user.profile, 'school') or not user.profile.school:
        print('school')
        return False
        
    # Check if user has a level set
    if not hasattr(user.profile, 'level') or not user.profile.level:
        print('level')
        return False
        
    # Check if user has names and phone
    if not user.profile.first_name or not (user.profile.surname or user.profile.last_name) or not user.profile.phone:
        print('Missing name or phone in profile')
        return False
        
    # Check if user has swap preference
    if not hasattr(user, 'swappreference') or not user.swappreference:
        print('swappreference 1')
        return False
        
    # Check if user has set their preferences (either open_to_all or desired_county)
    if not (user.swappreference.open_to_all or user.swappreference.desired_county):
        print('preferences')
        return False
    
    # Additional checks for secondary level teachers
    is_secondary = user.profile.level.name.lower() in ['Secondary/High School', 'high school']
    
    if is_secondary:
        # Check if user has at least one subject
        if not hasattr(user, 'mysubject_set') or user.mysubject_set.count() == 0:
            print('subject')
            return False
    
    # All checks passed
    return True
