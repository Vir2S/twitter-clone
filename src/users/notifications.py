from django.db.models.notifications import save_post

from django.contrib.auth.models import User

from django.dispatch import receiver

from .models import Profile

# notification that gets fired after the user is saved
@receiver(save_post, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)