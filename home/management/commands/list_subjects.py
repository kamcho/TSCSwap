from django.core.management.base import BaseCommand
from home.models import Subject, MySubject
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'List all subjects and their relationships'

    def handle(self, *args, **options):
        # List all subjects
        self.stdout.write("\n=== All Subjects ===")
        for subject in Subject.objects.all().order_by('name'):
            self.stdout.write(f"ID: {subject.id}, Name: '{subject.name}', Level: {subject.level}")
        
        # List all MySubject relationships
        self.stdout.write("\n=== User-Subject Relationships ===")
        for mysubject in MySubject.objects.all().select_related('user').prefetch_related('subject'):
            user = mysubject.user
            subjects = list(mysubject.subject.all())
            subject_names = ", ".join([f"{s.name} (ID: {s.id})" for s in subjects])
            self.stdout.write(f"User: {user.get_full_name() or user.email} (ID: {user.id})")
            self.stdout.write(f"  MySubject ID: {mysubject.id}, Subjects: {subject_names}")
        
        # For the specific user we saw in the debug output (ID: 2)
        self.stdout.write("\n=== Debug for User ID 2 ===")
        try:
            user = User.objects.get(id=2)
            self.stdout.write(f"User: {user.get_full_name() or user.email} (ID: {user.id})")
            mysubjects = MySubject.objects.filter(user=user).prefetch_related('subject')
            for ms in mysubjects:
                subjects = list(ms.subject.all())
                subject_names = ", ".join([f"{s.name} (ID: {s.id})" for s in subjects])
                self.stdout.write(f"  MySubject ID: {ms.id}, Subjects: {subject_names}")
        except User.DoesNotExist:
            self.stdout.write("User with ID 2 not found")
