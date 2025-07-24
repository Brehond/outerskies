"""
Business Analytics API Views

Provides endpoints for business intelligence and analytics including:
- Revenue metrics and MRR tracking
- Customer lifecycle analytics
- Subscription analytics
- Business performance metrics
"""

import logging
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from chart.services.business_logic import revenue_analytics, customer_lifecycle, subscription_logic
from chart.services.database_optimizer import db_optimizer, health_monitor
from api.utils.error_handler import handle_api_error

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def revenue_metrics(request):
    """
    Get comprehensive revenue metrics and analytics.
    
    Query Parameters:
    - period_days: Number of days to analyze (default: 30)
    - include_mrr: Include MRR calculation (default: true)
    - include_churn: Include churn analysis (default: true)
    
    Returns:
    {
        "revenue_metrics": {...},
        "mrr_data": {...},
        "churn_analysis": {...},
        "customer_lifetime_value": {...}
    }
    """
    try:
        # Get query parameters
        period_days = int(request.GET.get('period_days', 30))
        include_mrr = request.GET.get('include_mrr', 'true').lower() == 'true'
        include_churn = request.GET.get('include_churn', 'true').lower() == 'true'
        
        # Get revenue metrics
        revenue_data = revenue_analytics.get_revenue_metrics(period_days)
        
        response_data = {
            'revenue_metrics': revenue_data,
            'timestamp': revenue_data.get('end_date'),
            'period_days': period_days
        }
        
        # Include MRR data if requested
        if include_mrr:
            mrr_data = revenue_analytics.calculate_mrr()
            response_data['mrr_data'] = mrr_data
        
        # Include churn analysis if requested
        if include_churn:
            churn_data = revenue_analytics.calculate_churn_rate(period_days)
            response_data['churn_analysis'] = churn_data
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting revenue metrics: {e}")
        return handle_api_error(e, 'Failed to get revenue metrics')


@api_view(['GET'])
@permission_classes([IsAdminUser])
def customer_analytics(request):
    """
    Get customer analytics and lifecycle data.
    
    Query Parameters:
    - user_id: Specific user ID to analyze (optional)
    - include_onboarding: Include onboarding data (default: true)
    - include_retention: Include retention risk analysis (default: true)
    
    Returns:
    {
        "customer_data": {...},
        "onboarding_status": {...},
        "retention_risk": {...},
        "recommendations": [...]
    }
    """
    try:
        from chart.models import User
        
        user_id = request.GET.get('user_id')
        include_onboarding = request.GET.get('include_onboarding', 'true').lower() == 'true'
        include_retention = request.GET.get('include_retention', 'true').lower() == 'true'
        
        response_data = {}
        
        if user_id:
            # Analyze specific user
            try:
                user = User.objects.get(id=user_id)
                
                if include_onboarding:
                    onboarding_data = customer_lifecycle.process_user_onboarding(user)
                    response_data['onboarding_status'] = onboarding_data
                
                if include_retention:
                    retention_data = customer_lifecycle.get_retention_risk_score(user)
                    response_data['retention_risk'] = retention_data
                    
                    recommendations = customer_lifecycle.generate_retention_recommendations(user)
                    response_data['recommendations'] = recommendations
                
                # Get customer lifetime value
                clv_data = revenue_analytics.get_customer_lifetime_value(user)
                response_data['customer_lifetime_value'] = clv_data
                
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get aggregate customer data
            total_users = User.objects.count()
            active_subscriptions = User.objects.filter(subscription__status__in=['active', 'trialing']).count()
            
            response_data['customer_summary'] = {
                'total_users': total_users,
                'active_subscriptions': active_subscriptions,
                'subscription_rate': (active_subscriptions / total_users * 100) if total_users > 0 else 0
            }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting customer analytics: {e}")
        return handle_api_error(e, 'Failed to get customer analytics')


@api_view(['GET'])
@permission_classes([IsAdminUser])
def subscription_analytics(request):
    """
    Get subscription analytics and metrics.
    
    Query Parameters:
    - plan_type: Filter by plan type (optional)
    - status: Filter by subscription status (optional)
    - period_days: Analysis period in days (default: 30)
    
    Returns:
    {
        "subscription_metrics": {...},
        "plan_distribution": {...},
        "upgrade_downgrade_rates": {...},
        "revenue_by_plan": {...}
    }
    """
    try:
        from payments.models import UserSubscription, SubscriptionPlan
        
        plan_type = request.GET.get('plan_type')
        status_filter = request.GET.get('status')
        period_days = int(request.GET.get('period_days', 30))
        
        # Base queryset
        subscriptions = UserSubscription.objects.all()
        
        # Apply filters
        if plan_type:
            subscriptions = subscriptions.filter(plan__plan_type=plan_type)
        
        if status_filter:
            subscriptions = subscriptions.filter(status=status_filter)
        
        # Get subscription metrics
        total_subscriptions = subscriptions.count()
        active_subscriptions = subscriptions.filter(status__in=['active', 'trialing']).count()
        
        # Plan distribution
        plan_distribution = {}
        for plan in SubscriptionPlan.objects.all():
            plan_count = subscriptions.filter(plan=plan).count()
            if plan_count > 0:
                plan_distribution[plan.name] = {
                    'count': plan_count,
                    'percentage': (plan_count / total_subscriptions * 100) if total_subscriptions > 0 else 0,
                    'plan_type': plan.plan_type,
                    'price': float(plan.price_monthly) if plan.price_monthly else 0
                }
        
        # Revenue by plan
        revenue_by_plan = {}
        for plan_name, data in plan_distribution.items():
            plan = SubscriptionPlan.objects.get(name=plan_name)
            if plan.price_monthly:
                revenue_by_plan[plan_name] = {
                    'monthly_revenue': data['count'] * float(plan.price_monthly),
                    'plan_price': float(plan.price_monthly),
                    'subscriber_count': data['count']
                }
        
        response_data = {
            'subscription_metrics': {
                'total_subscriptions': total_subscriptions,
                'active_subscriptions': active_subscriptions,
                'active_rate': (active_subscriptions / total_subscriptions * 100) if total_subscriptions > 0 else 0
            },
            'plan_distribution': plan_distribution,
            'revenue_by_plan': revenue_by_plan,
            'analysis_period_days': period_days
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting subscription analytics: {e}")
        return handle_api_error(e, 'Failed to get subscription analytics')


@api_view(['GET'])
@permission_classes([IsAdminUser])
def database_performance(request):
    """
    Get database performance analytics and optimization recommendations.
    
    Returns:
    {
        "query_analytics": {...},
        "connection_pool_stats": {...},
        "slow_queries": [...],
        "optimization_recommendations": [...],
        "health_status": {...}
    }
    """
    try:
        # Get query analytics
        query_analytics = db_optimizer.get_query_analytics(hours=24)
        
        # Get connection pool stats
        connection_stats = db_optimizer.get_connection_pool_stats()
        
        # Get slow queries
        slow_queries = db_optimizer.get_slow_queries(limit=10)
        
        # Get optimization recommendations
        optimization_recommendations = db_optimizer.optimize_connection_pool()
        
        # Get database health status
        health_status = health_monitor.check_database_health()
        
        response_data = {
            'query_analytics': query_analytics,
            'connection_pool_stats': connection_stats,
            'slow_queries': slow_queries,
            'optimization_recommendations': optimization_recommendations,
            'health_status': health_status
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting database performance: {e}")
        return handle_api_error(e, 'Failed to get database performance')


@api_view(['GET'])
@permission_classes([IsAdminUser])
def business_dashboard(request):
    """
    Get comprehensive business dashboard data.
    
    Returns:
    {
        "revenue_summary": {...},
        "customer_summary": {...},
        "subscription_summary": {...},
        "performance_summary": {...},
        "alerts": [...]
    }
    """
    try:
        from chart.models import User
        from payments.models import UserSubscription, Payment
        
        # Revenue summary
        revenue_data = revenue_analytics.get_revenue_metrics(period_days=30)
        mrr_data = revenue_analytics.calculate_mrr()
        
        # Customer summary
        total_users = User.objects.count()
        active_subscriptions = UserSubscription.objects.filter(status__in=['active', 'trialing']).count()
        
        # Subscription summary
        subscription_summary = {
            'total_subscriptions': UserSubscription.objects.count(),
            'active_subscriptions': active_subscriptions,
            'subscription_rate': (active_subscriptions / total_users * 100) if total_users > 0 else 0
        }
        
        # Performance summary
        query_analytics = db_optimizer.get_query_analytics(hours=1)  # Last hour
        health_status = health_monitor.check_database_health()
        
        # Generate alerts
        alerts = []
        
        # Revenue alerts
        if revenue_data['total_revenue'] < 100:  # Less than $100 in 30 days
            alerts.append({
                'type': 'revenue',
                'severity': 'warning',
                'message': 'Low revenue in the last 30 days'
            })
        
        # Churn alerts
        churn_data = revenue_analytics.calculate_churn_rate(period_days=30)
        if churn_data['churn_rate'] > 10:  # More than 10% churn
            alerts.append({
                'type': 'churn',
                'severity': 'critical',
                'message': f'High churn rate: {churn_data["churn_rate"]:.1f}%'
            })
        
        # Performance alerts
        if query_analytics['slow_query_percentage'] > 20:  # More than 20% slow queries
            alerts.append({
                'type': 'performance',
                'severity': 'warning',
                'message': 'High percentage of slow queries detected'
            })
        
        # Health alerts
        if health_status['overall_status'] != 'healthy':
            alerts.append({
                'type': 'health',
                'severity': 'critical',
                'message': f'Database health status: {health_status["overall_status"]}'
            })
        
        response_data = {
            'revenue_summary': {
                'total_revenue_30d': revenue_data['total_revenue'],
                'mrr': mrr_data['total_mrr'],
                'payment_count': revenue_data['payment_count']
            },
            'customer_summary': {
                'total_users': total_users,
                'active_subscriptions': active_subscriptions,
                'subscription_rate': subscription_summary['subscription_rate']
            },
            'subscription_summary': subscription_summary,
            'performance_summary': {
                'query_performance': query_analytics,
                'health_status': health_status['overall_status']
            },
            'alerts': alerts,
            'timestamp': revenue_data.get('end_date')
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting business dashboard: {e}")
        return handle_api_error(e, 'Failed to get business dashboard')


@api_view(['POST'])
@permission_classes([IsAdminUser])
def clear_query_log(request):
    """
    Clear the database query log.
    
    Returns:
    {
        "success": true,
        "message": "Query log cleared successfully"
    }
    """
    try:
        db_optimizer.clear_query_log()
        
        return Response({
            'success': True,
            'message': 'Query log cleared successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error clearing query log: {e}")
        return handle_api_error(e, 'Failed to clear query log')


@api_view(['GET'])
@permission_classes([IsAdminUser])
def index_recommendations(request):
    """
    Get database index optimization recommendations.
    
    Returns:
    {
        "recommendations": [...],
        "estimated_impact": {...}
    }
    """
    try:
        recommendations = db_optimizer.recommend_indexes()
        
        # Calculate estimated impact
        total_queries = sum(rec.get('query_count', 0) for rec in recommendations)
        avg_improvement = 0.5  # Estimated 50% improvement for indexed queries
        
        estimated_impact = {
            'total_queries_affected': total_queries,
            'estimated_performance_improvement': f"{avg_improvement * 100:.1f}%",
            'recommendations_count': len(recommendations)
        }
        
        response_data = {
            'recommendations': recommendations,
            'estimated_impact': estimated_impact
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting index recommendations: {e}")
        return handle_api_error(e, 'Failed to get index recommendations') 