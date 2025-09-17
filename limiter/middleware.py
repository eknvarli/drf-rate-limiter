from django.conf import settings
from django.http import JsonResponse
import time
import redis


try:
    redis_client = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
    redis_client.ping()
except redis.ConnectionError:
    redis_client = None
    print('Connection error: Fallback mode active!')


RATE_LIMITS = {
    '/api/fast/': {'normal': (5,60), 'premium': (20, 60)},
    'api/slow/': {'normal': (50,60), 'premium': (200, 60)},
}


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        user_type = getattr(request.user, 'user_type', 'normal')
        
        limit, period = self.get_limit(path, user_type)
        if limit is None:
            return self.get_response(request)
        

        key = f"rate:{request.user.id}:{path}" if request.user.is_authenticated else f"rate:anon:{request.META.get('REMOTE_ADDR')}:{path}"
        allowed = self.consume_token(key, limit, period)
        if not allowed:
            retry_after = self.get_retry_after(key, period)
            return JsonResponse(
                {'detail': 'Rate limit exceeded.'},
                status=429,
                headers={
                    'Retry-After': str(retry_after),
                    'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Remaining': '0',
                }
            )
        
        response = self.get_response(request)
        remaining = self.get_remaining_tokens(key, limit)
        response['X-RateLimit-Limit'] = str(limit)
        response['X-RateLimit-Remaining'] = str(remaining)

    
    def get_limit(self, path, user_type):
        for endpoint, limits in RATE_LIMITS.items():
            if path.startswith(endpoint):
                return limits.get(user_type, limits.get('normal', (None, None)))
        return None, None

    def consume_token(self, key, limit, period):
        if not redis_client:
            return True
        now = int(time.time())
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now - period)
        pipe.zcard(key)
        pipe.execute()

        current_count = redis_client.zcard(key)
        if current_count >= limit:
            return False

        redis_client.zadd(key, {str(now): now})
        redis_client.expire(key, period)
        return True

    def get_remaining_tokens(self, key, limit):
        if not redis_client:
            return limit
        current_count = redis_client.zcard(key)
        return max(0, limit - current_count)

    def get_retry_after(self, key, period):
        if not redis_client:
            return period
        oldest = redis_client.zrange(key, 0, 0, withscores=True)
        if not oldest:
            return period
        oldest_time = oldest[0][1]
        return max(0, int(period - (time.time() - oldest_time)))