from django.urls import path
from rooms import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('create/', views.create_room_view, name='create_room'),
    path('join/', views.join_room_view, name='join_room'),
    path('room/<str:room_code>/', views.room_detail_view, name='room_detail'),
    path('room/<str:room_code>/status/', views.room_status_api, name='room_status'),
    path('room/<str:room_code>/toggle-ready/', views.toggle_ready_api, name='toggle_ready'),
    path('room/<str:room_code>/start/', views.start_game_api, name='start_game_api'),
    path('games/<str:game_type>/<str:room_code>/', views.room_detail_view, name='game_room_detail'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
]
