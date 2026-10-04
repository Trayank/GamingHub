from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    path('', views.game_library_view, name='library'),
    path('play/<str:room_code>/', views.tictactoe_play_view, name='play'),
    path('trivia/<str:room_code>/', views.trivia_play_view, name='trivia_play'),
    path('ludo/<str:room_code>/', views.ludo_play_view, name='ludo_play'),
    path('<str:game_id>/', views.game_detail_view, name='detail'),
]
