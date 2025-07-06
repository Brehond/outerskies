# urls.py

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Public pricing page
    path('pricing/', views.pricing_view, name='pricing'),
    
    # Subscription management
    path('subscription/', views.subscription_management, name='subscription_management'),
    path('subscription/create/', views.create_subscription, name='create_subscription'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/reactivate/', views.reactivate_subscription, name='reactivate_subscription'),
    path('subscription/payment-method/update/', views.update_payment_method, name='update_payment_method'),
    path('subscription/payment-methods/', views.get_payment_methods, name='get_payment_methods'),
    
    # Success/cancel pages
    path('subscription/success/', views.subscription_success, name='subscription_success'),
    path('subscription/canceled/', views.subscription_canceled, name='subscription_canceled'),
    
    # Billing
    path('billing/history/', views.billing_history, name='billing_history'),
    
    # Coupons
    path('coupon/validate/', views.validate_coupon, name='validate_coupon'),
    
    # Usage stats
    path('usage/stats/', views.usage_stats, name='usage_stats'),
    
    # Stripe webhook
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    
    # Admin views
    path('admin/subscriptions/', views.admin_subscription_list, name='admin_subscription_list'),
    path('admin/subscriptions/<int:subscription_id>/', views.admin_subscription_detail, name='admin_subscription_detail'),
    path('admin/subscriptions/<int:subscription_id>/cancel/', views.admin_cancel_subscription, name='admin_cancel_subscription'),
    path('admin/plans/create-default/', views.create_default_plans_view, name='create_default_plans'),
]
