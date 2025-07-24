"""
Database Optimization Service

This module provides database optimization features including:
- Query optimization and monitoring
- Connection pooling management
- Database performance analytics
- Index optimization recommendations
- Query caching strategies
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from django.db import connection, connections
from django.db.models import QuerySet
from django.core.cache import cache
from django.conf import settings
from django.db.models.sql import Query
from django.db.models.sql.compiler import SQLCompiler
import psutil
import threading

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """
    Database optimization service that provides query optimization,
    connection pooling, and performance monitoring.
    """
    
    def __init__(self):
        self.query_log = []
        self.slow_query_threshold = 1.0  # seconds
        self.max_query_log_size = 1000
        self.connection_pool_stats = {}
        self._lock = threading.Lock()
    
    def optimize_query(self, queryset: QuerySet, **kwargs) -> QuerySet:
        """
        Optimize a Django queryset for better performance.
        
        Args:
            queryset: Django queryset to optimize
            **kwargs: Optimization options
            
        Returns:
            Optimized queryset
        """
        # Add select_related for foreign keys
        if 'select_related' in kwargs:
            queryset = queryset.select_related(*kwargs['select_related'])
        
        # Add prefetch_related for many-to-many and reverse foreign keys
        if 'prefetch_related' in kwargs:
            queryset = queryset.prefetch_related(*kwargs['prefetch_related'])
        
        # Add only() to select specific fields
        if 'only' in kwargs:
            queryset = queryset.only(*kwargs['only'])
        
        # Add defer() to exclude specific fields
        if 'defer' in kwargs:
            queryset = queryset.defer(*kwargs['defer'])
        
        # Add distinct() to remove duplicates
        if kwargs.get('distinct', False):
            queryset = queryset.distinct()
        
        return queryset
    
    def monitor_query(self, queryset: QuerySet, operation_name: str = None) -> QuerySet:
        """
        Monitor a query for performance analysis.
        
        Args:
            queryset: QuerySet to monitor
            operation_name: Name of the operation for logging
            
        Returns:
            Monitored queryset
        """
        start_time = time.time()
        
        try:
            # Execute the query
            result = list(queryset)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log query performance
            self._log_query_performance(queryset, execution_time, operation_name)
            
            # Check for slow queries
            if execution_time > self.slow_query_threshold:
                self._log_slow_query(queryset, execution_time, operation_name)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query failed after {execution_time:.3f}s: {str(e)}")
            raise
    
    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """
        Get database connection pool statistics.
        
        Returns:
            Dictionary with connection pool stats
        """
        stats = {}
        
        try:
            # Get default database connection stats
            default_conn = connections['default']
            
            if hasattr(default_conn, 'connection'):
                conn = default_conn.connection
                
                # PostgreSQL specific stats
                if hasattr(conn, 'info'):
                    stats['postgresql'] = {
                        'backend_pid': getattr(conn.info, 'backend_pid', None),
                        'parameter_status': getattr(conn.info, 'parameter_status', {}),
                        'transaction_status': getattr(conn.info, 'transaction_status', None),
                    }
                
                # Connection age
                if hasattr(default_conn, '_conn_age'):
                    stats['connection_age'] = default_conn._conn_age
                
                # Connection count
                stats['connection_count'] = getattr(default_conn, '_connection_count', 0)
                
        except Exception as e:
            logger.error(f"Failed to get connection pool stats: {e}")
        
        return stats
    
    def optimize_connection_pool(self) -> Dict[str, Any]:
        """
        Optimize database connection pool settings.
        
        Returns:
            Dictionary with optimization results
        """
        optimizations = {}
        
        try:
            # Get current database settings
            db_settings = settings.DATABASES.get('default', {})
            
            # Check connection max age
            current_max_age = db_settings.get('CONN_MAX_AGE', 0)
            if current_max_age < 600:  # Less than 10 minutes
                optimizations['conn_max_age'] = {
                    'current': current_max_age,
                    'recommended': 600,
                    'description': 'Increase connection max age to reduce connection overhead'
                }
            
            # Check for connection pooling options
            if 'OPTIONS' not in db_settings:
                optimizations['connection_pooling'] = {
                    'current': 'Not configured',
                    'recommended': 'Enable connection pooling',
                    'description': 'Add connection pooling options for better performance'
                }
            
            # PostgreSQL specific optimizations
            if db_settings.get('ENGINE') == 'django.db.backends.postgresql':
                options = db_settings.get('OPTIONS', {})
                
                # Check for connection pooling
                if 'MAX_CONNS' not in options:
                    optimizations['postgresql_pooling'] = {
                        'current': 'Not configured',
                        'recommended': 'Add MAX_CONNS and MIN_CONNS',
                        'description': 'Configure PostgreSQL connection pooling'
                    }
                
                # Check for application name
                if 'application_name' not in options:
                    optimizations['application_name'] = {
                        'current': 'Not set',
                        'recommended': 'Set application_name',
                        'description': 'Set application name for better monitoring'
                    }
            
        except Exception as e:
            logger.error(f"Failed to optimize connection pool: {e}")
        
        return optimizations
    
    def get_query_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get query performance analytics.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with query analytics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            # Filter queries within time window
            recent_queries = [
                q for q in self.query_log
                if q['timestamp'] >= cutoff_time
            ]
        
        if not recent_queries:
            return {
                'total_queries': 0,
                'avg_execution_time': 0,
                'slow_queries': 0,
                'slow_query_percentage': 0,
                'most_common_operations': [],
                'execution_time_distribution': {}
            }
        
        # Calculate statistics
        execution_times = [q['execution_time'] for q in recent_queries]
        slow_queries = [q for q in recent_queries if q['execution_time'] > self.slow_query_threshold]
        
        # Most common operations
        operation_counts = {}
        for query in recent_queries:
            op = query.get('operation_name', 'unknown')
            operation_counts[op] = operation_counts.get(op, 0) + 1
        
        most_common = sorted(operation_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Execution time distribution
        time_distribution = {
            'fast': len([t for t in execution_times if t < 0.1]),
            'normal': len([t for t in execution_times if 0.1 <= t < 1.0]),
            'slow': len([t for t in execution_times if 1.0 <= t < 5.0]),
            'very_slow': len([t for t in execution_times if t >= 5.0])
        }
        
        return {
            'total_queries': len(recent_queries),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'max_execution_time': max(execution_times),
            'slow_queries': len(slow_queries),
            'slow_query_percentage': (len(slow_queries) / len(recent_queries)) * 100,
            'most_common_operations': most_common,
            'execution_time_distribution': time_distribution,
            'analysis_period_hours': hours
        }
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the slowest queries for analysis.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of slow query dictionaries
        """
        with self._lock:
            slow_queries = [
                q for q in self.query_log
                if q['execution_time'] > self.slow_query_threshold
            ]
        
        # Sort by execution time (slowest first)
        slow_queries.sort(key=lambda x: x['execution_time'], reverse=True)
        
        return slow_queries[:limit]
    
    def recommend_indexes(self) -> List[Dict[str, Any]]:
        """
        Recommend database indexes based on query patterns.
        
        Returns:
            List of index recommendations
        """
        recommendations = []
        
        # Analyze query patterns
        with self._lock:
            recent_queries = self.query_log[-100:]  # Last 100 queries
        
        # Group queries by table
        table_queries = {}
        for query in recent_queries:
            sql = query.get('sql', '').lower()
            
            # Extract table names from SQL (simplified)
            if 'from ' in sql:
                table_match = sql.split('from ')[1].split()[0]
                if table_match not in table_queries:
                    table_queries[table_match] = []
                table_queries[table_match].append(query)
        
        # Generate recommendations for each table
        for table, queries in table_queries.items():
            # Analyze WHERE clauses
            where_clauses = []
            for query in queries:
                sql = query.get('sql', '').lower()
                if 'where ' in sql:
                    where_part = sql.split('where ')[1].split('order by')[0].split('limit')[0]
                    where_clauses.append(where_part)
            
            # Find common WHERE patterns
            common_columns = self._analyze_where_clauses(where_clauses)
            
            if common_columns:
                recommendations.append({
                    'table': table,
                    'recommended_indexes': common_columns,
                    'query_count': len(queries),
                    'avg_execution_time': sum(q['execution_time'] for q in queries) / len(queries)
                })
        
        return recommendations
    
    def clear_query_log(self):
        """Clear the query log."""
        with self._lock:
            self.query_log.clear()
    
    def _log_query_performance(self, queryset: QuerySet, execution_time: float, operation_name: str = None):
        """Log query performance data."""
        with self._lock:
            # Get SQL query
            sql = str(queryset.query)
            
            # Add to query log
            query_data = {
                'timestamp': datetime.now(),
                'sql': sql[:500] + '...' if len(sql) > 500 else sql,  # Truncate long queries
                'execution_time': execution_time,
                'operation_name': operation_name,
                'model': queryset.model.__name__ if hasattr(queryset, 'model') else 'Unknown'
            }
            
            self.query_log.append(query_data)
            
            # Maintain log size
            if len(self.query_log) > self.max_query_log_size:
                self.query_log.pop(0)
    
    def _log_slow_query(self, queryset: QuerySet, execution_time: float, operation_name: str = None):
        """Log slow query for analysis."""
        sql = str(queryset.query)
        model_name = queryset.model.__name__ if hasattr(queryset, 'model') else 'Unknown'
        
        logger.warning(
            f"Slow query detected: {model_name}.{operation_name or 'unknown'} "
            f"took {execution_time:.3f}s - {sql[:200]}..."
        )
    
    def _analyze_where_clauses(self, where_clauses: List[str]) -> List[str]:
        """Analyze WHERE clauses to find common column patterns."""
        column_patterns = {}
        
        for clause in where_clauses:
            # Simple pattern matching for common WHERE conditions
            if 'user_id' in clause:
                column_patterns['user_id'] = column_patterns.get('user_id', 0) + 1
            if 'created_at' in clause:
                column_patterns['created_at'] = column_patterns.get('created_at', 0) + 1
            if 'status' in clause:
                column_patterns['status'] = column_patterns.get('status', 0) + 1
            if 'is_active' in clause:
                column_patterns['is_active'] = column_patterns.get('is_active', 0) + 1
        
        # Return columns that appear frequently
        return [col for col, count in column_patterns.items() if count >= 3]


class QueryCache:
    """
    Query caching service for frequently executed queries.
    """
    
    def __init__(self, default_timeout: int = 300):
        self.default_timeout = default_timeout
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0
        }
    
    def cached_query(self, cache_key: str, queryset: QuerySet, timeout: int = None) -> QuerySet:
        """
        Execute a query with caching.
        
        Args:
            cache_key: Cache key for the query
            queryset: QuerySet to execute
            timeout: Cache timeout in seconds
            
        Returns:
            QuerySet result (from cache if available)
        """
        if timeout is None:
            timeout = self.default_timeout
        
        # Try to get from cache
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            self.cache_stats['hits'] += 1
            return cached_result
        
        # Execute query and cache result
        result = list(queryset)
        cache.set(cache_key, result, timeout)
        
        self.cache_stats['misses'] += 1
        self.cache_stats['sets'] += 1
        
        return result
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match cache keys
        """
        # This is a simplified implementation
        # In production, you'd use Redis SCAN or similar
        logger.info(f"Cache invalidation requested for pattern: {pattern}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return self.cache_stats.copy()


class DatabaseHealthMonitor:
    """
    Database health monitoring service.
    """
    
    def __init__(self):
        self.health_checks = []
    
    def check_database_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive database health check.
        
        Returns:
            Dictionary with health check results
        """
        health_status = {
            'overall_status': 'healthy',
            'checks': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Check database connectivity
        connectivity_check = self._check_connectivity()
        health_status['checks']['connectivity'] = connectivity_check
        
        # Check connection pool
        pool_check = self._check_connection_pool()
        health_status['checks']['connection_pool'] = pool_check
        
        # Check query performance
        performance_check = self._check_query_performance()
        health_status['checks']['query_performance'] = performance_check
        
        # Check disk space (if available)
        disk_check = self._check_disk_space()
        health_status['checks']['disk_space'] = disk_check
        
        # Determine overall status
        failed_checks = [
            check for check in health_status['checks'].values()
            if check.get('status') == 'failed'
        ]
        
        if failed_checks:
            health_status['overall_status'] = 'unhealthy'
        elif any(check.get('status') == 'warning' for check in health_status['checks'].values()):
            health_status['overall_status'] = 'degraded'
        
        return health_status
    
    def _check_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    return {
                        'status': 'healthy',
                        'message': 'Database connection successful',
                        'response_time': 0.001  # Placeholder
                    }
                else:
                    return {
                        'status': 'failed',
                        'message': 'Database connection failed - unexpected response'
                    }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'Database connection failed: {str(e)}'
            }
    
    def _check_connection_pool(self) -> Dict[str, Any]:
        """Check connection pool health."""
        try:
            # Get connection stats
            default_conn = connections['default']
            
            # Check if connection is stale
            if hasattr(default_conn, 'connection') and default_conn.connection:
                # Try a simple query to test connection
                with default_conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                
                return {
                    'status': 'healthy',
                    'message': 'Connection pool is healthy',
                    'active_connections': 1  # Placeholder
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'No active database connection'
                }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'Connection pool check failed: {str(e)}'
            }
    
    def _check_query_performance(self) -> Dict[str, Any]:
        """Check query performance."""
        try:
            # Execute a simple query and measure time
            start_time = time.time()
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM chart_chart")
                result = cursor.fetchone()
            
            execution_time = time.time() - start_time
            
            if execution_time < 0.1:
                status = 'healthy'
            elif execution_time < 1.0:
                status = 'warning'
            else:
                status = 'failed'
            
            return {
                'status': status,
                'message': f'Query performance check completed in {execution_time:.3f}s',
                'execution_time': execution_time,
                'result': result[0] if result else 0
            }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f'Query performance check failed: {str(e)}'
            }
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space (if available)."""
        try:
            # Get disk usage for database directory
            disk_usage = psutil.disk_usage('/')
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            if usage_percent < 80:
                status = 'healthy'
            elif usage_percent < 90:
                status = 'warning'
            else:
                status = 'failed'
            
            return {
                'status': status,
                'message': f'Disk usage: {usage_percent:.1f}%',
                'usage_percent': usage_percent,
                'free_gb': disk_usage.free / (1024**3)
            }
        except Exception as e:
            return {
                'status': 'warning',
                'message': f'Could not check disk space: {str(e)}'
            }


# Global instances
db_optimizer = DatabaseOptimizer()
query_cache = QueryCache()
health_monitor = DatabaseHealthMonitor() 