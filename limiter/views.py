from rest_framework.views import Response
from rest_framework.decorators import api_view


@api_view(['GET'])
def hello(request):
    return Response({'message': 'George is working!'})