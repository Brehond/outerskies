# models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid
import stripe
from django.conf import settings

User = get_user_model()

class SubscriptionPlan(models.Model):
    """
    Defines available subscription plans and their features
    """
    PLAN_TYPES = [
        ('free', 'Free'),
        ('stellar', 'Stellar'),
        ('cosmic', 'Cosmic'),
    ]
    
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default='monthly')
    
    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stripe_price_id_monthly = models.CharField(max_length=100, null=True, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, null=True, blank=True)
    
    # Feature limits
    charts_per_month = models.IntegerField(default=3)
    ai_interpretations_per_month = models.IntegerField(default=3)
    priority_support = models.BooleanField(default=False)
    advanced_ai_models = models.BooleanField(default=False)
    chart_history_unlimited = models.BooleanField(default=False)
    export_features = models.BooleanField(default=False)
    
    # Plan details
    description = models.TextField()
    features = models.JSONField(default=list, help_text="List of features included in this plan")
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False, help_text="Mark as featured plan")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_plan'
        ordering = ['price_monthly']
    
    def __str__(self):
        return f"{self.name} ({self.billing_cycle})"
    
    @property
    def current_price(self):
        """Get the current price based on billing cycle"""
        if self.billing_cycle == 'yearly':
            return self.price_yearly
        return self.price_monthly
    
    @property
    def stripe_price_id(self):
        """Get the current Stripe price ID based on billing cycle"""
        if self.billing_cycle == 'yearly':
            return self.stripe_price_id_yearly
        return self.stripe_price_id_monthly
    
    def get_yearly_discount(self):
        """Calculate yearly discount percentage"""
        if self.price_monthly and self.price_yearly:
            yearly_cost = self.price_monthly * 12
            discount = ((yearly_cost - self.price_yearly) / yearly_cost) * 100
            return round(discount, 0)
        return 0

class UserSubscription(models.Model):
    """
    Tracks user subscriptions and their status
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    
    # Stripe integration
    stripe_customer_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    # Subscription details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='incomplete')
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    charts_used_this_month = models.IntegerField(default=0)
    interpretations_used_this_month = models.IntegerField(default=0)
    last_usage_reset = models.DateTimeField(auto_now_add=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_subscription'
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
    
    @property
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status in ['active', 'trialing']
    
    @property
    def charts_remaining(self):
        """Calculate remaining charts for current month"""
        return max(0, self.plan.charts_per_month - self.charts_used_this_month)
    
    @property
    def interpretations_remaining(self):
        """Calculate remaining interpretations for current month"""
        return max(0, self.plan.ai_interpretations_per_month - self.interpretations_used_this_month)
    
    def can_create_chart(self):
        """Check if user can create a new chart"""
        if self.plan.charts_per_month == -1:  # Unlimited
            return True
        return self.charts_remaining > 0
    
    def can_get_interpretation(self):
        """Check if user can get an AI interpretation"""
        if self.plan.ai_interpretations_per_month == -1:  # Unlimited
            return True
        return self.interpretations_remaining > 0
    
    def increment_chart_usage(self):
        """Increment chart usage counter"""
        if self.plan.charts_per_month != -1:  # Not unlimited
            self.charts_used_this_month += 1
            self.save(update_fields=['charts_used_this_month'])
    
    def increment_interpretation_usage(self):
        """Increment interpretation usage counter"""
        if self.plan.ai_interpretations_per_month != -1:  # Not unlimited
            self.interpretations_used_this_month += 1
            self.save(update_fields=['interpretations_used_this_month'])
    
    def reset_monthly_usage(self):
        """Reset monthly usage counters"""
        self.charts_used_this_month = 0
        self.interpretations_used_this_month = 0
        self.last_usage_reset = timezone.now()
        self.save(update_fields=['charts_used_this_month', 'interpretations_used_this_month', 'last_usage_reset'])

class Payment(models.Model):
    """
    Tracks individual payments and transactions
    """
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='card')
    
    # Stripe integration
    stripe_payment_intent_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    stripe_invoice_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Billing details
    billing_email = models.EmailField()
    billing_name = models.CharField(max_length=255)
    billing_address = models.JSONField(default=dict, blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payment'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - ${self.amount} - {self.status}"

class Coupon(models.Model):
    """
    Discount coupons for subscriptions
    """
    COUPON_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Discount details
    discount_type = models.CharField(max_length=20, choices=COUPON_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Usage limits
    max_uses = models.IntegerField(null=True, blank=True, help_text="Maximum number of times this coupon can be used")
    current_uses = models.IntegerField(default=0)
    
    # Validity
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Applicable plans
    applicable_plans = models.ManyToManyField(SubscriptionPlan, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'coupon'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_valid(self):
        """Check if coupon is currently valid"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True
    
    def can_be_used_by_user(self, user):
        """Check if user can use this coupon"""
        # Check if user has already used this coupon
        return not CouponUsage.objects.filter(coupon=self, user=user).exists()
    
    def calculate_discount(self, amount):
        """Calculate discount amount"""
        if self.discount_type == 'percentage':
            return (amount * self.discount_value) / 100
        return min(self.discount_value, amount)

class CouponUsage(models.Model):
    """
    Tracks coupon usage by users
    """
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_usages')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='coupon_usages')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'coupon_usage'
        unique_together = ['coupon', 'user']
    
    def __str__(self):
        return f"{self.user.username} used {self.coupon.code}"
