# views.py

import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from .models import SubscriptionPlan, UserSubscription, Payment, Coupon
from .stripe_utils import StripeService, handle_stripe_webhook, create_default_plans
import stripe

logger = logging.getLogger(__name__)


@login_required
def pricing_view(request):
    """Display pricing plans"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')

    # Get user's current subscription
    current_subscription = getattr(request.user, 'subscription', None)

    context = {
        'plans': plans,
        'current_subscription': current_subscription,
        'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY,
    }

    return render(request, 'payments/pricing.html', context)


@login_required
def subscription_management(request):
    """User subscription management page"""
    subscription = getattr(request.user, 'subscription', None)

    if not subscription:
        messages.warning(request, 'You don\'t have an active subscription.')
        return redirect('payments:pricing')

    # Get payment history
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')[:10]

    # Get available plans for upgrade/downgrade
    available_plans = SubscriptionPlan.objects.filter(is_active=True).exclude(id=subscription.plan.id)

    context = {
        'subscription': subscription,
        'payments': payments,
        'available_plans': available_plans,
        'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY,
    }

    return render(request, 'payments/subscription_management.html', context)


@login_required
@require_http_methods(["POST"])
def create_subscription(request):
    """Create a new subscription"""
    try:
        # Use cached body if available (from middleware), otherwise read from request
        if hasattr(request, '_body_cache'):
            if isinstance(request._body_cache, str):
                if request._body_cache.strip():
                    data = json.loads(request._body_cache)
                else:
                    data = {}
            else:
                if request._body_cache:
                    data = json.loads(request._body_cache.decode('utf-8'))
                else:
                    data = {}
        else:
            if request.body:
                data = json.loads(request.body)
            else:
                data = {}
        plan_id = data.get('plan_id')
        payment_method_id = data.get('payment_method_id')
        coupon_code = data.get('coupon_code')
        _billing_cycle = data.get('billing_cycle', 'monthly')

        # Validate plan
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

        # Check if user already has a subscription
        if hasattr(request.user, 'subscription') and request.user.subscription.is_active:
            return JsonResponse({
                'error': 'You already have an active subscription. Please manage your existing subscription.'
            }, status=400)

        # Create subscription
        subscription = StripeService.create_subscription(
            user=request.user,
            plan=plan,
            payment_method_id=payment_method_id,
            coupon_code=coupon_code
        )

        return JsonResponse({
            'success': True,
            'subscription_id': subscription.id,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice.payment_intent else None,
            'redirect_url': '/payments/subscription-success/'
        })

    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        return JsonResponse({'error': 'An error occurred while creating your subscription.'}, status=500)


@login_required
@require_http_methods(["POST"])
def cancel_subscription(request):
    """Cancel user subscription"""
    try:
        # Use cached body if available (from middleware), otherwise read from request
        if hasattr(request, '_body_cache'):
            if isinstance(request._body_cache, str):
                if request._body_cache.strip():
                    data = json.loads(request._body_cache)
                else:
                    data = {}
            else:
                if request._body_cache:
                    data = json.loads(request._body_cache.decode('utf-8'))
                else:
                    data = {}
        else:
            if request.body:
                data = json.loads(request.body)
            else:
                data = {}
        cancel_at_period_end = data.get('cancel_at_period_end', True)

        if not hasattr(request.user, 'subscription'):
            return JsonResponse({'error': 'No subscription found.'}, status=400)

        subscription = StripeService.cancel_subscription(
            user=request.user,
            cancel_at_period_end=cancel_at_period_end
        )

        message = 'Your subscription has been canceled.' if cancel_at_period_end else 'Your subscription has been canceled immediately.'

        return JsonResponse({
            'success': True,
            'message': message,
            'subscription_status': subscription.status
        })

    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        return JsonResponse({'error': 'An error occurred while canceling your subscription.'}, status=500)


@login_required
@require_http_methods(["POST"])
def reactivate_subscription(request):
    """Reactivate a canceled subscription"""
    try:
        if not hasattr(request.user, 'subscription'):
            return JsonResponse({'error': 'No subscription found.'}, status=400)

        subscription = StripeService.reactivate_subscription(request.user)

        return JsonResponse({
            'success': True,
            'message': 'Your subscription has been reactivated.',
            'subscription_status': subscription.status
        })

    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error reactivating subscription: {e}")
        return JsonResponse({'error': 'An error occurred while reactivating your subscription.'}, status=500)


@login_required
@require_http_methods(["POST"])
def update_payment_method(request):
    """Update user's payment method"""
    try:
        # Use cached body if available (from middleware), otherwise read from request
        if hasattr(request, '_body_cache'):
            if isinstance(request._body_cache, str):
                if request._body_cache.strip():
                    data = json.loads(request._body_cache)
                else:
                    data = {}
            else:
                if request._body_cache:
                    data = json.loads(request._body_cache.decode('utf-8'))
                else:
                    data = {}
        else:
            if request.body:
                data = json.loads(request.body)
            else:
                data = {}
        payment_method_id = data.get('payment_method_id')

        if not payment_method_id:
            return JsonResponse({'error': 'Payment method ID is required.'}, status=400)

        StripeService.update_payment_method(request.user, payment_method_id)

        return JsonResponse({
            'success': True,
            'message': 'Payment method updated successfully.'
        })

    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error updating payment method: {e}")
        return JsonResponse({'error': 'An error occurred while updating your payment method.'}, status=500)


@login_required
def get_payment_methods(request):
    """Get user's payment methods"""
    try:
        if not hasattr(request.user, 'subscription') or not request.user.subscription.stripe_customer_id:
            return JsonResponse({'payment_methods': []})

        payment_methods = StripeService.get_customer_payment_methods(
            request.user.subscription.stripe_customer_id
        )

        # Format payment methods for frontend
        formatted_methods = []
        for method in payment_methods.data:
            formatted_methods.append({
                'id': method.id,
                'type': method.type,
                'card': {
                    'brand': method.card.brand,
                    'last4': method.card.last4,
                    'exp_month': method.card.exp_month,
                    'exp_year': method.card.exp_year,
                } if method.card else None,
                'is_default': method.metadata.get('is_default', False)
            })

        return JsonResponse({'payment_methods': formatted_methods})

    except Exception as e:
        logger.error(f"Error fetching payment methods: {e}")
        return JsonResponse({'error': 'An error occurred while fetching payment methods.'}, status=500)


@login_required
def validate_coupon(request):
    """Validate a coupon code"""
    try:
        coupon_code = request.GET.get('code')
        plan_id = request.GET.get('plan_id')

        if not coupon_code:
            return JsonResponse({'error': 'Coupon code is required.'}, status=400)

        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
        except Coupon.DoesNotExist:
            return JsonResponse({'error': 'Invalid coupon code.'}, status=400)

        # Check if coupon is valid
        if not coupon.is_valid:
            return JsonResponse({'error': 'This coupon has expired or is no longer valid.'}, status=400)

        # Check if user can use this coupon
        if not coupon.can_be_used_by_user(request.user):
            return JsonResponse({'error': 'You have already used this coupon.'}, status=400)

        # Check if coupon applies to the selected plan
        if plan_id:
            try:
                plan = SubscriptionPlan.objects.get(id=plan_id)
                if not coupon.applicable_plans.filter(id=plan.id).exists():
                    return JsonResponse({'error': 'This coupon does not apply to the selected plan.'}, status=400)
            except SubscriptionPlan.DoesNotExist:
                return JsonResponse({'error': 'Invalid plan selected.'}, status=400)

        return JsonResponse({
            'valid': True,
            'coupon': {
                'code': coupon.code,
                'name': coupon.name,
                'description': coupon.description,
                'discount_type': coupon.discount_type,
                'discount_value': str(coupon.discount_value),
                'currency': coupon.currency,
            }
        })

    except Exception as e:
        logger.error(f"Error validating coupon: {e}")
        return JsonResponse({'error': 'An error occurred while validating the coupon.'}, status=500)


@login_required
def subscription_success(request):
    """Subscription success page"""
    return render(request, 'payments/subscription_success.html')


@login_required
def subscription_canceled(request):
    """Subscription canceled page"""
    return render(request, 'payments/subscription_canceled.html')


@login_required
def billing_history(request):
    """User billing history"""
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'payments': payments,
    }

    return render(request, 'payments/billing_history.html', context)


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)

    # Handle the event
    handle_stripe_webhook(event)

    return HttpResponse(status=200)

# Admin views for managing subscriptions


@login_required
def admin_subscription_list(request):
    """Admin view for listing all subscriptions"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('home')

    subscriptions = UserSubscription.objects.select_related('user', 'plan').order_by('-created_at')

    context = {
        'subscriptions': subscriptions,
    }

    return render(request, 'payments/admin/subscription_list.html', context)


@login_required
def admin_subscription_detail(request, subscription_id):
    """Admin view for subscription details"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('home')

    subscription = get_object_or_404(UserSubscription, id=subscription_id)
    payments = Payment.objects.filter(subscription=subscription).order_by('-created_at')

    context = {
        'subscription': subscription,
        'payments': payments,
    }

    return render(request, 'payments/admin/subscription_detail.html', context)


@login_required
@require_http_methods(["POST"])
def admin_cancel_subscription(request, subscription_id):
    """Admin cancel subscription"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Access denied.'}, status=403)

    try:
        subscription = get_object_or_404(UserSubscription, id=subscription_id)
        StripeService.cancel_subscription(subscription.user, cancel_at_period_end=False)

        return JsonResponse({
            'success': True,
            'message': 'Subscription canceled successfully.'
        })

    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        return JsonResponse({'error': 'An error occurred while canceling the subscription.'}, status=500)

# Utility views


def create_default_plans_view(request):
    """Create default subscription plans (admin only)"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('home')

    try:
        plans = create_default_plans()
        messages.success(request, f'Created {len(plans)} default subscription plans.')
    except Exception as e:
        logger.error(f"Error creating default plans: {e}")
        messages.error(request, 'An error occurred while creating default plans.')

    return redirect('payments:admin_subscription_list')


@login_required
def usage_stats(request):
    """Get user's usage statistics"""
    subscription = getattr(request.user, 'subscription', None)

    if not subscription:
        return JsonResponse({
            'charts_remaining': 0,
            'interpretations_remaining': 0,
            'charts_used': 0,
            'interpretations_used': 0,
            'plan_limits': {
                'charts_per_month': 0,
                'ai_interpretations_per_month': 0
            }
        })

    return JsonResponse({
        'charts_remaining': subscription.charts_remaining,
        'interpretations_remaining': subscription.interpretations_remaining,
        'charts_used': subscription.charts_used_this_month,
        'interpretations_used': subscription.interpretations_used_this_month,
        'plan_limits': {
            'charts_per_month': subscription.plan.charts_per_month,
            'ai_interpretations_per_month': subscription.plan.ai_interpretations_per_month
        },
        'can_create_chart': subscription.can_create_chart(),
        'can_get_interpretation': subscription.can_get_interpretation(),
        'subscription_status': subscription.status,
        'plan_name': subscription.plan.name
    })
