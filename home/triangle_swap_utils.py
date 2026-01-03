"""
Triangle Swap Detection Utilities

Triangle swaps involve three teachers exchanging locations in a circular pattern:
- Teacher A (Location X) wants Location Y
- Teacher B (Location Y) wants Location Z  
- Teacher C (Location Z) wants Location X

This creates a circular match where all three get their desired locations.
"""

from django.db.models import Q
from home.models import Level, MySubject


def get_current_county(user):
    """Get the current county where a teacher is teaching."""
    if not hasattr(user, 'profile') or not user.profile:
        return None
    
    if not user.profile.school or not user.profile.school.ward:
        return None
    
    try:
        return user.profile.school.ward.constituency.county
    except:
        return None


def wants_county(user, target_county):
    """
    Check if a user wants to go to a specific county.
    Checks both desired_county and open_to_all fields.
    """
    if not hasattr(user, 'swappreference') or not user.swappreference:
        return False
    
    pref = user.swappreference
    
    # Check desired_county
    if pref.desired_county and pref.desired_county.id == target_county.id:
        return True
    
    # Check open_to_all (ManyToManyField)
    if pref.open_to_all.filter(id=target_county.id).exists():
        return True
    
    return False


def get_user_subjects(user):
    """Get set of subject IDs for a user."""
    try:
        my_subjects = MySubject.objects.filter(user=user).first()
        if my_subjects and my_subjects.subject.exists():
            return set(my_subjects.subject.values_list('id', flat=True))
    except:
        pass
    return set()


def have_same_subjects(user1, user2):
    """Check if two users have exactly the same set of subjects."""
    subjects1 = get_user_subjects(user1)
    subjects2 = get_user_subjects(user2)
    return subjects1 == subjects2



def find_triangle_swaps_primary(teachers_queryset):
    """
    Find triangle swaps for PRIMARY level teachers.
    Only checks location matching (no subject requirement).
    
    Returns list of tuples: [(teacher_a, teacher_b, teacher_c), ...]
    """
    from users.models import MyUser
    
    triangle_swaps = []
    teachers_list = list(teachers_queryset)
    
    # Create a map: county_id -> list of teachers in that county
    teachers_by_current_county = {}
    for teacher in teachers_list:
        current_county = get_current_county(teacher)
        if current_county:
            teachers_by_current_county.setdefault(current_county.id, []).append(teacher)
    
    # Try to find triangles
    processed_triangles = set()
    
    for teacher_a in teachers_list:
        county_a = get_current_county(teacher_a)
        if not county_a:
            continue
        
        # What county does Teacher A want?
        pref_a = teacher_a.swappreference
        if not pref_a:
            continue
        
        # Get counties Teacher A wants (desired_county + open_to_all)
        wanted_counties_a = set()
        if pref_a.desired_county:
            wanted_counties_a.add(pref_a.desired_county.id)
        wanted_counties_a.update(pref_a.open_to_all.values_list('id', flat=True))
        
        if not wanted_counties_a:
            continue
        
        # For each county Teacher A wants, find teachers there
        for wanted_county_id in wanted_counties_a:
            teachers_in_wanted_county = teachers_by_current_county.get(wanted_county_id, [])
            
            for teacher_b in teachers_in_wanted_county:
                if teacher_b.id == teacher_a.id:
                    continue
                
                county_b = get_current_county(teacher_b)
                if not county_b:
                    continue
                
                # What county does Teacher B want?
                pref_b = teacher_b.swappreference
                if not pref_b:
                    continue
                
                wanted_counties_b = set()
                if pref_b.desired_county:
                    wanted_counties_b.add(pref_b.desired_county.id)
                wanted_counties_b.update(pref_b.open_to_all.values_list('id', flat=True))
                
                if not wanted_counties_b:
                    continue
                
                # For each county Teacher B wants, find teachers there
                for wanted_county_id_b in wanted_counties_b:
                    teachers_in_wanted_county_b = teachers_by_current_county.get(wanted_county_id_b, [])
                    
                    for teacher_c in teachers_in_wanted_county_b:
                        if teacher_c.id in [teacher_a.id, teacher_b.id]:
                            continue
                        
                        county_c = get_current_county(teacher_c)
                        if not county_c:
                            continue
                        
                        # Check if Teacher C wants Teacher A's current county
                        if wants_county(teacher_c, county_a):
                            # Found a triangle!
                            # Create a unique identifier for this triangle
                            triangle_ids = tuple(sorted([teacher_a.id, teacher_b.id, teacher_c.id]))
                            
                            if triangle_ids not in processed_triangles:
                                processed_triangles.add(triangle_ids)
                                triangle_swaps.append((teacher_a, teacher_b, teacher_c))
    
    return triangle_swaps


def find_triangle_swaps_secondary(teachers_queryset):
    """
    Find triangle swaps for SECONDARY level teachers.
    Find triangle swaps for SECONDARY level teachers.
    Checks BOTH location AND subject matching.
    All three teachers must have exactly the same subjects.
    
    Returns list of tuples: [(teacher_a, teacher_b, teacher_c), ...]
    """
    triangle_swaps = []
    teachers_list = list(teachers_queryset)
    
    # Create a map: county_id -> list of teachers in that county
    teachers_by_current_county = {}
    for teacher in teachers_list:
        current_county = get_current_county(teacher)
        if current_county:
            teachers_by_current_county.setdefault(current_county.id, []).append(teacher)
    
    # Try to find triangles
    processed_triangles = set()
    
    for teacher_a in teachers_list:
        county_a = get_current_county(teacher_a)
        if not county_a:
            continue
        
        # What county does Teacher A want?
        pref_a = teacher_a.swappreference
        if not pref_a:
            continue
        
        # Get counties Teacher A wants
        wanted_counties_a = set()
        if pref_a.desired_county:
            wanted_counties_a.add(pref_a.desired_county.id)
        wanted_counties_a.update(pref_a.open_to_all.values_list('id', flat=True))
        
        if not wanted_counties_a:
            continue
        
        # For each county Teacher A wants, find teachers there
        for wanted_county_id in wanted_counties_a:
            teachers_in_wanted_county = teachers_by_current_county.get(wanted_county_id, [])
            
            for teacher_b in teachers_in_wanted_county:
                if teacher_b.id == teacher_a.id:
                    continue
                
                # Check if Teacher A and Teacher B have same subjects
                if not have_same_subjects(teacher_a, teacher_b):
                    continue
                
                county_b = get_current_county(teacher_b)
                if not county_b:
                    continue
                
                # What county does Teacher B want?
                pref_b = teacher_b.swappreference
                if not pref_b:
                    continue
                
                wanted_counties_b = set()
                if pref_b.desired_county:
                    wanted_counties_b.add(pref_b.desired_county.id)
                wanted_counties_b.update(pref_b.open_to_all.values_list('id', flat=True))
                
                if not wanted_counties_b:
                    continue
                
                # For each county Teacher B wants, find teachers there
                for wanted_county_id_b in wanted_counties_b:
                    teachers_in_wanted_county_b = teachers_by_current_county.get(wanted_county_id_b, [])
                    
                    for teacher_c in teachers_in_wanted_county_b:
                        if teacher_c.id in [teacher_a.id, teacher_b.id]:
                            continue
                        
                        # Check if Teacher C has same subjects with A (Transitive property implies B is also same)
                        if not have_same_subjects(teacher_a, teacher_c):
                            continue
                        
                        county_c = get_current_county(teacher_c)
                        if not county_c:
                            continue
                        
                        # Check if Teacher C wants Teacher A's current county
                        if wants_county(teacher_c, county_a):
                            # Found a triangle!
                            triangle_ids = tuple(sorted([teacher_a.id, teacher_b.id, teacher_c.id]))
                            
                            if triangle_ids not in processed_triangles:
                                processed_triangles.add(triangle_ids)
                                triangle_swaps.append((teacher_a, teacher_b, teacher_c))
    
    return triangle_swaps




