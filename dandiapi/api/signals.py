from corsheaders.signals import check_request_enabled
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


@receiver(check_request_enabled)
def cors_allow_anyone_read_only(sender, request, **kwargs):
    """Allow any read-only request from any origin."""
    return request.method in ('GET', 'HEAD', 'OPTIONS')


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """Create an auth token for every new user."""
    if created:
        Token.objects.create(user=instance)
