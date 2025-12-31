import os
import re
import requests
import json
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

📞 *Request Support*
   • Get a callback from our team
   • Contact support

⚙️ *Update Preferences*
   • Change your location
   • Update your subject preferences
   • Modify your swap settings

Just send me a message and I'll help you! 😊

For example:
• "Show my profile"
• "Find swaps in Nairobi"
• "Update my preferences"
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
    if normalized.startswith('0') and len(normalized) == 10:
        normalized = '254' + normalized[1:]
    
    # If it's 9 digits starting with 7 (without leading 0), add 254
    if len(normalized) == 9 and normalized.startswith('7'):
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

def find_swaps_by_location(location: str, user_level, asking_user) -> list:
    """
    Find users who teach in a specific location and share the same teaching level.
    
    Args:
        location: Location name (e.g., "Nairobi")
        user_level: The Level object of the asking user
        asking_user: The User object who is asking for swaps
    
    Returns:
        List of User objects matching the criteria
    """
    try:
        from users.models import PersonalProfile
        from home.models import Counties, Schools
        
        if not user_level:
            return []
        
        # Find counties matching the location name (case-insensitive)
        counties = Counties.objects.filter(name__icontains=location) if location else Counties.objects.none()
        
        if not counties.exists() and location:
            print(f"⚠️ No counties found matching: {location}")
            return []
        
        # Find schools in those counties (through ward → constituency → county)
        # Schools are linked: school.ward.constituency.county
        schools_query = Schools.objects.filter(
            ward__constituency__county__in=counties,
            level=user_level  # Same teaching level
        ).select_related('ward__constituency__county', 'level')
        
        print(f"🔍 Found {schools_query.count()} schools in {location} at level {user_level.name}")
        
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
        
        return list(matching_users)
        
    except Exception as e:
        import traceback
        print(f"❌ Error finding swaps by location: {str(e)}\n{traceback.format_exc()}")
        return []

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

def format_swap_results(matching_profiles, location: str, user_level) -> str:
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
📚 Level: {user_level.name if user_level else 'Not set'}

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
            return """❌ *Profile Not Found*

Your account exists, but you haven't set up your personal profile yet.

Please log in to your TSC Swap account and complete your profile setup to view your information here."""
        
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
        
        return response
        
    except Exception as e:
        import traceback
        print(f"Error formatting profile: {str(e)}\n{traceback.format_exc()}")
        return f"""❌ *Error Loading Profile*

I encountered an error while loading your profile information. Please try again later or contact support.

Error: {str(e)}"""

def generate_response(message: str, intent: IntentType, entities: dict, phone_number: str = None) -> str:
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
                return f"""🔍 *Finding Swap Opportunities*

Detected Intent: {intent_name} ✅

❌ Your profile doesn't have a teaching level set.

Please log in to your TSC Swap account and set your teaching level to find matching swaps."""
        except Exception as e:
            print(f"Error getting user profile: {str(e)}")
            return f"""🔍 *Finding Swap Opportunities*

Detected Intent: {intent_name} ✅

❌ Error loading your profile. Please try again later."""
        
        # Find matching swaps
        try:
            matching_users = find_swaps_by_location(location, user_level, user)
            
            # Find triangle swaps if location is provided
            triangle_swaps_text = ""
            if location:
                triangle_swaps_text = find_triangle_swaps_for_whatsapp(user, location, user_level)
            
            # Build response
            if matching_users:
                response = format_swap_results(matching_users, location, user_level)
                
                # Append triangle swaps if found
                if triangle_swaps_text:
                    response += f"\n\n━━━━━━━━━━━━━━━━━━━━\n\n{triangle_swaps_text}"
            else:
                response = f"""🔍 *Finding Swap Opportunities*

Detected Intent: {intent_name} ✅
📍 Location: {location or 'Any location'}
📚 Level: {user_level.name if user_level else 'Not set'}

❌ No direct matching swaps found.

I couldn't find any teachers in {location or 'your specified location'} who teach at the same level as you ({user_level.name if user_level else 'your level'}).

Try:
• Searching in a different location
• Checking if your teaching level is correctly set in your profile"""
                
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
    
    else:
        # Unknown intent - provide helpful guidance
        return f"""🤔 I received your message: "{message}"

Detected Intent: {intent_name}

I'm here to help with TSC Swap! Here's what I can assist you with:

📋 View your profile information
🔍 Find swap opportunities
📞 Request a callback
⚙️ Update your preferences

Try asking me:
• "Show my profile"
• "Find swaps"
• "Update my location"

Need help? Just ask! 😊"""

@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """Handle incoming WhatsApp messages and webhook verification."""
    print("\n=== Incoming Webhook Request ===")
    print(f"Method: {request.method}")
    print(f"GET params: {dict(request.GET)}")
    print(f"Headers: {dict(request.headers)}")
    
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
        try:
            data = json.loads(request.body)
            print("\n--- Received Webhook Data ---")
            print(json.dumps(data, indent=2))
            
            # Process the webhook event
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Handle messages
                    if "messages" in value:
                        for message in value.get("messages", []):
                            if message.get("type") == "text":
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
                                
                                # Generate appropriate response (pass phone number for profile lookup)
                                response_text = generate_response(message_text, intent, entities, phone_number)
                                
                                print(f"Sending response: {response_text}")
                                
                                result = whatsapp_client.send_text_message(phone_number, response_text)
                                if result:
                                    print("✅ Message sent successfully")
                                    print("Response:", json.dumps(result, indent=2))
                                else:
                                    print("❌ Failed to send message")
            
            return JsonResponse({"status": "success"}, status=200)
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error: {str(e)}"
            print(error_msg)
            return JsonResponse({"status": "error", "message": error_msg}, status=400)
        except Exception as e:
            import traceback
            error_msg = f"Error processing webhook: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "method not allowed"}, status=405)
