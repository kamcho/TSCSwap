from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def chat_widget(context):
    """
    Renders the chat widget HTML.
    Usage in templates: {% load chat_tags %} {% chat_widget %}
    """
    # Show chat widget to all users, including non-authenticated ones
    return mark_safe(render_to_string('chat/chat_widget.html'))
