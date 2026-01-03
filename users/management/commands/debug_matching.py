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
            'profile__school__level',
            'swappreference__desired_county'
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
            if hasattr(user, 'profile') and user.profile:
                data['has_profile'] = True
                data['school'] = user.profile.school.name if user.profile.school else None
                data['school_level'] = user.profile.school.level.name if user.profile.school and user.profile.school.level else None
                
                # Current location
                if user.profile.school and user.profile.school.ward:
                    ward = user.profile.school.ward
                    if ward.constituency and ward.constituency.county:
                        data['current_county'] = ward.constituency.county.name
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
                data['current_county'] = None
            
            # Swap Preference
            try:
                pref = user.swappreference
                data['has_swappreference'] = True
                data['desired_county'] = pref.desired_county.name if pref.desired_county else None
                data['desired_county_id'] = pref.desired_county.id if pref.desired_county else None
                data['open_to_all'] = pref.open_to_all
            except:
                data['has_swappreference'] = False
                data['desired_county'] = None
                data['desired_county_id'] = None
                data['open_to_all'] = None
            
            # Subjects (for secondary)
            subjects = list(user.mysubject_set.values_list('subject__name', flat=True))
            data['subjects'] = subjects if subjects else []
            data['subject_count'] = len(subjects)
            
            users_data.append(data)
        
        # Print as formatted JSON
        print("\n" + "="*80)
        print(f"TOTAL ACTIVE TEACHERS: {len(users_data)}")
        print("="*80)
        print(json.dumps(users_data, indent=2))
        print("\n" + "="*80)
        
        # Summary statistics
        has_pref = sum(1 for u in users_data if u['has_swappreference'])
        has_school = sum(1 for u in users_data if u['school'])
        has_county = sum(1 for u in users_data if u['current_county'])
        secondary = sum(1 for u in users_data if u['school_level'] and 'secondary' in u['school_level'].lower())
        
        print(f"\nSTATISTICS:")
        print(f"  Users with SwapPreference: {has_pref}/{len(users_data)}")
        print(f"  Users with School: {has_school}/{len(users_data)}")
        print(f"  Users with County data: {has_county}/{len(users_data)}")
        print(f"  Secondary teachers: {secondary}/{len(users_data)}")
        print("="*80 + "\n")
