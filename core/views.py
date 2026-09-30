from django.shortcuts import render
from games.registry import game_registry


def landing_page(request):
    """
    Renders the platform landing page showcasing active games, 
    quick room creation options, and platform overview.
    """
    available_games = game_registry.list_games()
    return render(request, 'core/index.html', {
        'available_games': available_games,
    })
