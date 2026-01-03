from django.core.management.base import BaseCommand
from users.models import MyUser
from home.matching import find_matches


class Command(BaseCommand):
    help = 'Test matching for specific users'

    def handle(self, *args, **options):
        # Test the two users that should match
        kevin = MyUser.objects.filter(email='kevingitundu@gmail.com').first()
        harun = MyUser.objects.filter(email='harungitundu@gmail.com').first()
        mercy = MyUser.objects.filter(email='mercygitundu97@gmail.com').first()
        
        if not kevin:
            print("❌ kevingitundu@gmail.com not found")
            return
        if not harun:
            print("❌ harungitundu@gmail.com not found")
            return
        if not mercy:
            print("❌ mercygitundu97@gmail.com not found")
            return
            
        print("\n" + "="*80)
        print("TESTING MATCHING FOR KNOWN USERS")
        print("="*80)
        
        # Test Kevin
        print(f"\n1. Testing kevingitundu@gmail.com:")
        print(f"   Has profile: {hasattr(kevin, 'profile') and kevin.profile}")
        print(f"   Has school: {kevin.profile.school if kevin.profile else None}")
        print(f"   Has swappreference: {hasattr(kevin, 'swappreference')}")
        
        try:
            kevin_matches = find_matches(kevin)
            print(f"   ✅ Matches found: {kevin_matches.count()}")
            for match in kevin_matches:
                print(f"      → {match.email}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Test Harun
        print(f"\n2. Testing harungitundu@gmail.com:")
        print(f"   Has profile: {hasattr(harun, 'profile') and harun.profile}")
        print(f"   Has school: {harun.profile.school if harun.profile else None}")
        print(f"   Has swappreference: {hasattr(harun, 'swappreference')}")
        
        try:
            harun_matches = find_matches(harun)
            print(f"   ✅ Matches found: {harun_matches.count()}")
            for match in harun_matches:
                print(f"      → {match.email}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Test Mercy
        print(f"\n3. Testing mercygitundu97@gmail.com:")
        print(f"   Has profile: {hasattr(mercy, 'profile') and mercy.profile}")
        print(f"   Has school: {mercy.profile.school if mercy.profile else None}")
        print(f"   Has swappreference: {hasattr(mercy, 'swappreference')}")
        
        try:
            mercy_matches = find_matches(mercy)
            print(f"   ✅ Matches found: {mercy_matches.count()}")
            for match in mercy_matches:
                print(f"      → {match.email}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*80)
