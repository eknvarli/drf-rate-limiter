from django.urls import path
from limiter.views import *

urlpatterns = [
    path('', hello, name='hello'),
]