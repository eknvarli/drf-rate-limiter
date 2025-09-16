from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class RateLimitLog(models.Model):
    path = models.CharField(max_length=255)
    identifier = models.CharField(max_length=255)
    count = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    blocked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.identifier} - {self.path} ({'blocked' if self.blocked else 'ok'})"


class RateLimitWhitelist(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Whitelist: {self.identifier}"


class RateLimitBlacklist(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Blacklist: {self.identifier}"