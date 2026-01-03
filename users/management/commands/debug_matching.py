from django.core.management.base import BaseCommand
from users.models import MyUser
import json


class Command(BaseCommand):
    help = 'Debug matching data for all users'

    def handle(self, *args, **options):
        users_data = []
        
        users = MyUser.objects.filter(
            is_active=True,
            role='Teacher'
        ).select_related(
            'profile__school__ward__constituency__county',
            'profile__school__level'
        ).prefetch_related(
            'mysubject_set__subject'
        )
        
        for user in users:
            # Basic info
            data = {
                'id': user.id,
                'email': user.email,
                'is_active': user.is_active,
            }
            
            # Profile & School
            try:
                if user.profile:
                    data['has_profile'] = True
                    data['school'] = str(user.profile.school.name) if user.profile.school else None
                    data['school_level'] = str(user.profile.school.level.name) if user.profile.school and user.profile.school.level else None
                    data['teacher_level'] = str(user.profile.level.name) if user.profile.level else None  # IMPORTANT: Teacher's actual level
                    
                    # Current location
                    if user.profile.school and user.profile.school.ward:
                        ward = user.profile.school.ward
                        if ward.constituency and ward.constituency.county:
                            data['current_county'] = str(ward.constituency.county.name)
                            data['current_county_id'] = ward.constituency.county.id
                        else:
                            data['current_county'] = None
                            data['current_county_id'] = None
                    else:
                        data['current_county'] = None
                        data['current_county_id'] = None
                else:
                    data['has_profile'] = False
                    data['school'] = None
                    data['school_level'] = None
                    data['teacher_level'] = None
                    data['current_county'] = None
                    data['current_county_id'] = None
            except Exception as e:
                data['has_profile'] = False
                data['school'] = None
                data['school_level'] = None
                data['teacher_level'] = None
                data['current_county'] = None
                data['profile_error'] = str(e)
            
            # Swap Preference
            try:
                pref = user.swappreference
                data['has_swappreference'] = True
                data['desired_county'] = str(pref.desired_county.name) if pref.desired_county else None
                data['desired_county_id'] = pref.desired_county.id if pref.desired_county else None
                # Handle open_to_all - could be boolean or M2M
                try:
                    data['open_to_all'] = bool(pref.open_to_all)
                except:
                    # If it's a M2M field, get the county names
                    try:
                        open_counties = list(pref.open_to_all.values_list('name', flat=True))
                        data['open_to_all_counties'] = open_counties
                        data['open_to_all'] = len(open_counties) > 0
                    except:
                        data['open_to_all'] = None
            except Exception as e:
                data['has_swappreference'] = False
                data['desired_county'] = None
                data['desired_county_id'] = None
                data['open_to_all'] = None
                data['pref_error'] = str(e)
            
            # Subjects (for secondary)
            try:
                subjects = list(user.mysubject_set.values_list('subject__name', flat=True))
                data['subjects'] = [str(s) for s in subjects] if subjects else []
                data['subject_count'] = len(subjects)
            except Exception as e:
                data['subjects'] = []
                data['subject_count'] = 0
                data['subjects_error'] = str(e)
            
            users_data.append(data)
        
        # Write to file
        output_file = 'debug_matching_output.json'
        with open(output_file, 'w') as f:
            json.dump(users_data, f, indent=2)
        
        # Print summary to console
        print("\n" + "="*80)
        print(f"TOTAL ACTIVE TEACHERS: {len(users_data)}")
        print("="*80)
        print(f"\n✅ Data written to: {output_file}")
        print("\n" + "="*80)
        
        # Summary statistics
        has_pref = sum(1 for u in users_data if u.get('has_swappreference'))
        has_school = sum(1 for u in users_data if u.get('school'))
        has_county = sum(1 for u in users_data if u.get('current_county'))
        has_both = sum(1 for u in users_data if u.get('current_county') and u.get('desired_county'))
        secondary = sum(1 for u in users_data if u.get('school_level') and 'secondary' in u.get('school_level', '').lower())
        
        print(f"\nSTATISTICS:")
        print(f"  Users with SwapPreference: {has_pref}/{len(users_data)}")
        print(f"  Users with School: {has_school}/{len(users_data)}")
        print(f"  Users with Current County: {has_county}/{len(users_data)}")
        print(f"  Users with BOTH Current & Desired County: {has_both}/{len(users_data)} ⚠️")
        print(f"  Secondary teachers: {secondary}/{len(users_data)}")
        
        # Show potential match pairs
        matchable_users = [u for u in users_data if u.get('current_county') and u.get('desired_county') and u.get('teacher_level')]
        print(f"\n📊 MATCHABLE USERS (have location data AND teacher level): {len(matchable_users)}")
        
        if len(matchable_users) >= 2:
            print("\nLooking for potential matches...")
            matches_found = 0
            for i, user_a in enumerate(matchable_users):
                for user_b in matchable_users[i+1:]:
                    # Check if levels match AND locations are reciprocal
                    if (user_a['teacher_level'] == user_b['teacher_level'] and
                        user_a['current_county'] == user_b['desired_county'] and 
                        user_a['desired_county'] == user_b['current_county']):
                        matches_found += 1
                        print(f"\n  ✅ MATCH #{matches_found}:")
                        print(f"     {user_a['email']} ({user_a['teacher_level']}): {user_a['current_county']} → {user_a['desired_county']}")
                        print(f"     {user_b['email']} ({user_b['teacher_level']}): {user_b['current_county']} → {user_b['desired_county']}")
            
            if matches_found == 0:
                print("  ❌ No valid 2-way matches found in production data!")
                print("     (Check if users have same teacher level and reciprocal county preferences)")
        
        print("="*80 + "\n")
