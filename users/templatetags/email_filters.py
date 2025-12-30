from django import template

register = template.Library()

@register.filter
def mask_email(email):
    """
    Masks an email address, showing only the first part before @
    Example: "user@example.com" -> "user@***"
    """
    if not email or '@' not in str(email):
        return email
    
    local_part = str(email).split('@')[0]
    return f"{local_part}@***"
