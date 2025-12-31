from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import PersonalProfile
from django.db import transaction

class Command(BaseCommand):
    help = 'Sync names between MyUser and PersonalProfile models'

    def handle(self, *args, **options):
        User = get_user_model()
        updated_count = 0
        created_count = 0

        with transaction.atomic():
            for user in User.objects.all():
                try:
                    # Get or create the profile
                    profile, created = PersonalProfile.objects.get_or_create(user=user)
                    
                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Created profile for user {user.email}'))
                    
                    # Track if we make any changes
                    profile_updated = False
                    
                    # Sync from User to Profile if User has names but Profile doesn't
                    if user.first_name and not profile.first_name:
                        profile.first_name = user.first_name
                        profile_updated = True
                    if user.last_name and not profile.last_name:
                        profile.last_name = user.last_name
                        profile_updated = True
                    
                    # Sync from Profile to User if Profile has names but User doesn't
                    if profile.first_name and not user.first_name:
                        user.first_name = profile.first_name
                        user.save(update_fields=['first_name'])
                    if profile.last_name and not user.last_name:
                        user.last_name = profile.last_name
                        user.save(update_fields=['last_name'])
                    
                    # Save profile if we made changes
                    if profile_updated:
                        profile.save()
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Updated profile for user {user.email}'))
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing user {user.email}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'\nSync complete!'))
        self.stdout.write(f'Total users processed: {User.objects.count()}')
        self.stdout.write(f'Profiles created: {created_count}')
        self.stdout.write(f'Profiles updated: {updated_count}')
