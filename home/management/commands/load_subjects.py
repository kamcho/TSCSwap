from django.core.management.base import BaseCommand
from home.models import Level, Subject

class Command(BaseCommand):
    help = 'Load subjects data into the database from a predefined dataset'
    
    def handle(self, *args, **options):
        # Dataset containing level names and their respective subjects
        # Format: {'Level Name': ['Subject1', 'Subject2', ...], ...}
        SUBJECTS_DATA = {
            'Lower Primary': [
                'Creative Activities',
                'CRE',
                'English Activities',
                'Environmental Activities',
                'HRE',
                'IRE',
                'Kiswahili',
                'Mathematics'
            ],
            'Upper Primary': [
                'Agriculture',
                'Arabic',
                'Creative Arts',
                'CRE',
                'English',
                'French',
                'German',
                'HRE',
                'Indigenous Language',
                'IRE',
                'Kiswahili',
                'Mandarin',
                'Mathematics',
                'Science & Technology',
                'Social Studies'
            ],
            'Junior Secondary': [
                'Agriculture',
                'Arabic',
                'Creative Arts',
                'CRE',
                'English',
                'French',
                'German',
                'HRE',
                'Indigenous Language',
                'Integrated Science',
                'IRE',
                'Kiswahili',
                'Mandarin',
                'Mathematics',
                'Pre-Technical Studies',
                'Social Studies'
            ],
            'Senior Secondary': [
                'Applied Sciences',
                'Arts & Sports',
                'Foreign Languages',
                'Humanities',
                'Languages',
                'Pure Sciences',
                'Religious Education',
                'Technical Studies'
            ]
        }
        
        created_count = 0
        
        for level_name, subjects in SUBJECTS_DATA.items():
            try:
                # Get or create the level
                level, created = Level.objects.get_or_create(
                    name=level_name,
                    defaults={
                        'code': level_name.upper()[:3],
                        'description': f'{level_name} level subjects'
                    }
                )
                
                # Create subjects for this level
                for subject_name in subjects:
                    subject, created = Subject.objects.get_or_create(
                        name=subject_name,
                        level=level,
                        defaults={
                            'code': ''.join(word[0].upper() for word in subject_name.split())
                        }
                    )
                    if created:
                        created_count += 1
                
                self.stdout.write(self.style.SUCCESS(f'Successfully processed {level_name} level with {len(subjects)} subjects'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing {level_name}: {str(e)}'))
        
        total_subjects = sum(len(subjects) for subjects in SUBJECTS_DATA.values())
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created/updated {created_count} out of {total_subjects} total subjects'))
