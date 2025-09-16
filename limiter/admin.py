from django.contrib import admin
from limiter.models import RateLimitLog, RateLimitWhitelist, RateLimitBlacklist

@admin.register(RateLimitLog)
class RateLimitLogAdmin(admin.ModelAdmin):
    list_display = ("identifier", "path", "count", "timestamp", "blocked")
    list_filter = ("blocked", "path")


@admin.register(RateLimitWhitelist)
class RateLimitWhitelistAdmin(admin.ModelAdmin):
    list_display = ("identifier", "note")


@admin.register(RateLimitBlacklist)
class RateLimitBlacklistAdmin(admin.ModelAdmin):
    list_display = ("identifier", "note")
