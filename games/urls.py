from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    path('', views.game_library_view, name='library'),
    path('play/<str:room_code>/', views.tictactoe_play_view, name='play'),
    path('<str:game_id>/', views.game_detail_view, name='detail'),
]
