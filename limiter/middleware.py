import time
from django.core.cache import cache
from django.http import JsonResponse
from limiter.models import RateLimitLog, RateLimitWhitelist, RateLimitBlacklist

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.limits = {
            "/login": (3, 60),
            "/api/": (100, 60),
        }
        self.default_limit = (10, 60)

    def __call__(self, request):
        path = request.path
        identifier = self.get_identifier(request)

        if RateLimitBlacklist.objects.filter(identifier=identifier).exists():
            self.log(request, identifier, blocked=True)
            return JsonResponse({"detail": "Your access is blocked."}, status=403)

        if RateLimitWhitelist.objects.filter(identifier=identifier).exists():
            return self.get_response(request)

        max_requests, window = self.limits.get(path, self.default_limit)
        key = f"rl:{identifier}:{path}"
        now = int(time.time())

        record = cache.get(key)
        if record:
            count, first_request = record
            if now - first_request < window:
                if count >= max_requests:
                    self.log(request, identifier, blocked=True)
                    return JsonResponse(
                        {"detail": "Too many requests. Please try later."},
                        status=429,
                    )
                else:
                    cache.set(key, (count + 1, first_request), timeout=window)
            else:
                cache.set(key, (1, now), timeout=window)
        else:
            cache.set(key, (1, now), timeout=window)

        self.log(request, identifier, blocked=False)
        return self.get_response(request)

    def get_identifier(self, request):
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0]
        return request.META.get("REMOTE_ADDR")

    def log(self, request, identifier, blocked):
        path = request.path
        count = cache.get(f"rl:{identifier}:{path}")[0] if cache.get(f"rl:{identifier}:{path}") else 0
        RateLimitLog.objects.create(
            path=path,
            identifier=identifier,
            count=count,
            blocked=blocked
        )
