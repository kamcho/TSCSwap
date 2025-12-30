from django.core.management.base import BaseCommand
from home.models import Subject, MySubject
from django.contrib.auth import get_user_model
from django.db.models import Count

User = get_user_model()

class Command(BaseCommand):
    help = 'Check relationships between users and subjects'

    def handle(self, *args, **options):
        # Get all users with their subjects
        users = User.objects.annotate(subject_count=Count('mysubject__subject')).filter(subject_count__gt=0)
        
        for user in users:
            self.stdout.write(f"\nUser: {user.get_full_name() or user.email} (ID: {user.id})")
            
            # Get all MySubject records for this user
            mysubjects = MySubject.objects.filter(user=user).prefetch_related('subject')
            
            for ms in mysubjects:
                subjects = list(ms.subject.all())
                subject_names = ", ".join([f"{s.name} (ID: {s.id})" for s in subjects])
                self.stdout.write(f"  MySubject ID: {ms.id}, Subject Count: {len(subjects)}")
                self.stdout.write(f"  Subjects: {subject_names}")
        
        # Now show all subjects and their counts across all users
        self.stdout.write("\n=== Subject Distribution ===")
        subjects = Subject.objects.annotate(user_count=Count('mysubject__user')).order_by('-user_count')
        
        for subject in subjects:
            self.stdout.write(f"{subject.name} (ID: {subject.id}): {subject.user_count} users")
            
            # Show which users have this subject
            users = User.objects.filter(mysubject__subject=subject)
            for user in users:
                self.stdout.write(f"  - {user.get_full_name() or user.email} (ID: {user.id})")
        
        # Check for any potential data issues
        self.stdout.write("\n=== Potential Issues ===")
        
        # Check for MySubject records with no subjects
        empty_mysubjects = MySubject.objects.annotate(subj_count=Count('subject')).filter(subj_count=0)
        if empty_mysubjects.exists():
            self.stdout.write(f"Found {empty_mysubjects.count()} MySubject records with no subjects")
            for ms in empty_mysubjects[:5]:  # Show first 5 to avoid too much output
                self.stdout.write(f"  MySubject ID: {ms.id}, User: {ms.user.email if ms.user else 'No user'}")
