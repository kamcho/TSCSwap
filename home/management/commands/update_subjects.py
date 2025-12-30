from django.core.management.base import BaseCommand
from home.models import Subject, Level
from django.db import transaction

class Command(BaseCommand):
    help = 'Update test subjects to proper subject names'

    def handle(self, *args, **options):
        # Get the Secondary/High School level
        try:
            secondary_level = Level.objects.get(name__icontains='Secondary')
            
            # Update existing subjects one by one to handle unique constraint
            updated = 0
            with transaction.atomic():
                try:
                    # First, update the second subject to a temporary name
                    sub2 = Subject.objects.get(id=2)
                    sub2.name = 'TEMP_ENGLISH'
                    sub2.code = 'TEMP_ENG'
                    sub2.save()
                    
                    # Then update the first subject
                    sub1 = Subject.objects.get(id=1)
                    sub1.name = 'Mathematics'
                    sub1.code = 'MATH'
                    sub1.save()
                    
                    # Finally, update the second subject to its final name
                    sub2.name = 'English'
                    sub2.code = 'ENG'
                    sub2.save()
                    
                    updated = 2
                except Subject.DoesNotExist:
                    self.stdout.write(self.style.WARNING('One or more subjects not found'))
            
            self.stdout.write(self.style.SUCCESS(f'Updated {updated} subjects'))
            
            # Create common subjects if they don't exist
            common_subjects = [
                ('Kiswahili', 'KISW'),
                ('Biology', 'BIO'),
                ('Chemistry', 'CHEM'),
                ('Physics', 'PHY'),
                ('History', 'HIST'),
                ('Geography', 'GEO'),
                ('CRE', 'CRE'),
                ('IRE', 'IRE'),
                ('Business Studies', 'BS'),
                ('Agriculture', 'AGR')
            ]
            
            created_count = 0
            for name, code in common_subjects:
                _, created = Subject.objects.get_or_create(
                    name=name,
                    defaults={
                        'code': code,
                        'level': secondary_level
                    }
                )
                if created:
                    created_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'Created {created_count} new subjects'))
            
        except Level.DoesNotExist:
            self.stdout.write(self.style.ERROR('Secondary/High School level not found. Please create it first.'))
