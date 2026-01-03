from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from home.models import MySubject, Subject, SwapPreference, Schools
from home.matching import find_matches
from .models import MyUser

@staff_member_required
def user_management(request):
    # Get all users with their related data
    users = MyUser.objects.prefetch_related(
        'profile__school__level',
        'profile__school__ward__constituency__county',
        'swappreference',
        'mysubject_set__subject'
    ).order_by('-date_joined')

    # Prepare user data for the template
    user_data = []
    for user in users:
        # Build full name from profile if available
        full_name = 'No Name'
        if hasattr(user, 'profile') and user.profile:
            name_parts = []
            if user.profile.first_name:
                name_parts.append(user.profile.first_name)
            if user.profile.surname:
                name_parts.append(user.profile.surname)
            if user.profile.last_name and not user.profile.surname:  # Only use last_name if surname isn't set
                name_parts.append(user.profile.last_name)
            if name_parts:
                full_name = ' '.join(name_parts)
        
        user_dict = {
            'id': user.id,
            'email': user.email,
            'full_name': full_name,
            'is_active': user.is_active,
            'date_joined': user.date_joined,
            'phone': user.profile.phone if hasattr(user, 'profile') and user.profile.phone else '-',
            'school': None,
            'triangle_swaps': 0,
            'potential_matches': 0
        }

        # Add school info if available
        if hasattr(user, 'profile') and hasattr(user.profile, 'school') and user.profile.school:
            school = user.profile.school
            user_dict['school'] = {
                'name': school.name,
                'ward': school.ward.name if school.ward else 'N/A',
                'constituency': school.ward.constituency.name if school.ward and school.ward.constituency else 'N/A',
                'county': school.ward.constituency.county.name if school.ward and school.ward.constituency and school.ward.constituency.county else 'N/A',
                'level': school.level.name if hasattr(school, 'level') and school.level else 'N/A'
            }

        # Calculate triangle swaps
        try:
            if hasattr(user, 'profile') and user.profile.school and hasattr(user.profile.school, 'level') and hasattr(user, 'swappreference'):
                from home.triangle_swap_utils import find_triangle_swaps_primary, find_triangle_swaps_secondary
                from home.models import Level
                
                user_level = user.profile.school.level
                is_secondary = 'secondary' in user_level.name.lower() or 'high' in user_level.name.lower()
                
                # Get all teachers at the same level
                teachers = MyUser.objects.filter(
                    is_active=True,
                    role='Teacher',
                    profile__isnull=False,
                    profile__school__isnull=False,
                    profile__school__level=user_level,
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
                
                # Count triangles that include this user
                triangle_count = sum(1 for triangle in all_triangles if user.id in [t.id for t in triangle])
                user_dict['triangle_swaps'] = triangle_count
        except Exception as e:
            print(f"Error calculating triangle swaps for user {user.id}: {str(e)}")
            user_dict['triangle_swaps'] = 0

        # Calculate potential matches using the central logic
        try:
            # use find_matches to ensure consistency with dashboard and individual view
            user_dict['potential_matches'] = find_matches(user).count()
        except Exception as e:
            print(f"Error calculating matches for user {user.id}: {str(e)}")
            user_dict['potential_matches'] = 0

        user_data.append(user_dict)

    context = {
        'title': 'User Management',
        'users': user_data,
        'total_users': len(user_data),
        'active_users': len([u for u in user_data if u['is_active']])
    }
    
    return render(request, 'users/admin/user_management.html', context)

@staff_member_required
def user_potential_matches(request, user_id):
    # Get the user and their profile
    user = get_object_or_404(MyUser.objects.prefetch_related(
        'profile__school__level',
        'profile__school__ward__constituency__county',
        'swappreference',
        'mysubject_set__subject'
    ), id=user_id)
    
    # Build full name from profile if available
    full_name = 'No Name'
    if hasattr(user, 'profile') and user.profile:
        name_parts = []
        if user.profile.first_name:
            name_parts.append(user.profile.first_name)
        if user.profile.surname:
            name_parts.append(user.profile.surname)
        elif user.profile.last_name:  # Only use last_name if surname isn't set
            name_parts.append(user.profile.last_name)
        if name_parts:
            full_name = ' '.join(name_parts)
    
    # Prepare user data
    user_data = {
        'id': user.id,
        'email': user.email,
        'full_name': full_name,
        'phone': user.profile.phone if hasattr(user, 'profile') and user.profile.phone else '-',
        'tsc_number': user.tsc_number or 'Not provided',
        'id_number': user.id_number or 'Not provided',
        'school': None,
        'subjects': [],
        'preferences': {}
    }

    # Add school info if available
    if hasattr(user, 'profile') and hasattr(user.profile, 'school') and user.profile.school:
        school = user.profile.school
        user_data['school'] = {
            'name': school.name,
            'ward': school.ward.name if school.ward else 'N/A',
            'constituency': school.ward.constituency.name if school.ward and school.ward.constituency else 'N/A',
            'county': school.ward.constituency.county.name if school.ward and school.ward.constituency and school.ward.constituency.county else 'N/A',
            'level': school.level.name if hasattr(school, 'level') and school.level else 'N/A'
        }

    # Add subjects - using the same approach as in profile_view
    my_subjects = MySubject.objects.filter(user=user).first()
    if my_subjects:
        user_data['subjects'] = [s.name for s in my_subjects.subject.all()]
    else:
        user_data['subjects'] = []
    print(f"Debug - User {user.id} subjects: {user_data['subjects']}")

    # Add preferences
    if hasattr(user, 'swappreference'):
        prefs = user.swappreference
        user_data['preferences'] = {
            'desired_county': prefs.desired_county.name if prefs.desired_county else 'Any',
            'desired_constituency': prefs.desired_constituency.name if prefs.desired_constituency else 'Any',
            'open_to_all': ", ".join([c.name for c in prefs.open_to_all.all()]) if prefs.open_to_all.exists() else 'None',
            'is_hardship': prefs.is_hardship
        }

    # Find potential matches using the central matching logic
    potential_matches = []
    
    try:
        matches = find_matches(user)
        
        # Prepare match data for display
        for match in matches:
            # Build full name from profile if available
            full_name = 'No Name'
            name_parts = []
            if hasattr(match, 'profile') and match.profile:
                if match.profile.first_name:
                    name_parts.append(match.profile.first_name)
                if match.profile.surname:
                    name_parts.append(match.profile.surname)
                elif match.profile.last_name:  # Only use last_name if surname isn't set
                    name_parts.append(match.profile.last_name)
            
            if name_parts:
                full_name = ' '.join(name_parts)
            
            match_data = {
                'id': match.id,
                'email': match.email,
                'full_name': full_name,
                'phone': match.profile.phone if hasattr(match, 'profile') and match.profile.phone else '-',
                'school': None,
                'subjects': []
            }
            
            # Add school info
            if hasattr(match, 'profile') and hasattr(match.profile, 'school') and match.profile.school:
                school = match.profile.school
                match_data['school'] = {
                    'name': school.name,
                    'ward': school.ward.name if school.ward else 'N/A',
                    'constituency': school.ward.constituency.name if school.ward and school.ward.constituency else 'N/A',
                    'county': school.ward.constituency.county.name if school.ward and school.ward.constituency and school.ward.constituency.county else 'N/A',
                    'level': school.level.name if hasattr(school, 'level') and school.level else 'N/A'
                }
            
            # Add subjects
            if hasattr(match, 'mysubject_set'):
                # Get all MySubject instances for this user
                my_subjects = match.mysubject_set.all()
                subjects = []
                for my_subject in my_subjects:
                    # Get all subjects from the many-to-many relationship
                    subjects.extend([s.name for s in my_subject.subject.all()])
                match_data['subjects'] = subjects
            else:
                match_data['subjects'] = []
            
            potential_matches.append(match_data)
            
    except Exception as e:
        print(f"Error finding matches for {user.email}: {e}")
    # Find triangle matches
    triangle_matches = []
    try:
        from home.triangle_swap_utils import find_triangle_swaps_primary, find_triangle_swaps_secondary
        
        if hasattr(user, 'profile') and user.profile.school and hasattr(user.profile.school, 'level') and hasattr(user, 'swappreference'):
            user_level = user.profile.school.level
            is_secondary = 'secondary' in user_level.name.lower() or 'high' in user_level.name.lower()
            
            # Get all teachers at the same level (needed for triangle search)
            # This replicates logic from user_management view
            teachers = MyUser.objects.filter(
                is_active=True,
                role='Teacher',
                profile__isnull=False,
                profile__school__isnull=False,
                profile__school__level=user_level,
                swappreference__isnull=False
            ).select_related(
                'profile__school__ward__constituency__county',
                'swappreference__desired_county',
                'profile__school__level'
            ).prefetch_related(
                'swappreference__open_to_all',
                'mysubject_set__subject'
            ).distinct()
            
            # Find all triangles
            if is_secondary:
                all_triangles = find_triangle_swaps_secondary(teachers)
            else:
                all_triangles = find_triangle_swaps_primary(teachers)
            
            # Filter for triangles involving this user
            for triangle in all_triangles:
                teacher_a, teacher_b, teacher_c = triangle
                
                # Check if user is in this triangle
                user_in_triangle = False
                teachers_ordered = [] # Will order as User -> Next -> Next
                
                if teacher_a.id == user.id:
                    user_in_triangle = True
                    teachers_ordered = [teacher_b, teacher_c] # The two OTHER teachers
                elif teacher_b.id == user.id:
                    user_in_triangle = True
                    teachers_ordered = [teacher_c, teacher_a]
                elif teacher_c.id == user.id:
                    user_in_triangle = True
                    teachers_ordered = [teacher_a, teacher_b]
                
                if user_in_triangle:
                    # Process these 2 matches for display
                    triangle_data = []
                    for match in teachers_ordered:
                        match_info = {
                            'id': match.id,
                            'full_name': 'Unknown',
                            'email': match.email,
                            'phone': '-',
                            'school': None,
                            'subjects': []
                        }
                        
                        # Name
                        if hasattr(match, 'profile') and match.profile:
                            name_parts = []
                            if match.profile.first_name: name_parts.append(match.profile.first_name)
                            if match.profile.surname: name_parts.append(match.profile.surname)
                            elif match.profile.last_name: name_parts.append(match.profile.last_name)
                            if name_parts: match_info['full_name'] = ' '.join(name_parts)
                            
                            if match.profile.phone: match_info['phone'] = match.profile.phone
                            
                            if match.profile.school:
                                school = match.profile.school
                                match_info['school'] = {
                                    'name': school.name,
                                    'county': school.ward.constituency.county.name if school.ward and school.ward.constituency and school.ward.constituency.county else 'N/A'
                                }
                        
                        # Subjects
                        if hasattr(match, 'mysubject_set'):
                            subjects = []
                            for ms in match.mysubject_set.all():
                                subjects.extend([s.name for s in ms.subject.all()])
                            match_info['subjects'] = subjects
                            
                        triangle_data.append(match_info)
                    
                    triangle_matches.append(triangle_data)

    except Exception as e:
        print(f"Error finding triangle matches for {user.email}: {e}")


    context = {
        'title': f'Potential Matches for {user_data["full_name"]}',
        'user': user_data,
        'potential_matches': potential_matches,
        'triangle_matches': triangle_matches,
        'has_matches': len(potential_matches) > 0 or len(triangle_matches) > 0,
        'has_mutual_matches': len(potential_matches) > 0,
        'has_triangle_matches': len(triangle_matches) > 0
    }
    
    return render(request, 'users/admin/user_potential_matches.html', context)
