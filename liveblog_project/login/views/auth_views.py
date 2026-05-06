"""Authentication views: login, register, logout."""
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from login.forms import CustomUserCreationForm, LoginForm
from login.middleware import is_user_online, clear_user_online
from login.models import Profile
from login.turnstile import client_ip_from_request, verify_turnstile_response


@ratelimit(key='ip', rate=settings.RATELIMIT_LOGIN_RATE, method='POST', block=False)
def login_view(request):
    if request.user.is_authenticated:
        return redirect('login_app:profile', username=request.user.username)

    if request.method == 'POST':
        if getattr(request, 'limited', False):
            form = LoginForm(request.POST or None)
            form.add_error(
                None,
                'Too many login attempts from this network. Please wait and try again later.',
            )
            return render(request, 'accounts/login.html', {'form': form})
        form = LoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember = form.cleaned_data.get('remember')

            lookup = User.objects.select_related('profile').filter(username=username).first()
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if is_user_online(user):
                    form.add_error(None, "User already online")
                else:
                    login(request, user)
                    if remember:
                        request.session.set_expiry(1209600)  # 2 weeks
                    else:
                        request.session.set_expiry(0)
                    messages.success(request, f'Welcome back, {user.username}!')
                    next_url = request.GET.get('next', '')
                    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                        return redirect(next_url)
                    return redirect('login_app:profile', username=user.username)
            else:
                if not lookup or not lookup.check_password(password):
                    form.add_error(None, 'Invalid username or password.')
                elif not lookup.is_active:
                    try:
                        if lookup.profile.trust_banned:
                            from admin_panel.services.trust_score_service import format_trust_ban_login_message
                            form.add_error(None, format_trust_ban_login_message(lookup))
                        else:
                            form.add_error(None, "Your account has been disabled.")
                    except Exception:
                        form.add_error(None, "Your account has been disabled.")
                else:
                    form.add_error(None, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@ratelimit(key='ip', rate=settings.RATELIMIT_REGISTER_RATE, method='POST', block=False)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('login_app:profile', username=request.user.username)

    if request.method == 'POST':
        if getattr(request, 'limited', False):
            form = CustomUserCreationForm(request.POST)
            form.add_error(
                None,
                'Too many registration attempts from this network. Please try again later.',
            )
            return render(request, 'accounts/register.html', {'form': form})
        secret = getattr(settings, 'TURNSTILE_SECRET_KEY', '').strip()
        if secret:
            token = request.POST.get('cf-turnstile-response', '')
            if not verify_turnstile_response(
                token, secret, client_ip_from_request(request)
            ):
                form = CustomUserCreationForm(request.POST, request.FILES)
                form.add_error(
                    None,
                    'Security check failed. Please complete the verification and try again.',
                )
                return render(request, 'accounts/register.html', {'form': form})
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()

            avatar_url = form.cleaned_data.get('avatar_url', '') or ''
            avatar_file = form.cleaned_data.get('avatar_file')

            profile, _ = Profile.objects.get_or_create(user=user)

            if avatar_file:
                profile.set_avatar_file(avatar_file)
                profile.save()
            elif avatar_url:
                profile.avatar_url = avatar_url
                profile.save()

            messages.success(request, 'Registration successful. You can log in now.')
            return redirect('login_app:login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        clear_user_online(request.user)
    logout(request)
    return redirect('login_app:login')
