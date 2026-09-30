"""
URL configuration for gaming_hub project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls', namespace='core')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('accounts/social/', include('allauth.urls')),
    path('rooms/', include('rooms.urls', namespace='rooms')),
    path('games/', include('games.urls', namespace='games')),
]
