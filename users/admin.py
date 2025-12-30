from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Q, Count
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from home.models import Schools, SwapPreference, Counties, Constituencies, Wards, Level, Subject, MySubject
from .models import MyUser, PersonalProfile


class PotentialSwapMatchFilter(SimpleListFilter):
    title = _('Potential Swap Matches')
    parameter_name = 'potential_swap_match'
    
    def lookups(self, request, model_admin):
        # Get all users who have a school assigned
        users_with_schools = MyUser.objects.filter(
            profile__isnull=False,
            profile__school__isnull=False
        ).distinct()
        
        return [(str(user.id), f"{user.email} - {user.get_full_name() or 'No name'}") 
               for user in users_with_schools[:50]]  # Limit to 50 for performance
    
    def queryset(self, request, queryset):
        if not self.value():
            return queryset
            
        try:
            selected_user = MyUser.objects.get(id=self.value())
        except MyUser.DoesNotExist:
            return queryset.none()
            
        # Get selected user's school location
        try:
            user_school = selected_user.profile.school
            user_county = user_school.ward.constituency.county
            user_constituency = user_school.ward.constituency
            user_ward = user_school.ward
        except AttributeError:
            # User doesn't have complete school/location data
            return queryset.none()
            
        # Get selected user's swap preferences
        try:
            user_prefs = SwapPreference.objects.get(user=selected_user)
            
            # Create Q objects for location matching
            location_q = Q()
            
            # Check if user is open to all counties
            if user_prefs.open_to_all.exists():
                # User is open to all counties in their open_to_all list
                location_q |= Q(profile__school__ward__constituency__county__in=user_prefs.open_to_all.all())
            
            # Check specific location preferences
            if user_prefs.desired_county:
                location_q |= Q(profile__school__ward__constituency__county=user_prefs.desired_county)
                
                if user_prefs.desired_constituency:
                    location_q |= Q(profile__school__ward__constituency=user_prefs.desired_constituency)
                    
                    if user_prefs.desired_ward:
                        location_q |= Q(profile__school__ward=user_prefs.desired_ward)
            
            # Start with base query for location matches
            matches = queryset.filter(
                # User's current location matches selected user's preferences
                location_q,
                # And their preferences match selected user's current location
                Q(swappreference__open_to_all=user_county) |
                Q(swappreference__desired_county=user_county) |
                Q(swappreference__desired_constituency=user_constituency) |
                Q(swappreference__desired_ward=user_ward),
                # Exclude the selected user
                ~Q(id=selected_user.id),
                # Only include users with a profile and school
                profile__isnull=False,
                profile__school__isnull=False
            )
            
            # For secondary/high school, filter by matching subjects
            if hasattr(user_school, 'level') and ('secondary' in user_school.level.name.lower() or 'high' in user_school.level.name.lower()):
                # Get selected user's subjects
                user_subjects = set(MySubject.objects.filter(
                    user=selected_user
                ).values_list('subject__id', flat=True))
                
                if user_subjects:
                    # Filter matches to only include users who teach at least one of the same subjects
                    matches = matches.filter(
                        mysubject_set__subject__id__in=user_subjects
                    )
            
            return matches.distinct()
            
        except SwapPreference.DoesNotExist:
            return queryset.none()

def get_potential_matches_count(self, obj):
    """
    Calculate and return the number of potential swap matches for a user
    """
    try:
        # Check if user has a profile and school
        if not hasattr(obj, 'profile') or not obj.profile.school:
            return "No school assigned"
            
        # Get user's school and location
        user_school = obj.profile.school
        user_county = user_school.ward.constituency.county
        
        # Get user's level
        if not hasattr(user_school, 'level'):
            return "No level set"
            
        is_secondary = 'secondary' in user_school.level.name.lower() or 'high' in user_school.level.name.lower()
        
        # Base query for potential matches
        potential_matches = MyUser.objects.filter(
            ~Q(id=obj.id),  # Don't match with self
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
        if is_secondary:
            # Get user's subjects
            user_subjects = set(MySubject.objects.filter(
                user=obj
            ).values_list('subject__id', flat=True))
            
            if user_subjects:
                # Only include users who teach at least one of the same subjects
                potential_matches = potential_matches.filter(
                    mysubject_set__subject__in=user_subjects
                ).distinct()
        
        count = potential_matches.count()
        if count > 0:
            url = (
                reverse('admin:users_myuser_changelist') + 
                f'?potential_swap_match={obj.id}'
            )
            return format_html('<a href="{}">{} potential {}</a>', 
                             url, count, 'match' if count == 1 else 'matches')
        return "No matches"
        
    except Exception as e:
        return f"Error: {str(e)}"

def get_potential_matches_count_wrapper(obj):
    return get_potential_matches_count(None, obj)

get_potential_matches_count_wrapper.short_description = 'Potential Matches'

def get_school_location_wrapper(obj):
    if hasattr(obj, 'profile') and hasattr(obj.profile, 'school') and obj.profile.school:
        school = obj.profile.school
        return f"{school.ward.name}, {school.ward.constituency.name}, {school.ward.constituency.county.name}"
    return "No school assigned"

get_school_location_wrapper.short_description = 'School Location'

def get_school_level_wrapper(obj):
    if hasattr(obj, 'profile') and hasattr(obj.profile, 'school') and obj.profile.school and hasattr(obj.profile.school, 'level'):
        return obj.profile.school.level.name
    return "No level set"

get_school_level_wrapper.short_description = 'School Level'

@admin.register(MyUser)
class MyUserAdmin(admin.ModelAdmin):
    list_display = (
        'email', 
        'get_full_name', 
        get_school_level_wrapper,
        get_school_location_wrapper,
        get_potential_matches_count_wrapper,
        'is_active'
    )
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    # Removed duplicate method definitions since we're using wrapper functions
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            'profile__school__level',
            'swappreference__open_to_all',
            'mysubject_set__subject'  # Using the default related_name 'mysubject_set' for the reverse relation
        )
    
    # Using wrapper functions instead of class methods

@admin.register(PersonalProfile)
class PersonalProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'phone', 'location', 'gender', 'created_at')
    list_filter = ('gender', 'created_at')
    search_fields = ('user__email', 'first_name', 'last_name', 'phone', 'location')
    ordering = ('-created_at',)


    list_display = ('user',  'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    ordering = ('-created_at',)
    
    readonly_fields = ('created_at',)
    
   