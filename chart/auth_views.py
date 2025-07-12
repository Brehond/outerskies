import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.core.validators import validate_email
from django.forms import ValidationError as FormValidationError
from .models import User, Chart, PasswordResetToken
from .forms import UserRegistrationForm, UserProfileForm, PasswordChangeForm
import json
import re

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@ensure_csrf_cookie
def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('chart_form')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.set_password(form.cleaned_data['password1'])
                    user.save()

                    # Log the registration
                    logger.info(f"New user registered: {user.username} from IP: {get_client_ip(request)}")

                    # Auto-login the user
                    login(request, user)
                    messages.success(request, 'Account created successfully! Welcome to Outer Skies.')

                    return redirect('chart_form')
            except Exception as e:
                logger.error(f"Registration error: {e}")
                messages.error(request, 'An error occurred during registration. Please try again.')
    else:
        form = UserRegistrationForm()

    return render(request, 'chart/auth/register.html', {'form': form})


@ensure_csrf_cookie
def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('chart_form')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me') == 'on'

        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)

                # Update last login IP
                user.last_login_ip = get_client_ip(request)
                user.save()

                # Set session expiry based on remember me
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires when browser closes

                logger.info(f"User logged in: {user.username} from IP: {get_client_ip(request)}")
                messages.success(request, f'Welcome back, {user.username}!')

                # Redirect to next page or default
                next_url = request.GET.get('next', 'chart_form')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
                logger.warning(f"Failed login attempt for username: {username} from IP: {get_client_ip(request)}")
        else:
            messages.error(request, 'Please provide both username and password.')

    return render(request, 'chart/auth/login.html')


@login_required
def logout_view(request):
    """User logout view"""
    username = request.user.username
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    logger.info(f"User logged out: {username}")
    return redirect('auth:login')


@login_required
def profile_view(request):
    """User profile view and edit"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    # GeocodingService removed for now
                    user.save()
                    messages.success(request, 'Profile updated successfully!')
                    logger.info(f"Profile updated for user: {user.username}")

            except Exception as e:
                logger.error(f"Profile update error: {e}")
                messages.error(request, 'An error occurred while updating your profile.')
    else:
        form = UserProfileForm(instance=request.user)

    # Get user's charts
    charts = request.user.charts.all()[:10]  # Last 10 charts

    context = {
        'form': form,
        'charts': charts,
        'total_charts': request.user.charts.count(),
    }

    return render(request, 'chart/auth/profile.html', context)


@login_required
def change_password_view(request):
    """Change password view"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            try:
                user = form.save()
                messages.success(request, 'Password changed successfully!')
                logger.info(f"Password changed for user: {user.username}")
                return redirect('auth:profile')
            except Exception as e:
                logger.error(f"Password change error: {e}")
                messages.error(request, 'An error occurred while changing your password.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'chart/auth/change_password.html', {'form': form})


def password_reset_request_view(request):
    """Request password reset"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                # Create password reset token
                token = PasswordResetToken.objects.create(
                    user=user,
                    expires_at=timezone.now() + timezone.timedelta(hours=24)
                )

                # Send reset email
                reset_url = request.build_absolute_uri(
                    f'/auth/reset-password/{token.token}/'
                )

                context = {
                    'user': user,
                    'reset_url': reset_url,
                    'expires_in': '24 hours'
                }

                email_body = render_to_string('chart/auth/password_reset_email.html', context)

                send_mail(
                    subject='Password Reset Request - Outer Skies',
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )

                messages.success(request, 'Password reset instructions have been sent to your email.')
                logger.info(f"Password reset requested for user: {user.username}")

            except User.DoesNotExist:
                # Don't reveal if email exists or not
                messages.success(request, 'If an account with that email exists, password reset instructions have been sent.')
            except Exception as e:
                logger.error(f"Password reset request error: {e}")
                messages.error(request, 'An error occurred while processing your request.')

    return render(request, 'chart/auth/password_reset_request.html')


def password_reset_confirm_view(request, token):
    """Confirm password reset with token"""
    try:
        reset_token = PasswordResetToken.objects.get(
            token=token,
            is_used=False,
            expires_at__gt=timezone.now()
        )

        if request.method == 'POST':
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')

            if password1 and password2 and password1 == password2:
                try:
                    # Validate password
                    from django.contrib.auth.password_validation import validate_password
                    validate_password(password1, reset_token.user)

                    # Update password
                    reset_token.user.set_password(password1)
                    reset_token.user.save()

                    # Mark token as used
                    reset_token.is_used = True
                    reset_token.save()

                    messages.success(request, 'Your password has been reset successfully. You can now log in.')
                    logger.info(f"Password reset completed for user: {reset_token.user.username}")

                    return redirect('auth:login')

                except ValidationError as e:
                    messages.error(request, f'Password validation error: {e}')
            else:
                messages.error(request, 'Passwords do not match.')

        return render(request, 'chart/auth/password_reset_confirm.html')

    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Invalid or expired password reset link.')
        return redirect('auth:password_reset_request')


@login_required
def chart_history_view(request):
    """View user's chart history"""
    charts = request.user.charts.all().order_by('-created_at')

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(charts, 12)  # 12 charts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_charts': charts.count(),
    }

    return render(request, 'chart/auth/chart_history.html', context)


@login_required
def delete_chart_view(request, chart_id):
    """Delete a user's chart"""
    if request.method == 'POST':
        try:
            chart = get_object_or_404(Chart, id=chart_id, user=request.user)
            chart_name = chart.name or str(chart.birth_date)
            chart.delete()
            messages.success(request, f'Chart "{chart_name}" has been deleted.')
            logger.info(f"Chart deleted: {chart_id} by user: {request.user.username}")
        except Exception as e:
            logger.error(f"Chart deletion error: {e}")
            messages.error(request, 'An error occurred while deleting the chart.')

    return redirect('auth:chart_history')


@login_required
def toggle_favorite_chart_view(request, chart_id):
    """Toggle favorite status of a chart"""
    if request.method == 'POST':
        try:
            chart = get_object_or_404(Chart, id=chart_id, user=request.user)
            chart.is_favorite = not chart.is_favorite
            chart.save()

            status = 'favorited' if chart.is_favorite else 'unfavorited'
            messages.success(request, f'Chart has been {status}.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'is_favorite': chart.is_favorite})

        except Exception as e:
            logger.error(f"Toggle favorite error: {e}")
            messages.error(request, 'An error occurred while updating the chart.')

    return redirect('auth:chart_history')

# API Views for AJAX requests


@require_http_methods(["POST"])
def check_username_availability(request):
    """Check if username is available"""
    username = request.POST.get('username', '').strip()

    if not username:
        return JsonResponse({'available': False, 'error': 'Username is required'})

    if len(username) < 3:
        return JsonResponse({'available': False, 'error': 'Username must be at least 3 characters'})

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return JsonResponse({'available': False, 'error': 'Username can only contain letters, numbers, and underscores'})

    is_available = not User.objects.filter(username=username).exists()
    return JsonResponse({'available': is_available})


@require_http_methods(["POST"])
def check_email_availability(request):
    """Check if email is available"""
    email = request.POST.get('email', '').strip()

    if not email:
        return JsonResponse({'available': False, 'error': 'Email is required'})

    try:
        validate_email(email)
    except FormValidationError:
        return JsonResponse({'available': False, 'error': 'Invalid email format'})

    is_available = not User.objects.filter(email=email).exists()
    return JsonResponse({'available': is_available})
