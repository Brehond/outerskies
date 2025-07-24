"""
Business Logic Layer

This module provides centralized business logic for:
- Subscription management and lifecycle
- Usage tracking and enforcement
- Revenue analytics and metrics
- Customer lifecycle management
- Business rule enforcement
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.contrib.auth import get_user_model

from chart.models import User, Chart, TaskStatus
from payments.models import UserSubscription, SubscriptionPlan, Payment, Coupon
from payments.stripe_utils import StripeService

User = get_user_model()
logger = logging.getLogger(__name__)


class SubscriptionBusinessLogic:
    """
    Handles all subscription-related business logic including:
    - Subscription creation, upgrades, downgrades
    - Usage tracking and enforcement
    - Billing cycle management
    - Proration calculations
    """
    
    def __init__(self):
        self.stripe_service = StripeService()
    
    def create_subscription(self, user: User, plan: SubscriptionPlan, 
                          payment_method_id: str = None, 
                          coupon_code: str = None) -> UserSubscription:
        """
        Create a new subscription with proper business logic.
        
        Args:
            user: User to create subscription for
            plan: Subscription plan
            payment_method_id: Stripe payment method ID
            coupon_code: Optional coupon code
            
        Returns:
            UserSubscription instance
            
        Raises:
            ValidationError: If subscription creation fails
        """
        try:
            with transaction.atomic():
                # Check if user already has an active subscription
                if hasattr(user, 'subscription') and user.subscription.is_active:
                    raise ValidationError("User already has an active subscription")
                
                # Validate coupon if provided
                coupon = None
                if coupon_code:
                    coupon = self._validate_coupon(coupon_code, user, plan)
                
                # Create Stripe subscription
                stripe_subscription = self.stripe_service.create_subscription(
                    user=user,
                    plan=plan,
                    payment_method_id=payment_method_id,
                    coupon_code=coupon_code
                )
                
                # Create local subscription record
                subscription = UserSubscription.objects.create(
                    user=user,
                    plan=plan,
                    stripe_customer_id=stripe_subscription.customer,
                    stripe_subscription_id=stripe_subscription.id,
                    status=stripe_subscription.status,
                    current_period_start=timezone.now(),
                    current_period_end=timezone.now() + timedelta(days=30),
                    charts_used_this_month=0,
                    interpretations_used_this_month=0,
                    last_usage_reset=timezone.now()
                )
                
                logger.info(f"Created subscription for user {user.id}: {plan.name}")
                return subscription
                
        except Exception as e:
            logger.error(f"Failed to create subscription for user {user.id}: {e}")
            raise ValidationError(f"Failed to create subscription: {str(e)}")
    
    def upgrade_subscription(self, user: User, new_plan: SubscriptionPlan) -> UserSubscription:
        """
        Upgrade user's subscription with proration handling.
        
        Args:
            user: User to upgrade
            new_plan: New subscription plan
            
        Returns:
            Updated UserSubscription instance
        """
        try:
            with transaction.atomic():
                if not hasattr(user, 'subscription') or not user.subscription.is_active:
                    raise ValidationError("No active subscription to upgrade")
                
                current_subscription = user.subscription
                current_plan = current_subscription.plan
                
                # Calculate proration
                proration_amount = self._calculate_proration_amount(
                    current_subscription, new_plan
                )
                
                # Update Stripe subscription
                stripe_subscription = self.stripe_service.update_subscription(
                    user=user,
                    new_plan=new_plan
                )
                
                # Update local subscription
                current_subscription.plan = new_plan
                current_subscription.status = stripe_subscription.status
                current_subscription.save()
                
                # Create proration payment record if needed
                if proration_amount > 0:
                    Payment.objects.create(
                        user=user,
                        subscription=current_subscription,
                        amount=proration_amount,
                        currency='USD',
                        status='succeeded',
                        description=f"Proration for upgrade from {current_plan.name} to {new_plan.name}",
                        paid_at=timezone.now()
                    )
                
                logger.info(f"Upgraded subscription for user {user.id}: {current_plan.name} -> {new_plan.name}")
                return current_subscription
                
        except Exception as e:
            logger.error(f"Failed to upgrade subscription for user {user.id}: {e}")
            raise ValidationError(f"Failed to upgrade subscription: {str(e)}")
    
    def downgrade_subscription(self, user: User, new_plan: SubscriptionPlan) -> UserSubscription:
        """
        Downgrade user's subscription with proper handling.
        
        Args:
            user: User to downgrade
            new_plan: New subscription plan
            
        Returns:
            Updated UserSubscription instance
        """
        try:
            with transaction.atomic():
                if not hasattr(user, 'subscription') or not user.subscription.is_active:
                    raise ValidationError("No active subscription to downgrade")
                
                current_subscription = user.subscription
                current_plan = current_subscription.plan
                
                # Check if user has exceeded new plan limits
                if not self._can_downgrade_to_plan(user, new_plan):
                    raise ValidationError(f"Cannot downgrade to {new_plan.name}: usage exceeds plan limits")
                
                # Update Stripe subscription
                stripe_subscription = self.stripe_service.update_subscription(
                    user=user,
                    new_plan=new_plan
                )
                
                # Update local subscription
                current_subscription.plan = new_plan
                current_subscription.status = stripe_subscription.status
                current_subscription.save()
                
                logger.info(f"Downgraded subscription for user {user.id}: {current_plan.name} -> {new_plan.name}")
                return current_subscription
                
        except Exception as e:
            logger.error(f"Failed to downgrade subscription for user {user.id}: {e}")
            raise ValidationError(f"Failed to downgrade subscription: {str(e)}")
    
    def cancel_subscription(self, user: User, cancel_at_period_end: bool = True) -> UserSubscription:
        """
        Cancel user's subscription.
        
        Args:
            user: User to cancel subscription for
            cancel_at_period_end: Whether to cancel at period end or immediately
            
        Returns:
            Updated UserSubscription instance
        """
        try:
            if not hasattr(user, 'subscription') or not user.subscription.is_active:
                raise ValidationError("No active subscription to cancel")
            
            subscription = user.subscription
            
            # Cancel Stripe subscription
            self.stripe_service.cancel_subscription(user, cancel_at_period_end)
            
            # Update local subscription
            subscription.status = 'canceled' if not cancel_at_period_end else subscription.status
            subscription.cancel_at_period_end = cancel_at_period_end
            subscription.canceled_at = timezone.now() if not cancel_at_period_end else None
            subscription.save()
            
            logger.info(f"Canceled subscription for user {user.id}")
            return subscription
            
        except Exception as e:
            logger.error(f"Failed to cancel subscription for user {user.id}: {e}")
            raise ValidationError(f"Failed to cancel subscription: {str(e)}")
    
    def check_user_limits(self, user: User, action: str) -> bool:
        """
        Check if user can perform an action based on their subscription limits.
        
        Args:
            user: User to check
            action: Action type ('chart_generation' or 'ai_interpretation')
            
        Returns:
            True if user can perform action, False otherwise
        """
        if not hasattr(user, 'subscription') or not user.subscription.is_active:
            return False
        
        subscription = user.subscription
        plan = subscription.plan
        
        if action == 'chart_generation':
            return plan.charts_per_month == -1 or subscription.charts_remaining > 0
        elif action == 'ai_interpretation':
            return plan.ai_interpretations_per_month == -1 or subscription.interpretations_remaining > 0
        else:
            return False
    
    def track_usage(self, user: User, action: str) -> bool:
        """
        Track usage for a user action.
        
        Args:
            user: User to track usage for
            action: Action type ('chart_generation' or 'ai_interpretation')
            
        Returns:
            True if usage was tracked successfully, False otherwise
        """
        try:
            if not hasattr(user, 'subscription') or not user.subscription.is_active:
                return False
            
            subscription = user.subscription
            
            if action == 'chart_generation':
                subscription.increment_chart_usage()
            elif action == 'ai_interpretation':
                subscription.increment_interpretation_usage()
            else:
                return False
            
            logger.info(f"Tracked {action} usage for user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to track usage for user {user.id}: {e}")
            return False
    
    def reset_monthly_usage(self, user: User) -> bool:
        """
        Reset monthly usage counters for a user.
        
        Args:
            user: User to reset usage for
            
        Returns:
            True if reset successful, False otherwise
        """
        try:
            if hasattr(user, 'subscription'):
                user.subscription.reset_monthly_usage()
                logger.info(f"Reset monthly usage for user {user.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to reset usage for user {user.id}: {e}")
            return False
    
    def _validate_coupon(self, coupon_code: str, user: User, plan: SubscriptionPlan) -> Coupon:
        """Validate coupon for user and plan."""
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            
            # Check if coupon is valid
            if not coupon.is_valid:
                raise ValidationError("Coupon has expired or is invalid")
            
            # Check if user can use this coupon
            if not coupon.can_be_used_by_user(user):
                raise ValidationError("Coupon cannot be used by this user")
            
            # Check if coupon applies to this plan
            if coupon.applicable_plans.exists() and plan not in coupon.applicable_plans.all():
                raise ValidationError("Coupon does not apply to this plan")
            
            return coupon
            
        except Coupon.DoesNotExist:
            raise ValidationError("Invalid coupon code")
    
    def _calculate_proration_amount(self, subscription: UserSubscription, new_plan: SubscriptionPlan) -> Decimal:
        """Calculate proration amount for subscription change."""
        # This is a simplified calculation - in production, you'd use Stripe's proration API
        current_plan = subscription.plan
        days_remaining = (subscription.current_period_end - timezone.now()).days
        
        if days_remaining <= 0:
            return Decimal('0.00')
        
        # Calculate daily rates
        current_daily_rate = current_plan.price_monthly / 30
        new_daily_rate = new_plan.price_monthly / 30
        
        # Calculate proration
        if new_daily_rate > current_daily_rate:
            # Upgrade - charge difference
            proration_amount = (new_daily_rate - current_daily_rate) * days_remaining
        else:
            # Downgrade - credit difference
            proration_amount = (current_daily_rate - new_daily_rate) * days_remaining
        
        return max(Decimal('0.00'), proration_amount)
    
    def _can_downgrade_to_plan(self, user: User, new_plan: SubscriptionPlan) -> bool:
        """Check if user can downgrade to a specific plan."""
        if not hasattr(user, 'subscription'):
            return True
        
        subscription = user.subscription
        
        # Check chart usage
        if new_plan.charts_per_month != -1 and subscription.charts_used_this_month > new_plan.charts_per_month:
            return False
        
        # Check interpretation usage
        if new_plan.ai_interpretations_per_month != -1 and subscription.interpretations_used_this_month > new_plan.ai_interpretations_per_month:
            return False
        
        return True


class RevenueAnalytics:
    """
    Handles revenue analytics and business metrics including:
    - Monthly Recurring Revenue (MRR)
    - Churn analysis
    - Revenue forecasting
    - Customer lifetime value
    """
    
    def calculate_mrr(self, date: datetime = None) -> Dict[str, Any]:
        """
        Calculate Monthly Recurring Revenue.
        
        Args:
            date: Date to calculate MRR for (defaults to current date)
            
        Returns:
            Dictionary with MRR metrics
        """
        if date is None:
            date = timezone.now()
        
        # Get active subscriptions
        active_subscriptions = UserSubscription.objects.filter(
            status__in=['active', 'trialing'],
            current_period_end__gte=date
        )
        
        # Calculate MRR by plan
        mrr_by_plan = {}
        total_mrr = Decimal('0.00')
        
        for subscription in active_subscriptions:
            plan = subscription.plan
            plan_mrr = plan.price_monthly or Decimal('0.00')
            
            if plan.name not in mrr_by_plan:
                mrr_by_plan[plan.name] = {
                    'count': 0,
                    'mrr': Decimal('0.00'),
                    'plan_type': plan.plan_type
                }
            
            mrr_by_plan[plan.name]['count'] += 1
            mrr_by_plan[plan.name]['mrr'] += plan_mrr
            total_mrr += plan_mrr
        
        return {
            'total_mrr': total_mrr,
            'mrr_by_plan': mrr_by_plan,
            'active_subscriptions': active_subscriptions.count(),
            'calculation_date': date.isoformat()
        }
    
    def calculate_churn_rate(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Calculate churn rate for a given period.
        
        Args:
            period_days: Number of days to analyze
            
        Returns:
            Dictionary with churn metrics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Get subscriptions that were active at start of period
        active_at_start = UserSubscription.objects.filter(
            status__in=['active', 'trialing'],
            current_period_start__lte=start_date,
            current_period_end__gte=start_date
        ).count()
        
        # Get subscriptions that churned during period
        churned_subscriptions = UserSubscription.objects.filter(
            status='canceled',
            canceled_at__gte=start_date,
            canceled_at__lte=end_date
        ).count()
        
        # Calculate churn rate
        churn_rate = (churned_subscriptions / active_at_start * 100) if active_at_start > 0 else 0
        
        return {
            'period_days': period_days,
            'active_at_start': active_at_start,
            'churned_subscriptions': churned_subscriptions,
            'churn_rate': round(churn_rate, 2),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    
    def get_revenue_metrics(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive revenue metrics.
        
        Args:
            period_days: Number of days to analyze
            
        Returns:
            Dictionary with revenue metrics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Get payments in period
        payments = Payment.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            status='succeeded'
        )
        
        total_revenue = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        payment_count = payments.count()
        
        # Get new subscriptions in period
        new_subscriptions = UserSubscription.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Get active subscriptions
        active_subscriptions = UserSubscription.objects.filter(
            status__in=['active', 'trialing']
        ).count()
        
        return {
            'period_days': period_days,
            'total_revenue': total_revenue,
            'payment_count': payment_count,
            'average_payment': total_revenue / payment_count if payment_count > 0 else Decimal('0.00'),
            'new_subscriptions': new_subscriptions,
            'active_subscriptions': active_subscriptions,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    
    def get_customer_lifetime_value(self, user: User) -> Dict[str, Any]:
        """
        Calculate customer lifetime value for a user.
        
        Args:
            user: User to calculate CLV for
            
        Returns:
            Dictionary with CLV metrics
        """
        # Get all payments for user
        payments = Payment.objects.filter(
            user=user,
            status='succeeded'
        )
        
        total_spent = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        payment_count = payments.count()
        
        # Get subscription history
        subscription = getattr(user, 'subscription', None)
        subscription_age = 0
        if subscription:
            subscription_age = (timezone.now() - subscription.created_at).days
        
        # Calculate average monthly spend
        avg_monthly_spend = total_spent / (subscription_age / 30) if subscription_age > 0 else Decimal('0.00')
        
        return {
            'user_id': user.id,
            'total_spent': total_spent,
            'payment_count': payment_count,
            'subscription_age_days': subscription_age,
            'average_monthly_spend': avg_monthly_spend,
            'customer_since': subscription.created_at.isoformat() if subscription else None
        }


class CustomerLifecycleManager:
    """
    Manages customer lifecycle including:
    - Onboarding process
    - Retention strategies
    - Customer support integration
    - Engagement tracking
    """
    
    def __init__(self):
        self.subscription_logic = SubscriptionBusinessLogic()
    
    def process_user_onboarding(self, user: User) -> Dict[str, Any]:
        """
        Process user onboarding and return onboarding status.
        
        Args:
            user: User to process onboarding for
            
        Returns:
            Dictionary with onboarding status and next steps
        """
        onboarding_status = {
            'completed_steps': [],
            'pending_steps': [],
            'onboarding_complete': False
        }
        
        # Check if user has completed profile
        if user.has_birth_data:
            onboarding_status['completed_steps'].append('profile_complete')
        else:
            onboarding_status['pending_steps'].append('complete_profile')
        
        # Check if user has created first chart
        if Chart.objects.filter(user=user).exists():
            onboarding_status['completed_steps'].append('first_chart')
        else:
            onboarding_status['pending_steps'].append('create_first_chart')
        
        # Check if user has subscription
        if hasattr(user, 'subscription') and user.subscription.is_active:
            onboarding_status['completed_steps'].append('subscription_active')
        else:
            onboarding_status['pending_steps'].append('choose_plan')
        
        # Determine if onboarding is complete
        onboarding_status['onboarding_complete'] = len(onboarding_status['pending_steps']) == 0
        
        return onboarding_status
    
    def get_retention_risk_score(self, user: User) -> Dict[str, Any]:
        """
        Calculate retention risk score for a user.
        
        Args:
            user: User to analyze
            
        Returns:
            Dictionary with retention risk metrics
        """
        risk_factors = []
        risk_score = 0
        
        # Check subscription status
        if not hasattr(user, 'subscription') or not user.subscription.is_active:
            risk_factors.append('no_active_subscription')
            risk_score += 30
        
        # Check usage patterns
        if hasattr(user, 'subscription'):
            subscription = user.subscription
            plan = subscription.plan
            
            # Low usage relative to plan limits
            if plan.charts_per_month != -1:
                usage_percentage = (subscription.charts_used_this_month / plan.charts_per_month) * 100
                if usage_percentage < 20:
                    risk_factors.append('low_chart_usage')
                    risk_score += 15
            
            if plan.ai_interpretations_per_month != -1:
                usage_percentage = (subscription.interpretations_used_this_month / plan.ai_interpretations_per_month) * 100
                if usage_percentage < 20:
                    risk_factors.append('low_interpretation_usage')
                    risk_score += 15
        
        # Check last activity
        last_chart = Chart.objects.filter(user=user).order_by('-created_at').first()
        if last_chart:
            days_since_last_activity = (timezone.now() - last_chart.created_at).days
            if days_since_last_activity > 30:
                risk_factors.append('inactive_user')
                risk_score += 25
            elif days_since_last_activity > 7:
                risk_factors.append('recently_inactive')
                risk_score += 10
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = 'high'
        elif risk_score >= 25:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'user_id': user.id,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'last_activity': last_chart.created_at.isoformat() if last_chart else None,
            'days_since_last_activity': days_since_last_activity if last_chart else None
        }
    
    def generate_retention_recommendations(self, user: User) -> List[str]:
        """
        Generate retention recommendations for a user.
        
        Args:
            user: User to generate recommendations for
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        risk_analysis = self.get_retention_risk_score(user)
        
        if 'no_active_subscription' in risk_analysis['risk_factors']:
            recommendations.append("Consider upgrading to a paid plan for unlimited access")
        
        if 'low_chart_usage' in risk_analysis['risk_factors']:
            recommendations.append("Try creating more charts to get the most from your subscription")
        
        if 'low_interpretation_usage' in risk_analysis['risk_factors']:
            recommendations.append("Explore AI interpretations to gain deeper insights from your charts")
        
        if 'inactive_user' in risk_analysis['risk_factors']:
            recommendations.append("Welcome back! Create a new chart to rediscover your astrological insights")
        
        if 'recently_inactive' in risk_analysis['risk_factors']:
            recommendations.append("Don't miss out on your monthly chart allowance - create a new chart today")
        
        return recommendations


# Global instances for easy access
subscription_logic = SubscriptionBusinessLogic()
revenue_analytics = RevenueAnalytics()
customer_lifecycle = CustomerLifecycleManager() 