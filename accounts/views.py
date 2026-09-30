from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm, GuestNameForm
from .utils import get_or_create_guest_user


def register_view(request):
    """Handles user registration."""
    if request.user.is_authenticated and not request.user.is_guest:
        return redirect('rooms:lobby')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('rooms:lobby')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Handles registered user login."""
    if request.user.is_authenticated and not request.user.is_guest:
        return redirect('rooms:lobby')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('rooms:lobby')
    else:
        form = LoginForm()

    guest_form = GuestNameForm()
    return render(request, 'accounts/login.html', {
        'form': form,
        'guest_form': guest_form,
    })


def guest_login_view(request):
    """Initiates a guest session with an optional custom nickname."""
    if request.method == 'POST':
        form = GuestNameForm(request.POST)
        guest_name = form.cleaned_data.get('guest_name') if form.is_valid() else None
    else:
        guest_name = None

    guest_user = get_or_create_guest_user(request, custom_name=guest_name)
    login(request, guest_user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('rooms:lobby')


def logout_view(request):
    """Logs out the current user or guest."""
    logout(request)
    return redirect('core:landing')
