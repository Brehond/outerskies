# stripe_utils.py

import stripe
import logging
from django.conf import settings
from datetime import timezone as dt_timezone, datetime
from django.core.exceptions import ValidationError
from .models import UserSubscription, SubscriptionPlan, Payment, Coupon
from chart.models import User

logger = logging.getLogger(__name__)


class StripeService:
    """
    Service class for handling Stripe operations
    """

    @staticmethod
    def create_customer(user):
        """Create a Stripe customer for a user"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.username,
                metadata={
                    'user_id': user.id,
                    'username': user.username,
                }
            )
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer for user {user.id}: {e}")
            raise ValidationError(f"Failed to create payment account: {str(e)}")

    @staticmethod
    def create_subscription(user, plan, payment_method_id=None, coupon_code=None):
        """Create a Stripe subscription"""
        try:
            # Get or create customer
            if not hasattr(user, 'subscription') or not user.subscription.stripe_customer_id:
                customer = StripeService.create_customer(user)
                customer_id = customer.id
            else:
                customer_id = user.subscription.stripe_customer_id

            # Prepare subscription data
            subscription_data = {
                'customer': customer_id,
                'items': [{'price': plan.stripe_price_id}],
                'payment_behavior': 'default_incomplete',
                'expand': ['latest_invoice.payment_intent'],
                'metadata': {
                    'user_id': user.id,
                    'plan_id': plan.id,
                }
            }

            # Add payment method if provided
            if payment_method_id:
                subscription_data['default_payment_method'] = payment_method_id

            # Add coupon if provided
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                    if coupon.is_valid and coupon.can_be_used_by_user(user):
                        subscription_data['coupon'] = coupon.code
                except Coupon.DoesNotExist:
                    logger.warning(f"Invalid coupon code: {coupon_code}")

            # Create subscription
            subscription = stripe.Subscription.create(**subscription_data)

            # Update or create user subscription
            user_subscription, created = UserSubscription.objects.get_or_create(
                user=user,
                defaults={
                    'plan': plan,
                    'stripe_customer_id': customer_id,
                    'stripe_subscription_id': subscription.id,
                    'status': subscription.status,
                    'current_period_start': datetime.fromtimestamp(
                        subscription.current_period_start, tz=dt_timezone.utc
                    ).replace(tzinfo=None) if not settings.USE_TZ else datetime.fromtimestamp(
                        subscription.current_period_start, tz=dt_timezone.utc
                    ),
                    'current_period_end': datetime.fromtimestamp(
                        subscription.current_period_end, tz=dt_timezone.utc
                    ).replace(tzinfo=None) if not settings.USE_TZ else datetime.fromtimestamp(
                        subscription.current_period_end, tz=dt_timezone.utc
                    ),
                }
            )

            if not created:
                user_subscription.stripe_customer_id = customer_id
                user_subscription.stripe_subscription_id = subscription.id
                user_subscription.status = subscription.status
                user_subscription.current_period_start = datetime.fromtimestamp(
                    subscription.current_period_start, tz=dt_timezone.utc
                ).replace(tzinfo=None) if not settings.USE_TZ else datetime.fromtimestamp(
                    subscription.current_period_start, tz=dt_timezone.utc
                )
                user_subscription.current_period_end = datetime.fromtimestamp(
                    subscription.current_period_end, tz=dt_timezone.utc
                ).replace(tzinfo=None) if not settings.USE_TZ else datetime.fromtimestamp(
                    subscription.current_period_end, tz=dt_timezone.utc
                )
                user_subscription.save()

            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Error creating subscription for user {user.id}: {e}")
            raise ValidationError(f"Failed to create subscription: {str(e)}")

    @staticmethod
    def cancel_subscription(user, cancel_at_period_end=True):
        """Cancel a user's subscription"""
        try:
            if not hasattr(user, 'subscription') or not user.subscription.stripe_subscription_id:
                raise ValidationError("No active subscription found")

            subscription = stripe.Subscription.modify(
                user.subscription.stripe_subscription_id,
                cancel_at_period_end=cancel_at_period_end
            )

            # Update local subscription
            user.subscription.status = subscription.status
            user.subscription.cancel_at_period_end = cancel_at_period_end
            if cancel_at_period_end:
                user.subscription.canceled_at = datetime.now()
            user.subscription.save()

            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Error canceling subscription for user {user.id}: {e}")
            raise ValidationError(f"Failed to cancel subscription: {str(e)}")

    @staticmethod
    def reactivate_subscription(user):
        """Reactivate a canceled subscription"""
        try:
            if not hasattr(user, 'subscription') or not user.subscription.stripe_subscription_id:
                raise ValidationError("No subscription found")

            subscription = stripe.Subscription.modify(
                user.subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )

            # Update local subscription
            user.subscription.status = subscription.status
            user.subscription.cancel_at_period_end = False
            user.subscription.canceled_at = None
            user.subscription.save()

            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Error reactivating subscription for user {user.id}: {e}")
            raise ValidationError(f"Failed to reactivate subscription: {str(e)}")

    @staticmethod
    def update_payment_method(user, payment_method_id):
        """Update the default payment method for a customer"""
        try:
            if not hasattr(user, 'subscription') or not user.subscription.stripe_customer_id:
                raise ValidationError("No customer found")

            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.subscription.stripe_customer_id,
            )

            # Set as default payment method
            stripe.Customer.modify(
                user.subscription.stripe_customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id,
                },
            )

            return True

        except stripe.error.StripeError as e:
            logger.error(f"Error updating payment method for user {user.id}: {e}")
            raise ValidationError(f"Failed to update payment method: {str(e)}")

    @staticmethod
    def create_payment_intent(amount, currency='usd', customer_id=None, metadata=None):
        """Create a payment intent for one-time payments"""
        try:
            intent_data = {
                'amount': int(amount * 100),  # Convert to cents
                'currency': currency,
                'automatic_payment_methods': {
                    'enabled': True,
                },
            }

            if customer_id:
                intent_data['customer'] = customer_id

            if metadata:
                intent_data['metadata'] = metadata

            return stripe.PaymentIntent.create(**intent_data)

        except stripe.error.StripeError as e:
            logger.error(f"Error creating payment intent: {e}")
            raise ValidationError(f"Failed to create payment: {str(e)}")

    @staticmethod
    def get_customer_payment_methods(customer_id):
        """Get all payment methods for a customer"""
        try:
            return stripe.PaymentMethod.list(
                customer=customer_id,
                type='card'
            )
        except stripe.error.StripeError as e:
            logger.error(f"Error fetching payment methods for customer {customer_id}: {e}")
            return []


class WebhookHandler:
    """
    Handle Stripe webhook events
    """

    @staticmethod
    def handle_subscription_updated(event):
        """Handle subscription.updated webhook"""
        try:
            subscription_data = event.data.object
            subscription_id = subscription_data.id

            # Find local subscription
            try:
                user_subscription = UserSubscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
            except UserSubscription.DoesNotExist:
                logger.warning(f"Subscription {subscription_id} not found locally")
                return

            # Update subscription status
            user_subscription.status = subscription_data.status
            user_subscription.current_period_start = datetime.fromtimestamp(
                subscription_data.current_period_start, tz=dt_timezone.utc
            ).replace(tzinfo=None) if not settings.USE_TZ else datetime.fromtimestamp(
                subscription_data.current_period_start, tz=dt_timezone.utc
            )
            user_subscription.current_period_end = datetime.fromtimestamp(
                subscription_data.current_period_end, tz=dt_timezone.utc
            ).replace(tzinfo=None) if not settings.USE_TZ else datetime.fromtimestamp(
                subscription_data.current_period_end, tz=dt_timezone.utc
            )
            user_subscription.cancel_at_period_end = subscription_data.cancel_at_period_end

            if subscription_data.canceled_at:
                user_subscription.canceled_at = datetime.fromtimestamp(
                    subscription_data.canceled_at, tz=dt_timezone.utc
                ).replace(tzinfo=None) if not settings.USE_TZ else datetime.fromtimestamp(
                    subscription_data.canceled_at, tz=dt_timezone.utc
                )

            user_subscription.save()

            logger.info(f"Updated subscription {subscription_id} status to {subscription_data.status}")

        except Exception as e:
            logger.error(f"Error handling subscription.updated webhook: {e}")

    @staticmethod
    def handle_invoice_payment_succeeded(event):
        """Handle invoice.payment_succeeded webhook"""
        try:
            invoice_data = event.data.object
            subscription_id = invoice_data.subscription

            if not subscription_id:
                return

            # Find local subscription
            try:
                user_subscription = UserSubscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
            except UserSubscription.DoesNotExist:
                logger.warning(f"Subscription {subscription_id} not found locally")
                return

            # Create payment record
            Payment.objects.create(
                user=user_subscription.user,
                subscription=user_subscription,
                amount=invoice_data.amount_paid / 100,  # Convert from cents
                currency=invoice_data.currency,
                status='succeeded',
                stripe_invoice_id=invoice_data.id,
                billing_email=invoice_data.customer_email,
                billing_name=invoice_data.customer_name,
                description=f"Subscription payment for {user_subscription.plan.name}",
                paid_at=datetime.now(),
            )

            # Reset monthly usage on successful payment
            user_subscription.reset_monthly_usage()

            logger.info(f"Payment succeeded for subscription {subscription_id}")

        except Exception as e:
            logger.error(f"Error handling invoice.payment_succeeded webhook: {e}")

    @staticmethod
    def handle_invoice_payment_failed(event):
        """Handle invoice.payment_failed webhook"""
        try:
            invoice_data = event.data.object
            subscription_id = invoice_data.subscription

            if not subscription_id:
                return

            # Find local subscription
            try:
                user_subscription = UserSubscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
            except UserSubscription.DoesNotExist:
                logger.warning(f"Subscription {subscription_id} not found locally")
                return

            # Update subscription status
            user_subscription.status = 'past_due'
            user_subscription.save()

            # Create failed payment record
            Payment.objects.create(
                user=user_subscription.user,
                subscription=user_subscription,
                amount=invoice_data.amount_due / 100,  # Convert from cents
                currency=invoice_data.currency,
                status='failed',
                stripe_invoice_id=invoice_data.id,
                billing_email=invoice_data.customer_email,
                billing_name=invoice_data.customer_name,
                description=f"Failed payment for {user_subscription.plan.name}",
            )

            logger.warning(f"Payment failed for subscription {subscription_id}")

        except Exception as e:
            logger.error(f"Error handling invoice.payment_failed webhook: {e}")

    @staticmethod
    def handle_customer_subscription_deleted(event):
        """Handle customer.subscription.deleted webhook"""
        try:
            subscription_data = event.data.object
            subscription_id = subscription_data.id

            # Find local subscription
            try:
                user_subscription = UserSubscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
            except UserSubscription.DoesNotExist:
                logger.warning(f"Subscription {subscription_id} not found locally")
                return

            # Update subscription status
            user_subscription.status = 'canceled'
            user_subscription.canceled_at = datetime.now()
            user_subscription.save()

            logger.info(f"Subscription {subscription_id} deleted")

        except Exception as e:
            logger.error(f"Error handling customer.subscription.deleted webhook: {e}")


def handle_stripe_webhook(event):
    """Main webhook handler"""
    event_type = event.type

    if event_type == 'subscription.updated':
        WebhookHandler.handle_subscription_updated(event)
    elif event_type == 'invoice.payment_succeeded':
        WebhookHandler.handle_invoice_payment_succeeded(event)
    elif event_type == 'invoice.payment_failed':
        WebhookHandler.handle_invoice_payment_failed(event)
    elif event_type == 'customer.subscription.deleted':
        WebhookHandler.handle_customer_subscription_deleted(event)
    else:
        logger.info(f"Unhandled webhook event: {event_type}")


def create_default_plans():
    """Create default subscription plans"""
    plans_data = [
        {
            'name': 'Free',
            'plan_type': 'free',
            'price_monthly': 0,
            'price_yearly': 0,
            'charts_per_month': 3,
            'ai_interpretations_per_month': 3,
            'description': 'Perfect for getting started with astrology',
            'features': [
                '3 charts per month',
                'Basic AI interpretations',
                'Standard support',
                'Basic chart features'
            ]
        },
        {
            'name': 'Stellar',
            'plan_type': 'stellar',
            'price_monthly': 9.99,
            'price_yearly': 99.99,
            'charts_per_month': 20,
            'ai_interpretations_per_month': 20,
            'advanced_ai_models': True,
            'description': 'For astrology enthusiasts who want more insights',
            'features': [
                '20 charts per month',
                'Advanced AI interpretations',
                'Priority support',
                'Advanced chart features',
                'Chart history'
            ],
            'is_popular': True
        },
        {
            'name': 'Cosmic',
            'plan_type': 'cosmic',
            'price_monthly': 19.99,
            'price_yearly': 199.99,
            'charts_per_month': -1,  # Unlimited
            'ai_interpretations_per_month': -1,  # Unlimited
            'priority_support': True,
            'advanced_ai_models': True,
            'chart_history_unlimited': True,
            'export_features': True,
            'description': 'For serious astrologers and professionals',
            'features': [
                'Unlimited charts',
                'Unlimited AI interpretations',
                'Premium AI models',
                'Priority support',
                'Unlimited chart history',
                'Export features',
                'Advanced analytics'
            ]
        }
    ]

    for plan_data in plans_data:
        plan, created = SubscriptionPlan.objects.get_or_create(
            name=plan_data['name'],
            defaults=plan_data
        )
        if created:
            logger.info(f"Created subscription plan: {plan.name}")

    return SubscriptionPlan.objects.all()
