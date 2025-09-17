from rest_framework.response import Response
from rest_framework import status
from functools import wraps
import time
import redis
from django.conf import settings


try:
    redis_client = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
    redis_client.ping()
except redis.ConnectionError:
    redis_client = None
    print("Connection error: Fallback mode active!")


def rate_limit(limit=10, period=60, user_type_key='user_type'):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user_type = getattr(request.user, user_type_key, 'normal')
            if user_type == 'premium':
                limit_adj = limit * 4
            else:
                limit_adj = limit

            key = f"rate:{request.user.id}" if request.user.is_authenticated else f"rate:anon:{request.META.get('REMOTE_ADDR')}:{request.path}"

            allowed = consume_token(key, limit_adj, period)
            if not allowed:
                retry_after = get_retry_after(key, period)
                return Response(
                    {"detail": "Rate limit exceeded."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        'Retry-After': str(retry_after),
                        'X-RateLimit-Limit': str(limit_adj),
                        'X-RateLimit-Remaining': '0',
                    }
                )

            response = view_func(request, *args, **kwargs)
            remaining = get_remaining_tokens(key, limit_adj)
            response['X-RateLimit-Limit'] = str(limit_adj)
            response['X-RateLimit-Remaining'] = str(remaining)
            return response

        return _wrapped_view
    return decorator

def consume_token(key, limit, period):
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

def get_remaining_tokens(key, limit):
    if not redis_client:
        return limit
    current_count = redis_client.zcard(key)
    return max(0, limit - current_count)

def get_retry_after(key, period):
    if not redis_client:
        return period
    oldest = redis_client.zrange(key, 0, 0, withscores=True)
    if not oldest:
        return period
    oldest_time = oldest[0][1]
    return max(0, int(period - (time.time() - oldest_time)))
