"""
Optimized Chart Orchestrator with Performance Monitoring

This module provides an optimized version of the chart orchestrator with:
- Performance monitoring and profiling
- Enhanced caching with connection pooling
- Async support for heavy calculations
- Background task optimization
- Resource usage monitoring
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import wraps

from .chart_orchestrator import ChartOrchestrator
from .enhanced_caching_service import enhanced_cache, cache_result, async_cache_result
from monitoring.enhanced_performance_monitor import performance_monitor, monitor_performance

logger = logging.getLogger(__name__)


class OptimizedChartOrchestrator(ChartOrchestrator):
    """
    Optimized chart orchestrator with performance monitoring and enhanced caching
    """
    
    def __init__(self):
        super().__init__()
        self.performance_monitor = performance_monitor
        self.cache = enhanced_cache
        self._setup_performance_monitoring()
    
    def _setup_performance_monitoring(self):
        """Setup performance monitoring for chart operations"""
        # Start system monitoring
        self.performance_monitor.start_monitoring()
        
        # Add custom alerts for chart operations
        from monitoring.enhanced_performance_monitor import PerformanceAlert
        
        slow_chart_alert = PerformanceAlert(
            name="Slow Chart Calculation",
            condition=lambda current, threshold: current > threshold,
            threshold=5000.0,  # 5 seconds
            severity="warning"
        )
        
        high_memory_alert = PerformanceAlert(
            name="High Memory During Chart Calculation",
            condition=lambda current, threshold: current > threshold,
            threshold=85.0,  # 85% memory usage
            severity="critical"
        )
        
        self.performance_monitor.add_alert(slow_chart_alert)
        self.performance_monitor.add_alert(high_memory_alert)
    
    @monitor_performance("calculate_complete_chart")
    @cache_result("chart", timeout=3600)
    def calculate_complete_chart(self, dt: datetime, latitude: float, longitude: float,
                                house_system: str = "Placidus", include_aspects: bool = True,
                                include_dignities: bool = True) -> Dict[str, Any]:
        """
        Calculate complete chart with performance monitoring and caching
        
        Args:
            dt: Birth datetime
            latitude: Birth latitude
            longitude: Birth longitude
            house_system: House system to use
            include_aspects: Whether to include aspects
            include_dignities: Whether to include dignities
            
        Returns:
            Complete chart data
        """
        start_time = time.time()
        
        try:
            # Check performance alerts before calculation
            self.performance_monitor.check_alerts({
                'operation': 'calculate_complete_chart',
                'latitude': latitude,
                'longitude': longitude,
                'house_system': house_system
            })
            
            # Perform calculation using parent class
            result = super().calculate_complete_chart(
                dt, latitude, longitude, house_system, include_aspects, include_dignities
            )
            
            # Add performance metadata
            calculation_time = (time.time() - start_time) * 1000
            result['performance_metadata'] = {
                'calculation_time_ms': round(calculation_time, 2),
                'timestamp': datetime.now().isoformat(),
                'cache_hit': False  # This will be set by cache decorator
            }
            
            # Check alerts after calculation
            self.performance_monitor.check_alerts({
                'operation': 'calculate_complete_chart',
                'calculation_time_ms': calculation_time,
                'result_size': len(str(result))
            })
            
            return result
            
        except Exception as e:
            calculation_time = (time.time() - start_time) * 1000
            logger.error(f"Chart calculation failed after {calculation_time:.2f}ms: {e}")
            
            # Record error in performance monitor
            self.performance_monitor.profiler._record_metric(
                "calculate_complete_chart", calculation_time, False, str(e)
            )
            raise
    
    @monitor_performance("calculate_planetary_positions")
    @cache_result("ephemeris", timeout=7200)
    def calculate_planetary_positions(self, dt: datetime, latitude: float, longitude: float) -> Dict[str, Any]:
        """Calculate planetary positions with caching"""
        return super().calculate_planetary_positions(dt, latitude, longitude)
    
    @monitor_performance("calculate_houses")
    @cache_result("ephemeris", timeout=7200)
    def calculate_houses(self, dt: datetime, latitude: float, longitude: float,
                        house_system: str = "Placidus") -> Dict[str, Any]:
        """Calculate houses with caching"""
        return super().calculate_houses(dt, latitude, longitude, house_system)
    
    @monitor_performance("calculate_aspects")
    def calculate_aspects(self, planetary_positions: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate aspects with performance monitoring"""
        return super().calculate_aspects(planetary_positions)
    
    @monitor_performance("calculate_dignities")
    def calculate_dignities(self, planetary_positions: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate dignities with performance monitoring"""
        return super().calculate_dignities(planetary_positions)
    
    async def calculate_complete_chart_async(self, dt: datetime, latitude: float, longitude: float,
                                           house_system: str = "Placidus", include_aspects: bool = True,
                                           include_dignities: bool = True) -> Dict[str, Any]:
        """
        Async version of complete chart calculation
        
        Args:
            dt: Birth datetime
            latitude: Birth latitude
            longitude: Birth longitude
            house_system: House system to use
            include_aspects: Whether to include aspects
            include_dignities: Whether to include dignities
            
        Returns:
            Complete chart data
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.calculate_complete_chart,
            dt, latitude, longitude, house_system, include_aspects, include_dignities
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for chart operations"""
        return self.performance_monitor.get_performance_summary()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return self.cache.get_performance_summary()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        return {
            'performance': self.get_performance_summary(),
            'cache': self.cache.get_health_status(),
            'system': self.performance_monitor.system_monitor.get_current_metrics()
        }
    
    def optimize_cache(self):
        """Optimize cache based on performance metrics"""
        cache_stats = self.cache.get_performance_summary()
        performance_stats = self.get_performance_summary()
        
        recommendations = []
        
        # Check cache hit rate
        if cache_stats['cache_performance']['hit_rate_percent'] < 70:
            recommendations.append("Consider increasing cache timeouts for frequently accessed data")
        
        # Check for slow operations
        slow_operations = [
            op for op, stats in performance_stats['operation_stats'].items()
            if stats.get('average_time_ms', 0) > 1000
        ]
        
        if slow_operations:
            recommendations.append(f"Optimize slow operations: {', '.join(slow_operations)}")
        
        # Check memory usage
        system_metrics = self.performance_monitor.system_monitor.get_current_metrics()
        if system_metrics['memory_percent'] > 80:
            recommendations.append("High memory usage - consider clearing old cache entries")
        
        return recommendations
    
    def clear_old_cache(self, days: int = 7):
        """Clear cache entries older than specified days"""
        try:
            # This would require Redis to support TTL-based cleanup
            # For now, we'll clear by prefix
            cleared_charts = self.cache.clear_prefix('chart')
            cleared_ephemeris = self.cache.clear_prefix('ephemeris')
            
            logger.info(f"Cleared {cleared_charts} chart cache entries and {cleared_ephemeris} ephemeris cache entries")
            
            return {
                'cleared_charts': cleared_charts,
                'cleared_ephemeris': cleared_ephemeris,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {'error': str(e)}
    
    def batch_calculate_charts(self, chart_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate multiple charts in batch for better performance
        
        Args:
            chart_requests: List of chart request dictionaries
            
        Returns:
            List of chart results
        """
        results = []
        
        for i, request in enumerate(chart_requests):
            try:
                dt = request['datetime']
                lat = request['latitude']
                lon = request['longitude']
                house_system = request.get('house_system', 'Placidus')
                
                result = self.calculate_complete_chart(
                    dt, lat, lon, house_system, 
                    include_aspects=True, include_dignities=True
                )
                
                results.append({
                    'success': True,
                    'index': i,
                    'result': result
                })
                
            except Exception as e:
                results.append({
                    'success': False,
                    'index': i,
                    'error': str(e)
                })
        
        return results
    
    async def batch_calculate_charts_async(self, chart_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Async version of batch chart calculation"""
        tasks = []
        
        for request in chart_requests:
            dt = request['datetime']
            lat = request['latitude']
            lon = request['longitude']
            house_system = request.get('house_system', 'Placidus')
            
            task = self.calculate_complete_chart_async(
                dt, lat, lon, house_system, 
                include_aspects=True, include_dignities=True
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Format results
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    'success': False,
                    'index': i,
                    'error': str(result)
                })
            else:
                formatted_results.append({
                    'success': True,
                    'index': i,
                    'result': result
                })
        
        return formatted_results
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Get comprehensive optimization recommendations"""
        performance_summary = self.get_performance_summary()
        cache_stats = self.get_cache_stats()
        system_health = self.get_system_health()
        
        recommendations = {
            'performance': performance_summary['recommendations'],
            'cache': cache_stats['recommendations'],
            'system': []
        }
        
        # System-specific recommendations
        system_metrics = system_health['system']
        
        if system_metrics['cpu_percent'] > 80:
            recommendations['system'].append("Consider scaling up CPU resources or optimizing CPU-intensive operations")
        
        if system_metrics['memory_percent'] > 85:
            recommendations['system'].append("Consider increasing memory or implementing memory optimization strategies")
        
        if system_metrics['disk_usage_percent'] > 90:
            recommendations['system'].append("Disk space is running low - consider cleanup or storage expansion")
        
        # Cache optimization
        if cache_stats['cache_performance']['hit_rate_percent'] < 60:
            recommendations['cache'].append("Cache hit rate is low - review cache key strategies and timeouts")
        
        # Performance optimization
        slow_ops = [
            op for op, stats in performance_summary['operation_stats'].items()
            if stats.get('average_time_ms', 0) > 2000
        ]
        
        if slow_ops:
            recommendations['performance'].append(f"Critical: Operations {', '.join(slow_ops)} are very slow and need immediate optimization")
        
        return recommendations


# Global optimized instance
optimized_orchestrator = OptimizedChartOrchestrator()


def get_optimized_orchestrator() -> OptimizedChartOrchestrator:
    """Get the global optimized orchestrator instance"""
    return optimized_orchestrator 