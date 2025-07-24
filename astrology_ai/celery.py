import os
import platform
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')

app = Celery('astrology_ai')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Enhanced task routing for Phase 2 priority queues
app.conf.task_routes = {
    # High priority tasks
    'chart.tasks.generate_chart_task': {'queue': 'high'},
    'chart.tasks.generate_interpretation_task': {'queue': 'high'},
    'payments.tasks.*': {'queue': 'critical'},
    
    # Normal priority tasks
    'chart.tasks.calculate_ephemeris_task': {'queue': 'normal'},
    'chart.tasks.cleanup_old_tasks': {'queue': 'normal'},
    'chart.tasks.health_check': {'queue': 'normal'},
    'api.tasks.*': {'queue': 'normal'},
    
    # Low priority tasks
    'system.tasks.*': {'queue': 'low'},
    'maintenance.tasks.*': {'queue': 'low'},
    
    # Bulk processing tasks
    'chart.tasks.bulk_chart_generation': {'queue': 'bulk'},
    'chart.tasks.bulk_interpretation': {'queue': 'bulk'},
}

# Configure task serialization
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']

# Configure timezone
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

# Configure task timeouts
app.conf.task_soft_time_limit = 300  # 5 minutes
app.conf.task_time_limit = 600  # 10 minutes

# Production-ready Celery configuration
# Platform-specific optimizations
import platform
is_windows = platform.system().lower() == 'windows'

# Worker configuration - Platform optimized
if is_windows:
    # Windows-specific configuration
    app.conf.worker_pool = 'solo'  # Use solo pool for Windows
    app.conf.worker_concurrency = 1  # Single worker for Windows
    app.conf.worker_prefetch_multiplier = 1
    app.conf.worker_max_tasks_per_child = 1000
    app.conf.worker_disable_rate_limits = True  # Disable rate limits on Windows
else:
    # Unix/Linux production configuration
    app.conf.worker_pool = 'prefork'  # Use prefork for CPU-bound tasks
    app.conf.worker_concurrency = 4   # Scale based on CPU cores
    app.conf.worker_prefetch_multiplier = 1
    app.conf.worker_max_tasks_per_child = 1000
    app.conf.worker_disable_rate_limits = False

# Broker settings
app.conf.broker_transport_options = {
    'visibility_timeout': 3600,
    'fanout_prefix': True,
    'fanout_patterns': True,
    'socket_connect_timeout': 5,
    'socket_timeout': 5,
    'retry_on_timeout': True,
    'max_connections': 20,
    'connection_pool': {
        'max_connections': 20,
        'retry_on_timeout': True,
    }
}

# Result backend settings
app.conf.result_backend_transport_options = {
    'visibility_timeout': 3600,
    'socket_connect_timeout': 5,
    'socket_timeout': 5,
    'retry_on_timeout': True,
}

# Configure result backend and broker (moved to avoid settings access issues)


def configure_celery():
    app.conf.result_backend = settings.CELERY_RESULT_BACKEND
    app.conf.broker_url = settings.CELERY_BROKER_URL


# Call configuration function
configure_celery()

# Enhanced periodic tasks for Phase 2
app.conf.beat_schedule = {
    # Maintenance tasks
    'cleanup-old-tasks': {
        'task': 'chart.tasks.cleanup_old_tasks',
        'schedule': 3600.0,  # Every hour
    },
    'health-check': {
        'task': 'chart.tasks.health_check',
        'schedule': 300.0,  # Every 5 minutes
    },
    
    # Cache warming
    'cache-warming': {
        'task': 'chart.tasks.warm_cache',
        'schedule': 900.0,  # Every 15 minutes
    },
    
    # Database optimization
    'database-optimization': {
        'task': 'chart.tasks.optimize_database',
        'schedule': 86400.0,  # Daily
    },
    
    # System monitoring
    'system-monitoring': {
        'task': 'system.tasks.system_monitoring',
        'schedule': 300.0,  # Every 5 minutes
    },
    
    # Performance analytics
    'performance-analytics': {
        'task': 'system.tasks.performance_analytics',
        'schedule': 1800.0,  # Every 30 minutes
    },
}

# Development environment detection
if os.getenv('CELERY_ALWAYS_EAGER', 'False').lower() == 'true':
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True

# Production environment optimizations
if not is_windows and os.getenv('CELERY_PRODUCTION', 'False').lower() == 'true':
    # Production-specific optimizations for Unix/Linux
    app.conf.worker_direct = True  # Direct task execution for better performance
    app.conf.task_compression = 'gzip'  # Compress task data
    app.conf.result_compression = 'gzip'  # Compress result data
    app.conf.task_acks_late = True  # Acknowledge tasks after completion
    app.conf.worker_prefetch_multiplier = 1  # Don't prefetch tasks
    app.conf.task_reject_on_worker_lost = True  # Reject tasks if worker dies
