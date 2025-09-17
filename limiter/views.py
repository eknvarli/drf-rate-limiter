from rest_framework.views import Response
from rest_framework.decorators import api_view
from limiter.decorators import rate_limit


@api_view(['GET'])
@rate_limit(limit=5, period=60)
def hello(request):
    return Response({'message': 'George is working!'})