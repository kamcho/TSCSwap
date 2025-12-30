from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Check user information'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='User ID to check')

    def handle(self, *args, **options):
        user_id = options['user_id']
        try:
            user = User.objects.get(id=user_id)
            self.stdout.write(f"User ID: {user.id}")
            self.stdout.write(f"Username: {user.username}")
            self.stdout.write(f"Email: {user.email}")
            self.stdout.write(f"First Name: '{user.first_name}'")
            self.stdout.write(f"Last Name: '{user.last_name}'")
            self.stdout.write(f"Full Name (get_full_name): '{user.get_full_name()}'")
            
            # Check if profile exists
            if hasattr(user, 'profile'):
                self.stdout.write("\nProfile Information:")
                self.stdout.write(f"  - School: {getattr(user.profile, 'school', 'Not set')}")
            else:
                self.stdout.write("\nNo profile found for this user")
                
        except User.DoesNotExist:
            self.stderr.write(f"User with ID {user_id} does not exist")
