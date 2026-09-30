from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('guest/', views.guest_login_view, name='guest_login'),
    path('logout/', views.logout_view, name='logout'),
]
