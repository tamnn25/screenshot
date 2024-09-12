from django.urls import path
from .views import take_screenshot, home

urlpatterns = [
    path('api/take-screenshot/', take_screenshot, name='take_screenshot'),
    path('', home, name='home')
]
