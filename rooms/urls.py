from django.urls import path
from . import views
from games import views as game_views

app_name = 'rooms'

urlpatterns = [
    path('', views.lobby_view, name='lobby'),
    path('create/', views.create_room_view, name='create'),
    path('join/', views.join_room_view, name='join'),
    path('<str:room_code>/', views.room_detail_view, name='room_detail'),
    path('<str:room_code>/play/', game_views.tictactoe_play_view, name='tictactoe_play'),
    path('<str:room_code>/trivia/', game_views.trivia_play_view, name='trivia_play'),
]
