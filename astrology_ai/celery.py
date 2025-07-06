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

# Configure task routing
app.conf.task_routes = {
    'chart.tasks.generate_chart_task': {'queue': 'chart_generation'},
    'chart.tasks.generate_interpretation_task': {'queue': 'ai_processing'},
    'chart.tasks.calculate_ephemeris_task': {'queue': 'ephemeris'},
    'chart.tasks.cleanup_old_tasks': {'queue': 'maintenance'},
    'chart.tasks.health_check': {'queue': 'maintenance'},
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

# Windows-specific configuration
if platform.system() == 'Windows':
    # Use solo pool on Windows to avoid multiprocessing issues
    app.conf.worker_pool = 'solo'
    app.conf.worker_concurrency = 1
    app.conf.worker_prefetch_multiplier = 1
    app.conf.worker_disable_rate_limits = True
    
    # Windows-specific broker settings
    app.conf.broker_transport_options = {
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True,
        'socket_connect_timeout': 10,
        'socket_timeout': 10,
        'retry_on_timeout': True,
        'max_connections': 20,
        'connection_pool': {
            'max_connections': 20,
            'retry_on_timeout': True,
        }
    }
    
    # Windows-specific result backend settings
    app.conf.result_backend_transport_options = {
        'visibility_timeout': 3600,
        'socket_connect_timeout': 10,
        'socket_timeout': 10,
        'retry_on_timeout': True,
    }
else:
    # Linux/Unix settings
    app.conf.worker_prefetch_multiplier = 1
    app.conf.worker_max_tasks_per_child = 1000

# Configure result backend and broker (moved to avoid settings access issues)
def configure_celery():
    app.conf.result_backend = settings.CELERY_RESULT_BACKEND
    app.conf.broker_url = settings.CELERY_BROKER_URL

# Call configuration function
configure_celery()

# Configure periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-tasks': {
        'task': 'chart.tasks.cleanup_old_tasks',
        'schedule': 3600.0,  # Every hour
    },
    'health-check': {
        'task': 'chart.tasks.health_check',
        'schedule': 300.0,  # Every 5 minutes
    },
}

# Development environment detection
if os.getenv('CELERY_ALWAYS_EAGER', 'False').lower() == 'true':
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True 