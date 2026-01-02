import os
import re
import requests
import json
from difflib import get_close_matches
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from dotenv import load_dotenv
from .intent_detection import IntentType, get_intent_detector

User = get_user_model()

# Load environment variables
load_dotenv()

class WhatsAppClient:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v17.0"
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "test123")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def send_text_message(self, to_number, message_text):
        """Send a text message to a WhatsApp user."""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response content: {e.response.text}")
            return None

# Initialize the WhatsApp client
whatsapp_client = WhatsAppClient()

# Log configuration on startup
print("\n" + "="*50)
print("WhatsApp Client Configuration:")
print("="*50)
print(f"Phone Number ID: {whatsapp_client.phone_number_id}")
print(f"Access Token: {'✅ Set' if whatsapp_client.access_token else '❌ Missing'}")
print(f"Verify Token: {whatsapp_client.verify_token}")
print("="*50 + "\n")

def is_greeting(message: str) -> bool:
    """Check if the message is a greeting."""
    if not message:
        return False
    
    message_lower = message.lower().strip()
    greetings = [
        'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon',
        'good evening', 'good night', 'morning', 'afternoon', 'evening',
        'hey there', 'hi there', 'hello there', 'what\'s up', 'whats up',
        'sup', 'yo', 'hola', 'namaste', 'salam', 'jambo'
    ]
    
    # Check if message starts with a greeting or is just a greeting
    for greeting in greetings:
        if message_lower.startswith(greeting) or message_lower == greeting:
            return True
    
    return False

def get_welcome_message() -> str:
    """Get a welcome message with guide on what the bot can do."""
    return """👋 Hello! Welcome to TSC Swap! 🌟

I'm here to help you with teacher swap opportunities. Here's what I can do:

📋 *View Your Profile*
   • Show your profile information
   • Check your account details

🔍 *Find Swap Opportunities*
   • Search for available swaps
   • Find matching teachers
   • Discover exchange opportunities

❓ *Ask Questions*
   • How swaps work
   • TSC transfer process
   • Requirements and documents
   • Triangle swaps
   • Safety and verification

📞 *Request Support*
   • Get a callback from our team
   • Contact support

⚙️ *Update Preferences*
   • Change your location
   • Update your subject preferences
   • Modify your swap settings

*About TSC Swap:*
We're an organization that helps teachers find swap mates and verify information to keep off scammers. We're not TSC, but we help guide you through the process! 😊

Just send me a message and I'll help you!

For example:
• "Show my profile"
• "Find swaps in Nairobi"
• "How do swaps work?"
• "What documents do I need?"
"""

def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number for comparison.
    Handles different formats:
    - Local format: 0742134431 → 254742134431
    - International: 254742134431 → 254742134431
    - With +: +254742134431 → 254742134431
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters except keep digits
    normalized = re.sub(r'[^\d]', '', str(phone))
    
    # Handle Kenyan phone numbers
    # If it starts with 0 (local format), replace with 254
    if normalized.startswith('0'):
        normalized = '254' + normalized[1:]
    
    # If it doesn't start with 254 and is 9 digits (typically starting with 7), add 254 prefix
    if not normalized.startswith('254') and len(normalized) == 9:
        normalized = '254' + normalized
    
    return normalized

def get_user_by_phone(phone_number: str):
    """Get user by phone number from PersonalProfile.
    
    Handles multiple phone number formats:
    - Local: 0742134431
    - International: 254742134431
    - With +: +254742134431
    """
    try:
        from users.models import PersonalProfile
        
        if not phone_number:
            print("❌ No phone number provided")
            return None
        
        normalized_whatsapp_phone = normalize_phone_number(phone_number)
        print(f"🔍 Looking up user with WhatsApp phone: {phone_number} (normalized: {normalized_whatsapp_phone})")
        
        # Try exact match first (in case the stored format matches exactly)
        profile = PersonalProfile.objects.filter(phone=phone_number).first()
        if profile:
            print(f"✅ Found user with exact match: {profile.user.email}")
            return profile.user
        
        # Try normalized match - check all profiles
        if normalized_whatsapp_phone:
            profiles = PersonalProfile.objects.exclude(phone__isnull=True).exclude(phone='')
            print(f"🔍 Checking {profiles.count()} profiles for normalized match...")
            
            for prof in profiles:
                if not prof.phone:
                    continue
                    
                # Normalize the database phone number
                normalized_db_phone = normalize_phone_number(prof.phone)
                
                # Also try the original format from database
                if prof.phone == phone_number:
                    print(f"✅ Found user with exact DB match: {prof.user.email}")
                    return prof.user
                
                # Compare normalized versions
                if normalized_db_phone and normalized_whatsapp_phone:
                    print(f"  Comparing: '{prof.phone}' (normalized: {normalized_db_phone}) with {normalized_whatsapp_phone}")
                    
                    if normalized_db_phone == normalized_whatsapp_phone:
                        print(f"✅ Found user with normalized match: {prof.user.email}")
                        return prof.user
            
            print(f"❌ No matching profile found for phone: {phone_number} (normalized: {normalized_whatsapp_phone})")
    except Exception as e:
        import traceback
        print(f"❌ Error getting user by phone: {str(e)}\n{traceback.format_exc()}")
    return None

def get_profile_completeness_links(user) -> str:
    """
    Check profile completeness and return formatted message with links to incomplete sections.
    
    Returns:
        Formatted string with links to incomplete profile sections, or empty string if complete
    """
    try:
        from users.models import PersonalProfile
        from home.models import SwapPreference, MySubject
        
        missing_sections = []
        
        # Check if profile exists
        try:
            profile = user.profile
        except PersonalProfile.DoesNotExist:
            missing_sections.append({
                'name': 'Profile',
                'link': 'https://www.tscswap.com/users/profile/edit/',
                'description': 'Complete your personal profile'
            })
            return format_missing_sections_message(missing_sections)
        
        # Check if school is linked
        if not profile.school:
            missing_sections.append({
                'name': 'School Information',
                'link': None,  # Special case - need to contact admin
                'description': 'Contact admin to link your school',
                'admin_contact': '+254742134431'
            })
        
        # Check if level is set
        if not profile.level:
            missing_sections.append({
                'name': 'Teaching Level',
                'link': 'https://www.tscswap.com/mysubject/new/',
                'description': 'Set your teaching level'
            })
        
        # Check if swap preferences are set
        try:
            if not hasattr(user, 'swappreference') or not user.swappreference:
                missing_sections.append({
                    'name': 'Swap Preferences',
                    'link': 'https://www.tscswap.com/preferences/',
                    'description': 'Set your swap preferences'
                })
        except Exception:
            missing_sections.append({
                'name': 'Swap Preferences',
                'link': 'https://www.tscswap.com/preferences/',
                'description': 'Set your swap preferences'
            })
        
        # Check if subjects are set (for secondary/high school teachers only)
        if profile.level and ('secondary' in profile.level.name.lower() or 'high' in profile.level.name.lower()):
            try:
                my_subjects = MySubject.objects.filter(user=user).first()
                if not my_subjects or not my_subjects.subject.exists():
                    missing_sections.append({
                        'name': 'Teaching Subjects',
                        'link': 'https://www.tscswap.com/mysubject/new/',
                        'description': 'Add your teaching subjects'
                    })
            except Exception:
                missing_sections.append({
                    'name': 'Teaching Subjects',
                    'link': 'https://www.tscswap.com/mysubject/new/',
                    'description': 'Add your teaching subjects'
                })
        
        if missing_sections:
            return format_missing_sections_message(missing_sections)
        
        return ""
        
    except Exception as e:
        print(f"Error checking profile completeness: {str(e)}")
        return ""

def format_missing_sections_message(missing_sections: list) -> str:
    """
    Format a message with links to missing profile sections.
    
    Args:
        missing_sections: List of dicts with 'name', 'link', 'description', and optionally 'admin_contact'
    
    Returns:
        Formatted string with links
    """
    if not missing_sections:
        return ""
    
    message = "\n\n⚠️ *Complete Your Profile*\n\n"
    message += "To find better matches, please complete the following:\n\n"
    
    for i, section in enumerate(missing_sections, 1):
        if section.get('admin_contact'):
            # Special case for school information
            message += f"{i}️⃣ *{section['name']}*\n"
            message += f"   {section['description']}\n"
            message += f"   📧 Inbox school information to admin: {section['admin_contact']}\n\n"
        else:
            message += f"{i}️⃣ *{section['name']}*\n"
            message += f"   {section['description']}\n"
            message += f"   🔗 {section['link']}\n\n"
    
    return message

def find_similar_counties(location: str, limit: int = 3) -> list:
    """
    Find similar county names using fuzzy matching.
    
    Args:
        location: The location string to match
        limit: Maximum number of suggestions to return
    
    Returns:
        List of county name strings that are similar to the input
    """
    try:
        from home.models import Counties
        
        # Get all county names
        all_counties = list(Counties.objects.values_list('name', flat=True))
        
        if not all_counties:
            return []
        
        # Use difflib to find close matches
        # cutoff=0.6 means at least 60% similarity
        similar = get_close_matches(
            location.lower(),
            [county.lower() for county in all_counties],
            n=limit,
            cutoff=0.5
        )
        
        # Map back to original case county names
        county_map = {c.lower(): c for c in all_counties}
        return [county_map[match] for match in similar if match in county_map]
    except Exception as e:
        print(f"Error finding similar counties: {str(e)}")
        return []

def find_swaps_by_location(location: str, user_level, asking_user, counties_list=None) -> tuple:
    """
    Find users who teach in a specific location and share the same teaching level.
    
    Args:
        location: Location name (e.g., "Nairobi") - optional if counties_list is provided
        user_level: The Level object of the asking user
        asking_user: The User object who is asking for swaps
        counties_list: List of County objects to search in (optional, overrides location)
    
    Returns:
        Tuple of (list of User objects, error_info dict)
        error_info contains:
        - 'no_counties_found': bool - True if no counties matched the location
        - 'suggestions': list - List of suggested county names if no match found
    """
    try:
        from users.models import PersonalProfile
        from home.models import Counties, Schools
        
        error_info = {'no_counties_found': False, 'suggestions': []}
        
        if not user_level:
            return [], error_info
        
        # Use counties_list if provided, otherwise find counties by location name
        if counties_list:
            counties = Counties.objects.filter(id__in=[c.id for c in counties_list])
            print(f"🔍 Using {counties.count()} counties from swap preferences")
        elif location:
            # Find counties matching the location name (case-insensitive)
            counties = Counties.objects.filter(name__icontains=location)
            if not counties.exists():
                print(f"⚠️ No counties found matching: {location}")
                error_info['no_counties_found'] = True
                error_info['suggestions'] = find_similar_counties(location, limit=3)
                return [], error_info
        else:
            # No location and no counties_list provided
            return [], error_info
        
        # Find schools in those counties (through ward → constituency → county)
        # Schools are linked: school.ward.constituency.county
        schools_query = Schools.objects.filter(
            ward__constituency__county__in=counties,
            level=user_level  # Same teaching level
        ).select_related('ward__constituency__county', 'level')
        
        location_text = location or f"{counties.count()} preferred county/counties"
        print(f"🔍 Found {schools_query.count()} schools in {location_text} at level {user_level.name}")
        
        # Find users who teach at those schools and have the same level
        matching_users = PersonalProfile.objects.filter(
            school__in=schools_query,
            level=user_level,  # Same teaching level as asking user
            user__is_active=True
        ).exclude(
            user=asking_user  # Exclude the asking user
        ).select_related(
            'user', 'school', 'level', 'school__ward__constituency__county'
        ).distinct()
        
        print(f"✅ Found {matching_users.count()} matching users")
        
        return list(matching_users), error_info
        
    except Exception as e:
        import traceback
        print(f"❌ Error finding swaps by location: {str(e)}\n{traceback.format_exc()}")
        return [], {'no_counties_found': False, 'suggestions': []}

def mask_phone_number(phone: str) -> str:
    """Mask phone number for privacy (e.g., +254712345678 → +2547***5678)."""
    if not phone:
        return "Not provided"
    
    # Remove all non-digit characters for processing
    digits_only = re.sub(r'[^\d]', '', phone)
    
    # Handle different phone number formats
    if len(digits_only) >= 10:
        # Keep first 4 digits and last 4 digits, mask the middle
        if digits_only.startswith('254') and len(digits_only) == 12:
            # Format: 254712345678
            masked = f"+254{digits_only[3:4]}***{digits_only[-4:]}"
        elif digits_only.startswith('0') and len(digits_only) == 10:
            # Format: 0742134431
            masked = f"0{digits_only[1:2]}***{digits_only[-4:]}"
        elif len(digits_only) == 9:
            # Format: 742134431
            masked = f"{digits_only[0]}***{digits_only[-4:]}"
        else:
            # Generic masking: keep first 4 and last 4
            masked = f"{digits_only[:4]}***{digits_only[-4:]}"
    else:
        # Too short, just mask most of it
        masked = "***" + digits_only[-2:] if len(digits_only) > 2 else "***"
    
    return masked

def find_triangle_swaps_for_whatsapp(asking_user, location: str, user_level) -> str:
    """
    Find triangle swaps that include the asking user and format for WhatsApp.
    
    Args:
        asking_user: The User object who is asking for swaps
        location: Location name (optional, for filtering)
        user_level: The Level object of the asking user
    
    Returns:
        Formatted string with triangle swap opportunities, or empty string if none found
    """
    try:
        from home.triangle_swap_utils import (
            find_triangle_swaps_primary,
            find_triangle_swaps_secondary,
            get_current_county,
            get_user_subjects
        )
        from home.models import MyUser, Counties
        from users.models import PersonalProfile
        
        # Check if user has complete profile and swap preferences
        # Note: We don't return error messages here as triangle swaps are optional
        # The main swap search will handle profile completeness checks
        if not hasattr(asking_user, 'profile') or not asking_user.profile.school:
            return ""
        
        if not hasattr(asking_user, 'swappreference') or not asking_user.swappreference:
            return ""
        
        # Determine if user is primary or secondary
        user_school_level = asking_user.profile.school.level
        is_secondary = user_school_level and ('secondary' in user_school_level.name.lower() or 'high' in user_school_level.name.lower())
        
        # Get all teachers at the same level with complete profiles
        # Note: Include the asking user in the queryset so they can be part of triangle swaps
        # Note: For triangle swaps, we don't filter by location upfront because
        # triangle swaps involve circular exchanges, and the location might be relevant
        # to any teacher in the triangle (current location or desired location)
        teachers = MyUser.objects.filter(
            is_active=True,
            role='Teacher',
            profile__isnull=False,
            profile__school__isnull=False,
            profile__school__level=user_school_level,
            swappreference__isnull=False
        ).select_related(
            'profile__school__ward__constituency__county',
            'swappreference__desired_county'
        ).prefetch_related(
            'swappreference__open_to_all'
        )
        
        # Find triangle swaps
        if is_secondary:
            all_triangles = find_triangle_swaps_secondary(teachers)
        else:
            all_triangles = find_triangle_swaps_primary(teachers)
        
        # Filter triangles that include the asking user
        user_triangles = []
        for teacher_a, teacher_b, teacher_c in all_triangles:
            if asking_user.id in [teacher_a.id, teacher_b.id, teacher_c.id]:
                # Get locations
                county_a = get_current_county(teacher_a)
                county_b = get_current_county(teacher_b)
                county_c = get_current_county(teacher_c)
                
                # If location is provided, check if any teacher in the triangle is in that location
                # (either current location or desired location)
                if location:
                    counties = Counties.objects.filter(name__icontains=location)
                    if counties.exists():
                        county_ids = set(counties.values_list('id', flat=True))
                        triangle_counties = set()
                        if county_a:
                            triangle_counties.add(county_a.id)
                        if county_b:
                            triangle_counties.add(county_b.id)
                        if county_c:
                            triangle_counties.add(county_c.id)
                        
                        # Check desired counties too
                        for teacher in [teacher_a, teacher_b, teacher_c]:
                            if hasattr(teacher, 'swappreference') and teacher.swappreference:
                                if teacher.swappreference.desired_county:
                                    triangle_counties.add(teacher.swappreference.desired_county.id)
                                triangle_counties.update(
                                    teacher.swappreference.open_to_all.values_list('id', flat=True)
                                )
                        
                        # Only include if location matches any county in the triangle
                        if not triangle_counties.intersection(county_ids):
                            continue
                
                # Determine the user's position in the triangle
                if asking_user.id == teacher_a.id:
                    user_position = "A"
                elif asking_user.id == teacher_b.id:
                    user_position = "B"
                else:
                    user_position = "C"
                
                # Get common subjects for secondary teachers
                common_subjects_text = ""
                if is_secondary:
                    subjects_a = get_user_subjects(teacher_a)
                    subjects_b = get_user_subjects(teacher_b)
                    subjects_c = get_user_subjects(teacher_c)
                    common_subjects = subjects_a.intersection(subjects_b).intersection(subjects_c)
                    if common_subjects:
                        from home.models import Subject
                        subject_names = Subject.objects.filter(id__in=common_subjects).values_list('name', flat=True)
                        common_subjects_text = f"\n📚 Common Subjects: {', '.join(subject_names[:3])}"
                        if len(subject_names) > 3:
                            common_subjects_text += f" +{len(subject_names) - 3} more"
                
                user_triangles.append({
                    'teacher_a': teacher_a,
                    'teacher_b': teacher_b,
                    'teacher_c': teacher_c,
                    'county_a': county_a.name if county_a else 'Unknown',
                    'county_b': county_b.name if county_b else 'Unknown',
                    'county_c': county_c.name if county_c else 'Unknown',
                    'user_position': user_position,
                    'common_subjects': common_subjects_text
                })
        
        # Format for WhatsApp (limit to 3 triangles)
        if not user_triangles:
            return ""
        
        formatted_triangles = []
        formatted_triangles.append("🔺 *Triangle Swap Opportunities*\n")
        formatted_triangles.append("Found circular swap opportunities where 3 teachers exchange locations:\n")
        
        for i, triangle in enumerate(user_triangles[:3], 1):  # Limit to 3 triangles
            teacher_a = triangle['teacher_a']
            teacher_b = triangle['teacher_b']
            teacher_c = triangle['teacher_c']
            county_a = triangle['county_a']
            county_b = triangle['county_b']
            county_c = triangle['county_c']
            user_pos = triangle['user_position']
            common_subjects = triangle['common_subjects']
            
            # Get names
            name_a = teacher_a.get_full_name() or teacher_a.email.split('@')[0]
            name_b = teacher_b.get_full_name() or teacher_b.email.split('@')[0]
            name_c = teacher_c.get_full_name() or teacher_c.email.split('@')[0]
            
            formatted_triangles.append(f"*Triangle {i}:*\n")
            formatted_triangles.append(f"🔄 {name_a} ({county_a}) → {name_b} ({county_b}) → {name_c} ({county_c}) → {name_a}{common_subjects}\n")
        
        if len(user_triangles) > 3:
            formatted_triangles.append(f"\n... and {len(user_triangles) - 3} more triangle swap(s) available!")
        
        formatted_triangles.append("\n💡 *How it works:*")
        formatted_triangles.append("All three teachers exchange locations in a circular pattern, so everyone gets their desired location!")
        
        return "\n".join(formatted_triangles)
        
    except Exception as e:
        import traceback
        print(f"Error finding triangle swaps for WhatsApp: {str(e)}\n{traceback.format_exc()}")
        return ""

def format_swap_results(matching_profiles, location: str, user_level, using_preferences: bool = False) -> str:
    """Format swap results for WhatsApp response. Returns up to 10 results with masked phones."""
    try:
        if not matching_profiles:
            return "No matching swaps found."
        
        # Limit to 10 results
        profiles_to_show = matching_profiles[:10]
        total_count = len(matching_profiles)
        
        results = []
        results.append(f"""🔍 *Swap Opportunities Found*
        
Detected Intent: Find Swaps ✅
📍 Location: {location or 'Any location'}
📚 Level: {user_level.name if user_level else 'Not set'}""")
        
        # Add message if using preferences
        if using_preferences:
            results.append("\nℹ️ Since you didn't specify a location, I used your swap preferences.")
        
        results.append(f"""
Found {total_count} matching teacher(s):
        
━━━━━━━━━━━━━━━━━━━━""")
        
        for i, profile in enumerate(profiles_to_show, 1):
            user = profile.user
            
            # Get name - prefer first_name + surname, fallback to first_name + last_name, or just first_name
            if profile.first_name:
                if profile.surname:
                    full_name = f"{profile.first_name} {profile.surname}"
                elif profile.last_name:
                    full_name = f"{profile.first_name} {profile.last_name}"
                else:
                    full_name = profile.first_name
            else:
                full_name = user.email
            
            # Get school and location
            school_name = profile.school.name if profile.school else "Not set"
            county_name = ""
            if profile.school and profile.school.ward:
                county_name = profile.school.ward.constituency.county.name if profile.school.ward.constituency else ""
            
            # Get subjects if available
            subjects_text = ""
            try:
                from home.models import MySubject
                my_subjects = MySubject.objects.filter(user=user).first()
                if my_subjects and my_subjects.subject.exists():
                    subject_names = [subj.name for subj in my_subjects.subject.all()[:3]]  # Limit to 3 subjects
                    subjects_text = f"\n📚 Subjects: {', '.join(subject_names)}"
            except:
                pass
            
            # Mask phone number
            masked_phone = mask_phone_number(profile.phone) if profile.phone else "Not provided"
            
            results.append(f"""
{i}. 👤 *{full_name}*
   🏫 School: {school_name}
   📍 Location: {county_name}
   📞 Phone: {masked_phone}{subjects_text}""")
        
        if total_count > 10:
            results.append(f"\n... and {total_count - 10} more result(s)")
        
        results.append("\n━━━━━━━━━━━━━━━━━━━━")
        results.append("\n💡 Log in to your TSC Swap account to see all results and full contact details!")
        
        return "\n".join(results)
        
    except Exception as e:
        import traceback
        print(f"Error formatting swap results: {str(e)}\n{traceback.format_exc()}")
        return f"Found {len(matching_profiles)} matching swaps. Please log in to see details."

def format_profile_data(user, phone_number: str) -> str:
    """Format user profile data for WhatsApp response."""
    try:
        from users.models import PersonalProfile
        from home.models import SwapPreference, MySubject
        
        # Get profile
        try:
            profile = user.profile
        except PersonalProfile.DoesNotExist:
            completeness_msg = get_profile_completeness_links(user)
            return f"""❌ *Profile Not Found*

Your account exists, but you haven't set up your personal profile yet.

Please log in to your TSC Swap account and complete your profile setup to view your information here.{completeness_msg}"""
        
        # Build name
        name_parts = []
        if profile.first_name:
            name_parts.append(profile.first_name)
        if profile.surname:
            name_parts.append(profile.surname)
        elif profile.last_name:
            name_parts.append(profile.last_name)
        full_name = ' '.join(name_parts) if name_parts else user.email
        
        # Get school
        school_name = profile.school.name if profile.school else "Not set"
        
        # Get level
        level_name = profile.level.name if profile.level else "Not set"
        
        # Get swap preferences
        swap_pref_text = ""
        try:
            if hasattr(user, 'swappreference'):
                swap_pref = user.swappreference
                preferences = []
                
                if swap_pref.desired_county:
                    preferences.append(f"📍 Desired County: {swap_pref.desired_county.name}")
                if swap_pref.desired_constituency:
                    preferences.append(f"🏛️ Desired Constituency: {swap_pref.desired_constituency.name}")
                if swap_pref.desired_ward:
                    preferences.append(f"🏘️ Desired Ward: {swap_pref.desired_ward.name}")
                
                if swap_pref.open_to_all.exists():
                    open_counties = [c.name for c in swap_pref.open_to_all.all()]
                    preferences.append(f"🌍 Open To All: {', '.join(open_counties)}")
                
                if swap_pref.is_hardship and swap_pref.is_hardship != 'Any':
                    preferences.append(f"🏔️ Hardship Preference: {swap_pref.is_hardship}")
                
                if preferences:
                    swap_pref_text = "\n".join(preferences)
                else:
                    swap_pref_text = "No preferences set"
            else:
                swap_pref_text = "Not set"
        except Exception as e:
            print(f"Error getting swap preferences: {str(e)}")
            swap_pref_text = "Not set"
        
        # Get subjects
        subjects_text = ""
        try:
            my_subjects = MySubject.objects.filter(user=user).first()
            if my_subjects and my_subjects.subject.exists():
                subject_names = [subj.name for subj in my_subjects.subject.all()]
                subjects_text = ", ".join(subject_names)
            else:
                subjects_text = "No subjects set"
        except Exception as e:
            print(f"Error getting subjects: {str(e)}")
            subjects_text = "Not set"
        
        # Format the response
        response = f"""👤 *Your Profile Information*

━━━━━━━━━━━━━━━━━━━━

👨‍💼 *Personal Details*
• Name: {full_name}
• Email: {user.email}
• Phone: {profile.phone or 'Not set'}

🏫 *School Information*
• School: {school_name}
• Level: {level_name}

📚 *Teaching Subjects*
• Subjects: {subjects_text}

⚙️ *Swap Preferences*
{swap_pref_text}

━━━━━━━━━━━━━━━━━━━━

Need to update your profile? Log in to your TSC Swap account! 😊"""
        
        # Add profile completeness check
        completeness_msg = get_profile_completeness_links(user)
        if completeness_msg:
            response += completeness_msg
        
        return response
        
    except Exception as e:
        import traceback
        print(f"Error formatting profile: {str(e)}\n{traceback.format_exc()}")
        return f"""❌ *Error Loading Profile*

I encountered an error while loading your profile information. Please try again later or contact support.

Error: {str(e)}"""

def answer_swap_question(question: str, user=None, conversation_history=None) -> str:
    """
    Answer questions about swaps, TSC transfers, and the platform using OpenAI.
    
    Args:
        question: The user's question
        user: The User object (optional, for conversation history)
        conversation_history: List of previous messages in format [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    
    Returns:
        A helpful answer to the question
    """
    try:
        from openai import OpenAI
        import os
        from dotenv import load_dotenv
        from chat.models import UserQuery, AIResponse
        
        load_dotenv()
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not openai_api_key:
            return """❌ I'm having trouble accessing my knowledge base right now. Please try again later or contact our support team."""
        
        client = OpenAI(api_key=openai_api_key)
        
        # System prompt that clarifies the organization's role
        system_prompt = """You are a helpful assistant for TSC Swap, an organization that helps teachers find suitable swap mates and verify information to keep off scammers.

IMPORTANT CONTEXT:
- TSC Swap is NOT the Teachers Service Commission (TSC)
- We are an independent organization that helps teachers find swap opportunities
- We verify teacher information to prevent scams and fraud
- We help teachers connect with potential swap partners across Kenya's 47 counties
- We provide guidance on the TSC transfer process but are not TSC itself

Your role is to answer questions about:
- How teacher swaps work
- The TSC transfer process (as a helpful guide, not as TSC)
- How to use the TSC Swap platform
- Requirements for swaps
- Triangle swaps (circular 3-teacher exchanges)
- Safety and verification measures
- General questions about finding swap partners

Be friendly, helpful, and accurate. Always clarify that TSC Swap is a helping organization, not TSC itself. Keep answers concise and WhatsApp-friendly (use emojis appropriately)."""
        
        # Prepare messages with conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided (last 5 messages = 5 user + 5 assistant = 10 messages total)
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current question
        messages.append({"role": "user", "content": question})
        
        # Call OpenAI with web search if available (using GPT-4 with browsing or similar)
        # For now, we'll use GPT-3.5-turbo and add web search results if needed
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Add a friendly footer
            answer += "\n\n💡 *Need more help?* Just ask me anything about swaps, or try:\n• \"Find swaps in [location]\"\n• \"Show my profile\"\n• \"How do I update my preferences?\""
            
            return answer
            
        except Exception as e:
            print(f"Error getting answer from OpenAI: {str(e)}")
            return f"""I understand you're asking about: "{question}"

I'm here to help with questions about teacher swaps and the TSC transfer process!

TSC Swap is an organization that helps teachers find swap mates and verify information to keep off scammers. We're not TSC, but we help guide you through the process.

For specific questions, you can:
• Ask me about how swaps work
• Ask about requirements and documents
• Ask about the transfer process
• Search for swaps in your preferred location

What would you like to know? 😊"""
            
    except Exception as e:
        print(f"Error in answer_swap_question: {str(e)}")
        return f"""I'd love to help answer your question, but I'm having a technical issue right now.

Please try asking again, or contact our support team for assistance.

Remember: TSC Swap helps teachers find swap mates and verify information. We're here to help! 😊"""

def generate_response(message: str, intent: IntentType, entities: dict, phone_number: str = None, conversation_history: list = None) -> str:
    """Generate an appropriate response based on intent and message."""
    intent_name = intent.value.replace("_", " ").title()
    
    # Handle greetings
    if is_greeting(message):
        return get_welcome_message()
    
    # Handle different intents with friendly responses
    if intent == IntentType.GET_PROFILE:
        # Try to get user by phone number
        user = None
        if phone_number:
            user = get_user_by_phone(phone_number)
        
        if user:
            # User found, return formatted profile
            print(f"✅ User found: {user.email}, formatting profile data...")
            return format_profile_data(user, phone_number)
        else:
            # User not found by phone number
            print(f"❌ User not found for WhatsApp number: {phone_number}")
            return f"""👤 *Profile Information Request*

I detected you want to view your profile information.

Detected Intent: {intent_name} ✅

❌ I couldn't find your profile linked to this WhatsApp number ({phone_number}).

To view your profile via WhatsApp, please make sure:
• Your phone number in your TSC Swap profile matches this WhatsApp number
• The phone number format matches (e.g., 254712345678 or +254712345678)

You can update your phone number by logging in to your TSC Swap account and editing your profile.

Need help? Just ask! 😊"""
    
    elif intent == IntentType.FIND_SWAPS:
        # Get location from entities
        location = entities.get('location', '').strip() if entities.get('location') else None
        
        # Try to get user by phone number to find their level
        user = None
        if phone_number:
            user = get_user_by_phone(phone_number)
        
        if not user:
            return f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        
        ❌ I couldn't find your profile linked to this WhatsApp number.
        
        To find swaps, please make sure your phone number in your TSC Swap profile matches this WhatsApp number.
        
        You can update your phone number by logging in to your account."""
        
        # Get user's teaching level
        try:
            user_profile = user.profile
            user_level = user_profile.level if user_profile and user_profile.level else None
            
            if not user_level:
                completeness_msg = get_profile_completeness_links(user)
                return f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        
        ❌ Your profile doesn't have a teaching level set.
        
        Please log in to your TSC Swap account and set your teaching level to find matching swaps.{completeness_msg}"""
        except Exception as e:
            print(f"Error getting user profile: {str(e)}")
            return f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        
        ❌ Error loading your profile. Please try again later."""
        
        # Check if location is provided, if not, use swap preferences
        using_preferences = False
        preference_counties = []
        preference_county_names = []
        
        if not location:
            # Try to get swap preferences
            try:
                if hasattr(user, 'swappreference') and user.swappreference:
                    swap_pref = user.swappreference
                    
                    # Collect counties from desired_county and open_to_all
                    if swap_pref.desired_county:
                        preference_counties.append(swap_pref.desired_county)
                        preference_county_names.append(swap_pref.desired_county.name)
                    
                    # Add open_to_all counties
                    open_to_all_counties = swap_pref.open_to_all.all()
                    for county in open_to_all_counties:
                        if county not in preference_counties:
                            preference_counties.append(county)
                            preference_county_names.append(county.name)
                    
                    if preference_counties:
                        using_preferences = True
                        print(f"✅ Using swap preferences: {len(preference_counties)} counties")
            except Exception as e:
                print(f"Error getting swap preferences: {str(e)}")
        
        # Find matching swaps
        try:
            if using_preferences:
                matching_users, error_info = find_swaps_by_location(None, user_level, user, counties_list=preference_counties)
                search_location = ", ".join(preference_county_names[:3])
                if len(preference_county_names) > 3:
                    search_location += f" +{len(preference_county_names) - 3} more"
            else:
                matching_users, error_info = find_swaps_by_location(location, user_level, user)
                search_location = location
            
            # Find triangle swaps if location or preferences are provided
            triangle_swaps_text = ""
            if location or using_preferences:
                # For triangle swaps, use the first county name if using preferences
                triangle_location = location if location else (preference_county_names[0] if preference_county_names else None)
                if triangle_location:
                    triangle_swaps_text = find_triangle_swaps_for_whatsapp(user, triangle_location, user_level)
            
            # Build response
            if matching_users:
                response = format_swap_results(matching_users, search_location, user_level, using_preferences=using_preferences)
                
                # Append triangle swaps if found
                if triangle_swaps_text:
                    response += f"\n\n━━━━━━━━━━━━━━━━━━━━\n\n{triangle_swaps_text}"
            else:
                # Check if location was not found
                if error_info.get('no_counties_found') and location:
                    suggestions = error_info.get('suggestions', [])
                    if suggestions:
                        suggestions_text = "\n".join([f"   • {s}" for s in suggestions])
                        response = f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        📍 Location: {location}
        📚 Level: {user_level.name if user_level else 'Not set'}
        
        ❌ Location not found: "{location}"
        
        Did you mean one of these?
{suggestions_text}
        
        Try searching again with the correct county name! 😊"""
                    else:
                        response = f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        📍 Location: {location}
        📚 Level: {user_level.name if user_level else 'Not set'}
        
        ❌ Location not found: "{location}"
        
        Please check the spelling and try again. Make sure you're using a valid Kenyan county name.
        
        Examples:
        • Nairobi
        • Mombasa
        • Kisumu
        • Nakuru"""
                elif using_preferences:
                    response = f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        📍 Using Your Swap Preferences: {search_location}
        📚 Level: {user_level.name if user_level else 'Not set'}
        
        ℹ️ Since you didn't specify a location, I used your swap preferences.
        
        ❌ No direct matching swaps found in your preferred counties.
        
        Try:
        • Searching with a specific location (e.g., "Find swaps in Nairobi")
        • Updating your swap preferences to include more counties
        • Checking if your teaching level is correctly set in your profile"""
                    
                    # Add profile completeness check
                    completeness_msg = get_profile_completeness_links(user)
                    if completeness_msg:
                        response += completeness_msg
                    
                    # Append triangle swaps if found
                    if triangle_swaps_text:
                        response += f"\n\n━━━━━━━━━━━━━━━━━━━━\n\n{triangle_swaps_text}"
                elif location:
                    # Location was provided and found, but no matching swaps
                    # Check if user is secondary/high school
                    is_secondary = user_level and ('secondary' in user_level.name.lower() or 'high' in user_level.name.lower())
                    
                    if is_secondary:
                        response = f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        📍 Location: {location}
        📚 Level: {user_level.name if user_level else 'Not set'}
        
        😔 No matching swaps found in {location} right now.
        
        For secondary/high school teachers, I look for matches with:
        • Same teaching level (Secondary/High School)
        • Common subjects
        
        I couldn't find any teachers in {location} who meet both criteria.
        
        💡 *Tips to find more matches:*
        • Try searching in nearby counties
        • Make sure your subjects are set in your profile
        • Check back later - new teachers join regularly!
        
        Don't worry, we'll keep looking for you! 😊"""
                        
                        # Add profile completeness check
                        completeness_msg = get_profile_completeness_links(user)
                        if completeness_msg:
                            response += completeness_msg
                    else:
                        response = f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        📍 Location: {location}
        📚 Level: {user_level.name if user_level else 'Not set'}
        
        😔 No matching swaps found in {location} right now.
        
        I couldn't find any teachers in {location} who teach at the same level as you ({user_level.name if user_level else 'your level'}).
        
        💡 *Tips to find more matches:*
        • Try searching in nearby counties
        • Make sure your profile is complete
        • Check back later - new teachers join regularly!
        
        Don't worry, we'll keep looking for you! 😊"""
                        
                        # Add profile completeness check
                        completeness_msg = get_profile_completeness_links(user)
                        if completeness_msg:
                            response += completeness_msg
                    
                    # Append triangle swaps if found
                    if triangle_swaps_text:
                        response += f"\n\n━━━━━━━━━━━━━━━━━━━━\n\n{triangle_swaps_text}"
                else:
                    # No location and no preferences - ask user to set preferences or specify location
                    completeness_msg = get_profile_completeness_links(user)
                    response = f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        
        ℹ️ You didn't specify a location, and I couldn't find your swap preferences.
        
        To find swaps, please choose one of these options:
        
        1️⃣ *Specify a location* in your message:
           • "Find swaps in Nairobi"
           • "Find swaps in Mombasa"
        
        2️⃣ *Set your swap preferences* in your profile:
           🔗 https://www.tscswap.com/preferences/
           
           This will help me automatically search in your preferred counties when you ask for swaps.
        
        📚 Your Level: {user_level.name if user_level else 'Not set'}{completeness_msg}"""
                
                # Append triangle swaps if found
                if triangle_swaps_text:
                    response += f"\n\n━━━━━━━━━━━━━━━━━━━━\n\n{triangle_swaps_text}"
            
            return response
            
        except Exception as e:
            import traceback
            print(f"Error finding swaps: {str(e)}\n{traceback.format_exc()}")
            return f"""🔍 *Finding Swap Opportunities*
        
        Detected Intent: {intent_name} ✅
        
        ❌ Error searching for swaps. Please try again later.
        
        Error: {str(e)}"""
    
    elif intent == IntentType.REQUEST_CALL:
        # Get user by phone number to get their phone for the notification
        user = None
        requester_phone = phone_number or "Unknown"
        
        if phone_number:
            user = get_user_by_phone(phone_number)
            if user:
                try:
                    profile = user.profile
                    if profile and profile.phone:
                        requester_phone = profile.phone
                except Exception as e:
                    print(f"Error getting user phone: {str(e)}")
        
        # Send notification to admin via WhatsApp
        admin_phone = "254742134431"
        notification_message = f"Callback request from {requester_phone}"
        
        try:
            result = whatsapp_client.send_text_message(admin_phone, notification_message)
            if result:
                print(f"✅ Callback notification sent to admin: {admin_phone}")
            else:
                print(f"❌ Failed to send callback notification to admin")
        except Exception as e:
            print(f"Error sending callback notification: {str(e)}")
        
        return f"""📞 *Callback Request*

Detected Intent: {intent_name} ✅

I've noted your request for a callback. Our support team will contact you shortly!

In the meantime, feel free to ask me any questions about TSC Swap. 😊"""
    
    elif intent == IntentType.UPDATE_PREFERENCE:
        updates = []
        if entities.get('location'):
            updates.append(f"📍 Location: {entities['location']}")
        if entities.get('subject'):
            updates.append(f"📚 Subject: {entities['subject']}")
        
        response = f"""⚙️ *Update Preferences*
        
        Detected Intent: {intent_name} ✅
"""
        if updates:
            response += "\n" + "\n".join(updates)
        
        response += "\n\nI'll help you update your preferences. Please log in to your account to complete the update."
        
        return response
    
    elif intent == IntentType.ASK_QUESTION:
        # Answer questions about swaps, TSC transfers, etc.
        # Use conversation history if provided, otherwise get it
        if conversation_history is None:
            conversation_history = []
            if phone_number:
                user = get_user_by_phone(phone_number)
                if user:
                    # Get last 5 queries and their responses for context
                    try:
                        from chat.models import UserQuery, AIResponse
                        recent_queries = UserQuery.objects.filter(user=user).order_by('-created_at')[:5]
                        for query in reversed(recent_queries):  # Oldest first
                            try:
                                ai_response = query.ai_response
                                conversation_history.append({"role": "user", "content": query.message})
                                conversation_history.append({"role": "assistant", "content": ai_response.message})
                            except AIResponse.DoesNotExist:
                                # If no response exists, just add the user message
                                conversation_history.append({"role": "user", "content": query.message})
                    except Exception as e:
                        print(f"Error getting conversation history: {str(e)}")
        
        return answer_swap_question(message, user=None, conversation_history=conversation_history)
    
    else:
        # Unknown intent - try to answer as a question if it seems like one
        if any(word in message.lower() for word in ['how', 'what', 'when', 'where', 'why', 'who', 'can', 'do', 'does', 'is', 'are', '?']):
            # It looks like a question, try to answer it
            # Use conversation history if provided, otherwise get it
            if conversation_history is None:
                conversation_history = []
                if phone_number:
                    user = get_user_by_phone(phone_number)
                    if user:
                        # Get last 5 queries and their responses for context
                        try:
                            from chat.models import UserQuery, AIResponse
                            recent_queries = UserQuery.objects.filter(user=user).order_by('-created_at')[:5]
                            for query in reversed(recent_queries):  # Oldest first
                                try:
                                    ai_response = query.ai_response
                                    conversation_history.append({"role": "user", "content": query.message})
                                    conversation_history.append({"role": "assistant", "content": ai_response.message})
                                except AIResponse.DoesNotExist:
                                    # If no response exists, just add the user message
                                    conversation_history.append({"role": "user", "content": query.message})
                        except Exception as e:
                            print(f"Error getting conversation history: {str(e)}")
            
            return answer_swap_question(message, user=None, conversation_history=conversation_history)
        
        # Otherwise provide helpful guidance
        return f"""🤔 I received your message: "{message}"

I'm here to help with TSC Swap! Here's what I can assist you with:

📋 *View your profile information*
🔍 *Find swap opportunities*
❓ *Answer questions* about swaps, TSC transfers, requirements, etc.
📞 *Request a callback*
⚙️ *Update your preferences*

Try asking me:
• "Show my profile"
• "Find swaps in Nairobi"
• "How do swaps work?"
• "What documents do I need?"
• "What is a triangle swap?"

*About TSC Swap:*
We're an organization that helps teachers find swap mates and verify information to keep off scammers. We're not TSC, but we help guide you through the process! 😊

Need help? Just ask! 😊"""

@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """Handle incoming WhatsApp messages and webhook verification."""
    # Log immediately when function is called - this confirms the request reached Django
    import sys
    print("\n" + "="*50, file=sys.stderr)
    print("=== FUNCTION CALLED - REQUEST RECEIVED ===", file=sys.stderr)
    print("="*50, file=sys.stderr)
    print("\n" + "="*50)
    print("=== Incoming Webhook Request ===")
    print("="*50)
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    print(f"GET params: {dict(request.GET)}")
    print(f"POST params: {dict(request.POST)}")
    print(f"Content-Type: {request.content_type}")
    print(f"Content-Length: {request.headers.get('Content-Length', 'N/A')}")
    print(f"User-Agent: {request.headers.get('User-Agent', 'N/A')}")
    print(f"X-Forwarded-For: {request.headers.get('X-Forwarded-For', 'N/A')}")
    print(f"All Headers: {dict(request.headers)}")
    
    if request.method == "GET":
        try:
            # Handle webhook verification
            mode = request.GET.get("hub.mode")
            token = request.GET.get("hub.verify_token")
            challenge = request.GET.get("hub.challenge")
            
            print(f"\n--- Webhook Verification ---")
            print(f"Mode: {mode}")
            print(f"Token received: {token}")
            print(f"Expected token: {whatsapp_client.verify_token}")
            print(f"Challenge: {challenge}")
            
            if mode == "subscribe" and token == whatsapp_client.verify_token:
                print("✅ Webhook verification successful!")
                # Return challenge as plain text with 200 status
                response = HttpResponse(challenge, content_type='text/plain', status=200)
                return response
            else:
                print("❌ Webhook verification failed!")
                if mode != "subscribe":
                    print(f"Expected mode 'subscribe', got: {mode}")
                if token != whatsapp_client.verify_token:
                    print(f"Token mismatch. Expected: '{whatsapp_client.verify_token}', got: '{token}'")
                return HttpResponse("Verification token mismatch", content_type='text/plain', status=403)
        except Exception as e:
            import traceback
            error_msg = f"Error in webhook verification: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return HttpResponse(f"Error: {str(e)}", content_type='text/plain', status=500)
    
    elif request.method == "POST":
        print("\n" + "-"*50)
        print("=== POST REQUEST RECEIVED ===")
        print("-"*50)
        print(f"Request body length: {len(request.body)}")
        print(f"Request body (first 500 chars): {str(request.body)[:500]}")
        
        try:
            data = json.loads(request.body)
            print("\n--- Received Webhook Data ---")
            print(json.dumps(data, indent=2))
            
            # Check if this is a status update (delivery receipts, read receipts, etc.)
            # These don't have messages but we should still acknowledge them
            print(f"\n--- Webhook Object Type: {data.get('object', 'unknown')} ---")
            
            # Process the webhook event
            entries = data.get("entry", [])
            print(f"\n--- Processing {len(entries)} entry/entries ---")
            
            if not entries:
                print("⚠️ WARNING: No 'entry' found in webhook data!")
                print(f"Full data structure: {list(data.keys())}")
                print(f"Full data: {json.dumps(data, indent=2)}")
                # Still return success for status updates
                return JsonResponse({"status": "success"}, status=200)
            
            for entry_idx, entry in enumerate(entries):
                print(f"\n--- Processing Entry {entry_idx + 1} ---")
                changes = entry.get("changes", [])
                print(f"Found {len(changes)} change(s) in entry")
                
                for change_idx, change in enumerate(changes):
                    print(f"\n--- Processing Change {change_idx + 1} ---")
                    value = change.get("value", {})
                    print(f"Change keys: {list(value.keys())}")
                    
                    # Check metadata for phone number ID
                    metadata = value.get("metadata", {})
                    phone_number_id = metadata.get("phone_number_id")
                    display_phone = metadata.get("display_phone_number")
                    print(f"📱 Phone Number ID from webhook: {phone_number_id}")
                    print(f"📱 Display Phone Number: {display_phone}")
                    print(f"📱 Expected Phone Number ID: {whatsapp_client.phone_number_id}")
                    
                    # Verify phone number ID matches (optional check)
                    if phone_number_id and whatsapp_client.phone_number_id:
                        if str(phone_number_id) != str(whatsapp_client.phone_number_id):
                            print(f"⚠️ WARNING: Phone number ID mismatch!")
                            print(f"   Webhook: {phone_number_id}")
                            print(f"   Config: {whatsapp_client.phone_number_id}")
                            print(f"   Continuing anyway...")
                    
                    # Handle messages
                    if "messages" in value:
                        messages = value.get("messages", [])
                        print(f"✅ Found {len(messages)} message(s) in change")
                        for msg_idx, message in enumerate(messages):
                            print(f"\n--- Processing Message {msg_idx + 1} ---")
                            print(f"Message keys: {list(message.keys())}")
                            print(f"Message type: {message.get('type', 'N/A')}")
                            
                            if message.get("type") == "text":
                                print("✅ Message type is 'text' - processing...")
                                phone_number = message.get("from")
                                message_text = message.get("text", {}).get("body", "")
                                
                                print(f"\n--- Processing Message ---")
                                print(f"From: {phone_number}")
                                print(f"Message: {message_text}")
                                
                                if not phone_number:
                                    print("❌ No phone number in message")
                                    continue
                                
                                if not message_text:
                                    print("❌ No message text")
                                    continue
                                
                                # Get user by phone number (for saving queries)
                                user = None
                                if phone_number:
                                    user = get_user_by_phone(phone_number)
                                    if user:
                                        print(f"✅ User found for saving query: {user.email}")
                                    else:
                                        print(f"⚠️ User not found for phone {phone_number} - will not save query")
                                
                                # Detect intent
                                try:
                                    intent_detector = get_intent_detector()
                                    intent, entities = intent_detector.detect_intent(message_text)
                                    intent_name = intent.value.replace("_", " ").title()
                                    print(f"Detected intent: {intent_name}")
                                    if entities:
                                        print(f"Detected entities: {entities}")
                                except Exception as e:
                                    print(f"Error detecting intent: {str(e)}")
                                    intent = IntentType.UNKNOWN
                                    entities = {}
                                
                                # Save user query if user is found (before generating response to get history)
                                user_query = None
                                conversation_history = []
                                if user:
                                    try:
                                        from chat.models import UserQuery, AIResponse
                                        from django.db import transaction
                                        with transaction.atomic():
                                            user_query = UserQuery.objects.create(
                                                user=user,
                                                message=message_text
                                            )
                                            print(f"✅ Saved user query: {user_query.id}")
                                            
                                            # Get last 5 queries (excluding current one) for conversation history
                                            recent_queries = UserQuery.objects.filter(
                                                user=user
                                            ).exclude(pk=user_query.pk).order_by('-created_at')[:5]
                                            
                                            for query in reversed(recent_queries):  # Oldest first
                                                try:
                                                    ai_response = query.ai_response
                                                    conversation_history.append({"role": "user", "content": query.message})
                                                    conversation_history.append({"role": "assistant", "content": ai_response.message})
                                                except AIResponse.DoesNotExist:
                                                    # If no response exists, just add the user message
                                                    conversation_history.append({"role": "user", "content": query.message})
                                            
                                            print(f"✅ Retrieved {len(conversation_history)} messages for conversation history")
                                    except Exception as e:
                                        print(f"Error saving user query or getting history: {str(e)}")
                                
                                # Generate appropriate response (pass phone number and conversation history)
                                # Update generate_response to accept conversation_history if needed
                                response_text = generate_response(message_text, intent, entities, phone_number, conversation_history=conversation_history)
                                
                                # Save AI response if user query was saved
                                if user_query:
                                    try:
                                        from chat.models import AIResponse
                                        from django.db import transaction
                                        with transaction.atomic():
                                            AIResponse.objects.create(
                                                query=user_query,
                                                message=response_text
                                            )
                                            print(f"✅ Saved AI response for query: {user_query.id}")
                                    except Exception as e:
                                        print(f"Error saving AI response: {str(e)}")
                                
                                print(f"Sending response: {response_text}")
                                
                                result = whatsapp_client.send_text_message(phone_number, response_text)
                                if result:
                                    print("✅ Message sent successfully")
                                    print("Response:", json.dumps(result, indent=2))
                                else:
                                    print("❌ Failed to send message")
                                    print("Check WhatsApp API credentials and phone number ID")
                            else:
                                print(f"⚠️ Skipping message - type is '{message.get('type')}', not 'text'")
                    else:
                        print(f"⚠️ No 'messages' key in value. Available keys: {list(value.keys())}")
                        # Check if this is a status update
                        if "statuses" in value:
                            print("ℹ️ This appears to be a status update (delivery/read receipt), not a message")
                        else:
                            print(f"⚠️ Unknown webhook structure. Full value: {json.dumps(value, indent=2)}")
            
            print("\n" + "="*50)
            print("=== Returning Success Response ===")
            print("="*50)
            
            return JsonResponse({"status": "success"}, status=200)
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error: {str(e)}"
            print("\n" + "="*50)
            print("❌ JSON DECODE ERROR")
            print("="*50)
            print(error_msg)
            print(f"Request body: {request.body}")
            return JsonResponse({"status": "error", "message": error_msg}, status=400)
        except Exception as e:
            import traceback
            error_msg = f"Error processing webhook: {str(e)}\n{traceback.format_exc()}"
            print("\n" + "="*50)
            print("❌ EXCEPTION IN WEBHOOK HANDLER")
            print("="*50)
            print(error_msg)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "method not allowed"}, status=405)
