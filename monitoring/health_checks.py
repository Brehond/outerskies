"""
Comprehensive Health Check System for Outer Skies

This module provides health checks for all critical system components:
- Database connectivity and performance
- Redis cache health
- Celery background task system
- AI API connectivity
- Swiss Ephemeris calculations
- File system and storage
- External service dependencies
"""

import time
import logging
import psutil
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.db import connection, DatabaseError
from django.utils import timezone
import requests
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthCheckResult:
    """Represents the result of a health check"""
    
    def __init__(self, name: str, status: str, details: Dict[str, Any] = None, 
                 response_time: float = 0.0, error: str = None):
        self.name = name
        self.status = status  # 'healthy', 'degraded', 'unhealthy'
        self.details = details or {}
        self.response_time = response_time
        self.error = error
        self.timestamp = timezone.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization, converting Path objects to strings recursively."""
        def convert(obj):
            if isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(i) for i in obj]
            else:
                return obj
        return {
            'name': self.name,
            'status': self.status,
            'details': convert(self.details),
            'response_time': round(self.response_time, 3),
            'error': self.error,
            'timestamp': self.timestamp.isoformat()
        }


class SystemHealthChecker:
    """
    Comprehensive system health checker for Outer Skies
    """
    
    def __init__(self):
        self.results: List[HealthCheckResult] = []
        self.start_time = time.time()
    
    def check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # Test performance with a simple query
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                migration_count = cursor.fetchone()[0]
            
            # Check connection pool
            db_info = connection.get_connection_params()
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name="database",
                status="healthy",
                details={
                    'migration_count': migration_count,
                    'database_name': str(db_info.get('database', 'unknown')),
                    'host': db_info.get('host', 'unknown'),
                    'port': db_info.get('port', 'unknown')
                },
                response_time=response_time
            )
            
        except DatabaseError as e:
            return HealthCheckResult(
                name="database",
                status="unhealthy",
                error=f"Database connection failed: {str(e)}",
                response_time=time.time() - start_time
            )
        except Exception as e:
            return HealthCheckResult(
                name="database",
                status="degraded",
                error=f"Database check error: {str(e)}",
                response_time=time.time() - start_time
            )
    
    def check_redis_health(self) -> HealthCheckResult:
        """Check Redis cache health"""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            cache.set('health_check', 'ok', timeout=10)
            test_value = cache.get('health_check')
            
            if test_value != 'ok':
                raise Exception("Cache read/write test failed")
            
            # Test cache performance
            cache.set('performance_test', 'data', timeout=60)
            cache.get('performance_test')
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name="redis_cache",
                status="healthy",
                details={
                    'cache_backend': getattr(settings, 'CACHE_BACKEND', 'default'),
                    'cache_location': getattr(settings, 'CACHE_LOCATION', 'unknown')
                },
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="redis_cache",
                status="unhealthy",
                error=f"Redis cache failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    def check_celery_health(self) -> HealthCheckResult:
        """Check Celery background task system"""
        start_time = time.time()
        
        try:
            from chart.celery_utils import enhanced_celery_manager
            
            # Check Celery availability
            is_available = enhanced_celery_manager.is_celery_available()
            
            if not is_available:
                return HealthCheckResult(
                    name="celery",
                    status="degraded",
                    details={'available': False, 'fallback_mode': True},
                    response_time=time.time() - start_time
                )
            
            # Get system health
            health_info = enhanced_celery_manager.get_system_health()
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name="celery",
                status="healthy",
                details=health_info,
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="celery",
                status="degraded",
                error=f"Celery health check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    def check_ai_api_health(self) -> HealthCheckResult:
        """Check AI API connectivity"""
        start_time = time.time()
        
        try:
            from ai_integration.openrouter_api import get_available_models
            
            # Test API connectivity
            models = get_available_models()
            
            if not models:
                raise Exception("No AI models available")
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name="ai_api",
                status="healthy",
                details={
                    'available_models': len(models),
                    'model_names': list(models.keys())[:5]  # First 5 models
                },
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="ai_api",
                status="degraded",
                error=f"AI API check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    def check_ephemeris_health(self) -> HealthCheckResult:
        """Check Swiss Ephemeris calculations"""
        start_time = time.time()
        
        try:
            import swisseph as swe
            
            # Test basic ephemeris calculation
            jd = swe.julday(2024, 1, 1, 12.0)
            result = swe.calc_ut(jd, swe.SUN)
            
            if not result or len(result) < 2:
                raise Exception("Ephemeris calculation failed")
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name="ephemeris",
                status="healthy",
                details={
                    'swiss_ephemeris_version': getattr(swe, 'version', 'unknown'),
                    'test_calculation': 'successful'
                },
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="ephemeris",
                status="unhealthy",
                error=f"Ephemeris check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    def check_file_system_health(self) -> HealthCheckResult:
        """Check file system and storage"""
        start_time = time.time()
        
        try:
            # Check disk usage
            disk_usage = psutil.disk_usage('/')
            disk_percent = disk_usage.percent
            
            # Check if we can write to media directory
            media_dir = getattr(settings, 'MEDIA_ROOT', '/tmp')
            test_file = os.path.join(media_dir, 'health_check_test.txt')
            
            try:
                with open(test_file, 'w') as f:
                    f.write('health_check')
                
                with open(test_file, 'r') as f:
                    content = f.read()
                
                os.remove(test_file)
                
                if content != 'health_check':
                    raise Exception("File system read/write test failed")
                    
            except Exception as e:
                raise Exception(f"File system test failed: {str(e)}")
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name="file_system",
                status="healthy" if disk_percent < 90 else "degraded",
                details={
                    'disk_usage_percent': disk_percent,
                    'disk_free_gb': round(disk_usage.free / (1024**3), 2),
                    'disk_total_gb': round(disk_usage.total / (1024**3), 2),
                    'media_directory': media_dir
                },
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="file_system",
                status="unhealthy",
                error=f"File system check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    def check_memory_health(self) -> HealthCheckResult:
        """Check system memory usage"""
        start_time = time.time()
        
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name="memory",
                status="healthy" if memory_percent < 85 else "degraded",
                details={
                    'memory_usage_percent': memory_percent,
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'memory_total_gb': round(memory.total / (1024**3), 2)
                },
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status="degraded",
                error=f"Memory check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    def check_external_services(self) -> HealthCheckResult:
        """Check external service dependencies"""
        start_time = time.time()
        
        try:
            # Check if we can reach external services
            services_status = {}
            
            # Test basic internet connectivity
            try:
                response = requests.get('https://httpbin.org/status/200', timeout=5)
                services_status['internet'] = response.status_code == 200
            except:
                services_status['internet'] = False
            
            # Test DNS resolution
            try:
                import socket
                socket.gethostbyname('google.com')
                services_status['dns'] = True
            except:
                services_status['dns'] = False
            
            response_time = time.time() - start_time
            
            # Determine overall status
            healthy_services = sum(services_status.values())
            total_services = len(services_status)
            
            if healthy_services == total_services:
                status = "healthy"
            elif healthy_services > 0:
                status = "degraded"
            else:
                status = "unhealthy"
            
            return HealthCheckResult(
                name="external_services",
                status=status,
                details={
                    'services': services_status,
                    'healthy_count': healthy_services,
                    'total_count': total_services
                },
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="external_services",
                status="degraded",
                error=f"External services check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    def run_all_health_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive results"""
        logger.info("Starting comprehensive health checks...")
        
        # Run all health checks
        checks = [
            self.check_database_health,
            self.check_redis_health,
            self.check_celery_health,
            self.check_ai_api_health,
            self.check_ephemeris_health,
            self.check_file_system_health,
            self.check_memory_health,
            self.check_external_services
        ]
        
        for check_func in checks:
            try:
                result = check_func()
                self.results.append(result)
                logger.info(f"Health check {result.name}: {result.status}")
            except Exception as e:
                logger.error(f"Health check {check_func.__name__} failed: {e}")
                error_result = HealthCheckResult(
                    name=check_func.__name__.replace('check_', '').replace('_health', ''),
                    status="unhealthy",
                    error=f"Health check failed: {str(e)}"
                )
                self.results.append(error_result)
        
        # Calculate overall health
        total_time = time.time() - self.start_time
        healthy_count = sum(1 for r in self.results if r.status == 'healthy')
        degraded_count = sum(1 for r in self.results if r.status == 'degraded')
        unhealthy_count = sum(1 for r in self.results if r.status == 'unhealthy')
        
        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            'overall_status': overall_status,
            'timestamp': timezone.now().isoformat(),
            'total_checks': len(self.results),
            'healthy_count': healthy_count,
            'degraded_count': degraded_count,
            'unhealthy_count': unhealthy_count,
            'total_time': round(total_time, 3),
            'checks': [result.to_dict() for result in self.results]
        }


# Global health checker instance
health_checker = SystemHealthChecker()


def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status"""
    return health_checker.run_all_health_checks()


def get_quick_health_status() -> str:
    """Get quick health status for load balancers"""
    try:
        # Quick database check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Quick cache check
        cache.set('quick_health', 'ok', timeout=5)
        if cache.get('quick_health') != 'ok':
            return "unhealthy"
        
        return "healthy"
    except:
        return "unhealthy" 