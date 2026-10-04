from django.urls import path
from rooms import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('create/', views.create_room_view, name='create_room'),
    path('join/', views.join_room_view, name='join_room'),
    path('room/<str:room_code>/', views.room_detail_view, name='room_detail'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
]
