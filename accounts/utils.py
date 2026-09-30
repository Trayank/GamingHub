import uuid
from django.contrib.auth import get_user_model

User = get_user_model()


class GuestUserMiddleware:
    """
    Middleware that ensures every anonymous visitor has a unique guest session ID
    and guest display name stored in their session.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.session.session_key:
            try:
                request.session.save()
            except Exception:
                # Prevent crash on read-only environments or unmigrated databases
                pass

        if 'guest_id' not in request.session:
            guest_uuid = uuid.uuid4().hex[:8]
            request.session['guest_id'] = guest_uuid
            request.session['guest_name'] = f"Player_{guest_uuid[:4]}"

        response = self.get_response(request)
        return response


def get_or_create_guest_user(request, custom_name=None):
    """
    Retrieves or creates a temporary guest User instance for session-backed guest play.
    """
    guest_id = request.session.get('guest_id')
    if not guest_id:
        guest_uuid = uuid.uuid4().hex[:8]
        request.session['guest_id'] = guest_uuid
        guest_id = guest_uuid

    username = f"guest_{guest_id}"
    display_name = custom_name or request.session.get('guest_name', f"Guest_{guest_id[:4]}")
    request.session['guest_name'] = display_name

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': display_name,
            'is_guest': True,
        }
    )
    return user
