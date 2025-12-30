from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from home.models import MySubject, Subject, SwapPreference, Schools
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
            'subjects': [],
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

        # Add subjects
        if hasattr(user, 'mysubject_set'):
            user_dict['subjects'] = [ms.subject.name for ms in user.mysubject_set.all()]

        # Calculate potential matches using the same logic as the dashboard
        try:
            if hasattr(user, 'profile') and user.profile.school and hasattr(user.profile.school, 'level'):
                # Only count matches if user has completed profile and preferences
                if hasattr(user, 'swappreference'):
                    # Get user's county from school
                    user_county = user.profile.school.ward.constituency.county if hasattr(user.profile.school, 'ward') and user.profile.school.ward else None
                    
                    if user_county:
                        # Base query for potential matches
                        potential_matches = MyUser.objects.filter(
                            ~Q(id=user.id),
                            is_active=True,
                            profile__isnull=False,
                            profile__school__isnull=False,
                            swappreference__isnull=False
                        )
                        
                        # Filter by swap preferences (county match or open to all)
                        potential_matches = potential_matches.filter(
                            Q(swappreference__desired_county=user_county) |
                            Q(swappreference__open_to_all=user_county)
                        )
                        
                        # For secondary/high school, check subject matches
                        is_secondary = 'secondary' in user.profile.school.level.name.lower() or 'high' in user.profile.school.level.name.lower()
                        if is_secondary and hasattr(user, 'mysubject_set'):
                            user_subjects = set(MySubject.objects.filter(
                                user=user
                            ).values_list('subject__id', flat=True))
                            
                            if user_subjects:
                                # Only include users who teach at least one of the same subjects
                                potential_matches = potential_matches.filter(
                                    id__in=MySubject.objects.filter(
                                        subject__in=user_subjects
                                    ).values('user')
                                ).distinct()
                        
                        user_dict['potential_matches'] = potential_matches.count()
                        
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

    # Find potential matches using the same logic as the dashboard
    potential_matches = []
    if hasattr(user, 'profile') and user.profile.school and hasattr(user.profile.school, 'level'):
        # Only show matches if user has completed profile and preferences
        if hasattr(user, 'swappreference'):
            # Get user's county from school
            user_county = user.profile.school.ward.constituency.county if hasattr(user.profile.school, 'ward') and user.profile.school.ward else None
            
            if user_county:
                # Base query for potential matches
                matches = MyUser.objects.filter(
                    ~Q(id=user.id),
                    is_active=True,
                    profile__isnull=False,
                    profile__school__isnull=False,
                    swappreference__isnull=False
                ).prefetch_related(
                    'profile__school__level',
                    'profile__school__ward__constituency__county',
                    'mysubject_set__subject',
                    'swappreference'
                )
                
                # Filter by swap preferences (county match or open to all)
                matches = matches.filter(
                    Q(swappreference__desired_county=user_county) |
                    Q(swappreference__open_to_all=user_county)
                )
                
                # For secondary/high school, check subject matches
                is_secondary = 'secondary' in user.profile.school.level.name.lower() or 'high' in user.profile.school.level.name.lower()
                if is_secondary and hasattr(user, 'mysubject_set'):
                    user_subjects = set(MySubject.objects.filter(
                        user=user
                    ).values_list('subject__id', flat=True))
                    
                    if user_subjects:
                        # Only include users who teach at least one of the same subjects
                        matches = matches.filter(
                            id__in=MySubject.objects.filter(
                                subject__in=user_subjects
                            ).values('user')
                        )
                
                # Prepare match data for display
                for match in matches.distinct():
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
                        print(f"Match {match.id} subjects: {subjects}")
                    else:
                        match_data['subjects'] = []
                        print(f"Match {match.id} has no mysubject_set")
                    
                    potential_matches.append(match_data)
                    print(f"Added match data: {match_data}")  # Debug output

    context = {
        'title': f'Potential Matches for {user_data["full_name"]}',
        'user': user_data,
        'potential_matches': potential_matches,
        'has_matches': len(potential_matches) > 0
    }
    
    return render(request, 'users/admin/user_potential_matches.html', context)
