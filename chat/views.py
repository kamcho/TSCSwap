import json
import os
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from dotenv import load_dotenv
from openai import OpenAI

from .models import AIResponse, UserQuery

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(env_path)

# Initialize OpenAI client
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")

client = OpenAI(api_key=openai_api_key)

@require_http_methods(["GET", "POST"])
@csrf_exempt
def chat_view(request):
    """
    Chat view that works for both authenticated and anonymous users.
    - Authenticated users: Chat history is saved and retrieved
    - Anonymous users: Chat works but history is not saved (session-based only)
    """
    if request.method == 'GET':
        # Return chat history for authenticated users only
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'chats': []})  # No history for anonymous users
                
            chats = UserQuery.objects.filter(user=request.user).order_by('-created_at')[:10]
            chat_history = []
            
            for chat in chats:
                try:
                    ai_response = chat.ai_response
                    chat_history.append({
                        'user_message': chat.message,
                        'ai_message': ai_response.message,
                        'timestamp': chat.created_at.isoformat()
                    })
                except AIResponse.DoesNotExist:
                    continue
                    
            return JsonResponse({'chats': chat_history})
            
        except Exception as e:
            print(f"Chat GET error: {str(e)}")
            return JsonResponse({'chats': []})  # Return empty on error instead of 500
    
    elif request.method == 'POST':
        try:
            # Parse JSON data from request body
            data = json.loads(request.body.decode('utf-8'))
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)
            
            # For authenticated users, save chat history
            if request.user.is_authenticated:
                with transaction.atomic():
                    # Save user query
                    user_query = UserQuery.objects.create(
                        user=request.user,
                        message=user_message
                    )
                    
                    try:
                        # Get the last 9 previous messages (plus current makes 10)
                        previous_messages = []
                        previous_chats = UserQuery.objects.filter(user=request.user).exclude(pk=user_query.pk).order_by('-created_at')[:9]
                        
                        # Format previous messages in reverse chronological order (oldest first)
                        for chat in reversed(previous_chats):
                            try:
                                ai_response = chat.ai_response
                                previous_messages.append({"role": "user", "content": chat.message})
                                previous_messages.append({"role": "assistant", "content": ai_response.message})
                            except AIResponse.DoesNotExist:
                                continue
                        
                        # Prepare the messages list with system message, previous messages, and current message
                        messages = [
                            {"role": "system", "content": """You are a helpful assistant for TSC Swap, a platform that helps teachers find suitable swap mates—other teachers who wish to exchange teaching locations in line with TSC guidelines.
Your role is to assist users by providing clear, accurate, and supportive information about teacher swaps, eligibility, and the matching process.
If users ask questions outside this scope, politely explain your role and guide the conversation back to topics related to TSC Swap.
Be friendly, concise, and helpful, and always aim to support teachers in finding suitable swap opportunities."""}
                        ]
                        
                        # Add previous messages and current message
                        messages.extend(previous_messages)
                        messages.append({"role": "user", "content": user_message})
                        
                        # Get response from OpenAI with conversation history
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=messages,
                            temperature=0.7,
                            max_tokens=500
                        )
                        
                        ai_message = response.choices[0].message.content.strip()
                        
                        # Save AI response
                        AIResponse.objects.create(
                            query=user_query,
                            message=ai_message
                        )
                        
                        return JsonResponse({
                            'success': True,
                            'user_message': user_message,
                            'ai_message': ai_message,
                            'timestamp': timezone.now().isoformat()
                        })
                        
                    except Exception as e:
                        # Log the error but don't expose internal details to the client
                        print(f"Error generating AI response: {str(e)}")
                        return JsonResponse({
                            'success': False,
                            'error': 'Sorry, there was an error processing your request. Please try again later.'
                        }, status=500)
            
            else:
                # For anonymous users, don't save history but still provide AI response
                try:
                    # Prepare the messages list with system message and current message only
                    messages = [
                        {"role": "system", "content": """You are a helpful assistant for TSC Swap, a platform that helps teachers find suitable swap mates—other teachers who wish to exchange teaching locations in line with TSC guidelines.
Your role is to assist users by providing clear, accurate, and supportive information about teacher swaps, eligibility, and the matching process.
If users ask questions outside this scope, politely explain your role and guide the conversation back to topics related to TSC Swap.
Be friendly, concise, and helpful.

IMPORTANT: This user is NOT logged in. If they ask you to:
- Find them a swap
- Search for swap opportunities
- Match them with other teachers
- Help them create a swap request
- Show available swaps in a specific location
- Or any action that requires being a registered user

You MUST respond by telling them they need to login or register first to use these features. Include these exact links in your response:
- Login: /users/login/
- Register: /users/signup/

Format your response like this when they need to login:
"To find swaps and connect with other teachers, you'll need to create an account or login first! 

👉 [Login here](/users/login/) if you already have an account
👉 [Register here](/users/signup/) to create a new account

Once logged in, you'll be able to browse swaps, create your own swap requests, and get personalized matches based on your preferences!"

For general questions about how TSC Swap works, eligibility, or the swap process, you can answer those without requiring login."""},
                        {"role": "user", "content": user_message}
                    ]
                    
                    # Get response from OpenAI (no conversation history for anonymous users)
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    ai_message = response.choices[0].message.content.strip()
                    
                    return JsonResponse({
                        'success': True,
                        'user_message': user_message,
                        'ai_message': ai_message,
                        'timestamp': timezone.now().isoformat()
                    })
                    
                except Exception as e:
                    # Log the error but don't expose internal details to the client
                    print(f"Error generating AI response for anonymous user: {str(e)}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Sorry, there was an error processing your request. Please try again later.'
                    }, status=500)
                    
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
