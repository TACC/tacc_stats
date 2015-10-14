import binascii
import os
from django.db import models
from datetime import timedelta, datetime
from django.conf import settings
from django.utils.encoding import python_2_unicode_compatible

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

@python_2_unicode_compatible
class Token(models.Model):
    """
    Customized authorization token model.
    """
    key = models.CharField(max_length=40, primary_key=True)
    user = models.OneToOneField(AUTH_USER_MODEL, related_name='auth_token')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True) 
    expires = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        if not self.expires:
            self.expires = datetime.now() + timedelta(days=365*20)
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __str__(self):
        return self.key