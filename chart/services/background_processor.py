"""
Enhanced Background Processing Service

This module provides advanced background processing capabilities including:
- Task prioritization and queuing
- Comprehensive retry strategies with exponential backoff
- Task monitoring and alerting
- Resource management and load balancing
- Dead letter queue handling
- Performance analytics
"""

import logging
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from celery import current_app
from celery.result import AsyncResult
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BULK = 4


class TaskStatus(Enum):
    """Enhanced task status tracking."""
    PENDING = 'pending'
    QUEUED = 'queued'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRYING = 'retrying'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'
    DEAD_LETTER = 'dead_letter'


@dataclass
class TaskMetadata:
    """Task metadata for enhanced tracking."""
    task_id: str
    task_name: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300  # 5 minutes default
    user_id: Optional[int] = None
    resource_usage: Dict[str, Any] = None
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.resource_usage is None:
            self.resource_usage = {}
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


class EnhancedBackgroundProcessor:
    """
    Enhanced background processor with advanced features for task management,
    prioritization, and monitoring.
    """
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        self.task_queues = {
            TaskPriority.CRITICAL: 'critical',
            TaskPriority.HIGH: 'high',
            TaskPriority.NORMAL: 'normal',
            TaskPriority.LOW: 'low',
            TaskPriority.BULK: 'bulk'
        }
        self.retry_strategies = {
            'exponential': self._exponential_backoff,
            'linear': self._linear_backoff,
            'fixed': self._fixed_backoff
        }
        self.monitoring_enabled = True
        self.alert_thresholds = {
            'queue_size': 100,
            'failure_rate': 0.1,  # 10%
            'avg_processing_time': 300,  # 5 minutes
            'memory_usage': 0.8  # 80%
        }
    
    def submit_task(self, task_name: str, args: tuple = None, kwargs: dict = None,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   user_id: Optional[int] = None,
                   timeout: int = 300,
                   max_retries: int = 3,
                   retry_strategy: str = 'exponential',
                   tags: List[str] = None) -> str:
        """
        Submit a task with enhanced metadata and prioritization.
        
        Args:
            task_name: Name of the task to execute
            args: Task arguments
            kwargs: Task keyword arguments
            priority: Task priority level
            user_id: User ID associated with the task
            timeout: Task timeout in seconds
            max_retries: Maximum number of retries
            retry_strategy: Retry strategy to use
            tags: Tags for task categorization
            
        Returns:
            Task ID
        """
        try:
            # Generate task ID
            task_id = self._generate_task_id(task_name, args, kwargs, user_id)
            
            # Create task metadata
            metadata = TaskMetadata(
                task_id=task_id,
                task_name=task_name,
                priority=priority,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                user_id=user_id,
                timeout=timeout,
                max_retries=max_retries,
                tags=tags or []
            )
            
            # Store metadata
            self._store_task_metadata(metadata)
            
            # Submit to Celery with priority
            queue = self.task_queues[priority]
            task_result = current_app.send_task(
                task_name,
                args=args or (),
                kwargs=kwargs or {},
                task_id=task_id,
                queue=queue,
                expires=timeout,
                retry=True,
                retry_policy={
                    'max_retries': max_retries,
                    'interval_start': 0,
                    'interval_step': 0.2,
                    'interval_max': 0.2,
                }
            )
            
            # Update status to queued
            metadata.status = TaskStatus.QUEUED
            self._update_task_metadata(metadata)
            
            # Track task submission
            self._track_task_submission(metadata)
            
            logger.info(f"Task submitted: {task_id} ({task_name}) with priority {priority.name}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to submit task {task_name}: {e}")
            raise
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get comprehensive task status and metadata.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Dictionary with task status and metadata
        """
        try:
            # Get Celery result
            celery_result = AsyncResult(task_id)
            
            # Get stored metadata
            metadata = self._get_task_metadata(task_id)
            
            if not metadata:
                return {
                    'task_id': task_id,
                    'status': 'not_found',
                    'error': 'Task metadata not found'
                }
            
            # Update metadata with current status
            metadata.status = self._map_celery_status(celery_result.status)
            
            if celery_result.ready():
                metadata.completed_at = datetime.now()
                
                if celery_result.successful():
                    metadata.result_data = celery_result.result
                else:
                    metadata.error_message = str(celery_result.info)
            
            # Update stored metadata
            self._update_task_metadata(metadata)
            
            # Get additional metrics
            metrics = self._get_task_metrics(task_id)
            
            return {
                **metadata.to_dict(),
                'celery_status': celery_result.status,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return {
                'task_id': task_id,
                'status': 'error',
                'error': str(e)
            }
    
    def cancel_task(self, task_id: str, force: bool = False) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task ID to cancel
            force: Force cancellation even if task is running
            
        Returns:
            True if task was cancelled successfully
        """
        try:
            # Get task metadata
            metadata = self._get_task_metadata(task_id)
            if not metadata:
                return False
            
            # Check if task can be cancelled
            if metadata.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            # Cancel in Celery
            celery_result = AsyncResult(task_id)
            celery_result.revoke(terminate=force)
            
            # Update metadata
            metadata.status = TaskStatus.CANCELLED
            metadata.completed_at = datetime.now()
            self._update_task_metadata(metadata)
            
            # Track cancellation
            self._track_task_cancellation(metadata)
            
            logger.info(f"Task cancelled: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    def retry_task(self, task_id: str, delay: int = 0) -> bool:
        """
        Retry a failed task.
        
        Args:
            task_id: Task ID to retry
            delay: Delay before retry in seconds
            
        Returns:
            True if task was queued for retry
        """
        try:
            # Get task metadata
            metadata = self._get_task_metadata(task_id)
            if not metadata:
                return False
            
            # Check if task can be retried
            if metadata.status not in [TaskStatus.FAILED, TaskStatus.TIMEOUT]:
                return False
            
            if metadata.retry_count >= metadata.max_retries:
                # Move to dead letter queue
                metadata.status = TaskStatus.DEAD_LETTER
                self._update_task_metadata(metadata)
                self._move_to_dead_letter(metadata)
                return False
            
            # Calculate retry delay
            retry_delay = self._calculate_retry_delay(metadata, delay)
            
            # Update retry count
            metadata.retry_count += 1
            metadata.status = TaskStatus.RETRYING
            self._update_task_metadata(metadata)
            
            # Resubmit task with delay
            queue = self.task_queues[metadata.priority]
            current_app.send_task(
                metadata.task_name,
                task_id=f"{task_id}_retry_{metadata.retry_count}",
                queue=queue,
                countdown=retry_delay
            )
            
            logger.info(f"Task queued for retry: {task_id} (attempt {metadata.retry_count})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry task {task_id}: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        try:
            stats = {}
            
            for priority, queue_name in self.task_queues.items():
                # Get queue length
                queue_length = self.redis_client.llen(f"celery:{queue_name}")
                
                # Get active tasks
                active_tasks = self._get_active_tasks_by_queue(queue_name)
                
                # Get failed tasks
                failed_tasks = self._get_failed_tasks_by_queue(queue_name)
                
                stats[priority.name.lower()] = {
                    'queue_length': queue_length,
                    'active_tasks': len(active_tasks),
                    'failed_tasks': len(failed_tasks),
                    'avg_processing_time': self._calculate_avg_processing_time(queue_name)
                }
            
            # Overall statistics
            stats['overall'] = {
                'total_queued': sum(s['queue_length'] for s in stats.values()),
                'total_active': sum(s['active_tasks'] for s in stats.values()),
                'total_failed': sum(s['failed_tasks'] for s in stats.values()),
                'system_health': self._calculate_system_health()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """
        Clean up old completed tasks.
        
        Args:
            days: Number of days to keep task data
            
        Returns:
            Number of tasks cleaned up
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned_count = 0
            
            # Get all task keys
            task_keys = self.redis_client.keys("task_metadata:*")
            
            for key in task_keys:
                task_data = self.redis_client.get(key)
                if task_data:
                    metadata = TaskMetadata(**json.loads(task_data))
                    
                    # Check if task is old and completed
                    if (metadata.created_at < cutoff_date and 
                        metadata.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]):
                        
                        # Remove from Redis
                        self.redis_client.delete(key)
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old tasks")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0
    
    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """
        Get tasks in the dead letter queue.
        
        Returns:
            List of dead letter tasks
        """
        try:
            dead_letter_tasks = []
            dead_letter_keys = self.redis_client.keys("dead_letter:*")
            
            for key in dead_letter_keys:
                task_data = self.redis_client.get(key)
                if task_data:
                    metadata = TaskMetadata(**json.loads(task_data))
                    dead_letter_tasks.append(metadata.to_dict())
            
            return dead_letter_tasks
            
        except Exception as e:
            logger.error(f"Failed to get dead letter queue: {e}")
            return []
    
    def reprocess_dead_letter_task(self, task_id: str) -> bool:
        """
        Reprocess a task from the dead letter queue.
        
        Args:
            task_id: Task ID to reprocess
            
        Returns:
            True if task was reprocessed successfully
        """
        try:
            # Get task from dead letter queue
            dead_letter_key = f"dead_letter:{task_id}"
            task_data = self.redis_client.get(dead_letter_key)
            
            if not task_data:
                return False
            
            metadata = TaskMetadata(**json.loads(task_data))
            
            # Reset retry count and status
            metadata.retry_count = 0
            metadata.status = TaskStatus.PENDING
            metadata.created_at = datetime.now()
            
            # Remove from dead letter queue
            self.redis_client.delete(dead_letter_key)
            
            # Resubmit task
            return self.submit_task(
                task_name=metadata.task_name,
                priority=metadata.priority,
                user_id=metadata.user_id,
                timeout=metadata.timeout,
                max_retries=metadata.max_retries,
                tags=metadata.tags
            ) is not None
            
        except Exception as e:
            logger.error(f"Failed to reprocess dead letter task {task_id}: {e}")
            return False
    
    def _generate_task_id(self, task_name: str, args: tuple, kwargs: dict, user_id: Optional[int]) -> str:
        """Generate a unique task ID."""
        content = f"{task_name}:{args}:{kwargs}:{user_id}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _store_task_metadata(self, metadata: TaskMetadata):
        """Store task metadata in Redis."""
        key = f"task_metadata:{metadata.task_id}"
        self.redis_client.setex(
            key,
            metadata.timeout + 3600,  # Store for timeout + 1 hour
            json.dumps(metadata.to_dict())
        )
    
    def _get_task_metadata(self, task_id: str) -> Optional[TaskMetadata]:
        """Get task metadata from Redis."""
        key = f"task_metadata:{task_id}"
        data = self.redis_client.get(key)
        if data:
            return TaskMetadata(**json.loads(data))
        return None
    
    def _update_task_metadata(self, metadata: TaskMetadata):
        """Update task metadata in Redis."""
        self._store_task_metadata(metadata)
    
    def _map_celery_status(self, celery_status: str) -> TaskStatus:
        """Map Celery status to our TaskStatus enum."""
        status_mapping = {
            'PENDING': TaskStatus.PENDING,
            'STARTED': TaskStatus.RUNNING,
            'SUCCESS': TaskStatus.SUCCESS,
            'FAILURE': TaskStatus.FAILED,
            'RETRY': TaskStatus.RETRYING,
            'REVOKED': TaskStatus.CANCELLED
        }
        return status_mapping.get(celery_status, TaskStatus.PENDING)
    
    def _calculate_retry_delay(self, metadata: TaskMetadata, base_delay: int) -> int:
        """Calculate retry delay using exponential backoff."""
        if metadata.retry_count == 0:
            return base_delay
        
        # Exponential backoff: 2^retry_count * base_delay
        delay = base_delay * (2 ** (metadata.retry_count - 1))
        
        # Cap at 1 hour
        return min(delay, 3600)
    
    def _move_to_dead_letter(self, metadata: TaskMetadata):
        """Move task to dead letter queue."""
        key = f"dead_letter:{metadata.task_id}"
        self.redis_client.setex(
            key,
            86400 * 30,  # Store for 30 days
            json.dumps(metadata.to_dict())
        )
    
    def _track_task_submission(self, metadata: TaskMetadata):
        """Track task submission metrics."""
        if not self.monitoring_enabled:
            return
        
        # Increment submission counter
        self.redis_client.incr(f"metrics:task_submissions:{metadata.task_name}")
        
        # Track by priority
        self.redis_client.incr(f"metrics:priority_submissions:{metadata.priority.name}")
        
        # Track by user
        if metadata.user_id:
            self.redis_client.incr(f"metrics:user_submissions:{metadata.user_id}")
    
    def _track_task_cancellation(self, metadata: TaskMetadata):
        """Track task cancellation metrics."""
        if not self.monitoring_enabled:
            return
        
        self.redis_client.incr(f"metrics:task_cancellations:{metadata.task_name}")
    
    def _get_task_metrics(self, task_id: str) -> Dict[str, Any]:
        """Get task-specific metrics."""
        metadata = self._get_task_metadata(task_id)
        if not metadata:
            return {}
        
        metrics = {
            'processing_time': None,
            'memory_usage': metadata.resource_usage.get('memory', 0),
            'cpu_usage': metadata.resource_usage.get('cpu', 0)
        }
        
        if metadata.started_at and metadata.completed_at:
            metrics['processing_time'] = (metadata.completed_at - metadata.started_at).total_seconds()
        
        return metrics
    
    def _get_active_tasks_by_queue(self, queue_name: str) -> List[str]:
        """Get active tasks for a specific queue."""
        # This is a simplified implementation
        # In production, you'd query Celery's active tasks
        return []
    
    def _get_failed_tasks_by_queue(self, queue_name: str) -> List[str]:
        """Get failed tasks for a specific queue."""
        # This is a simplified implementation
        # In production, you'd query Celery's failed tasks
        return []
    
    def _calculate_avg_processing_time(self, queue_name: str) -> float:
        """Calculate average processing time for a queue."""
        # This is a simplified implementation
        # In production, you'd calculate from actual task data
        return 0.0
    
    def _calculate_system_health(self) -> str:
        """Calculate overall system health."""
        try:
            # Get queue stats
            stats = self.get_queue_stats()
            
            # Check failure rate
            total_tasks = stats['overall']['total_queued'] + stats['overall']['total_active']
            if total_tasks > 0:
                failure_rate = stats['overall']['total_failed'] / total_tasks
                if failure_rate > self.alert_thresholds['failure_rate']:
                    return 'degraded'
            
            # Check queue size
            if stats['overall']['total_queued'] > self.alert_thresholds['queue_size']:
                return 'warning'
            
            return 'healthy'
            
        except Exception:
            return 'unknown'
    
    def _exponential_backoff(self, retry_count: int, base_delay: int = 60) -> int:
        """
        Calculate exponential backoff delay for retries.
        
        Args:
            retry_count: Current retry attempt number
            base_delay: Base delay in seconds
            
        Returns:
            Delay in seconds before next retry
        """
        return min(base_delay * (2 ** retry_count), 3600)  # Max 1 hour
    
    def _linear_backoff(self, retry_count: int, base_delay: int = 60) -> int:
        """
        Calculate linear backoff delay for retries.
        
        Args:
            retry_count: Current retry attempt number
            base_delay: Base delay in seconds
            
        Returns:
            Delay in seconds before next retry
        """
        return min(base_delay * retry_count, 1800)  # Max 30 minutes
    
    def _fixed_backoff(self, retry_count: int, base_delay: int = 60) -> int:
        """
        Calculate fixed backoff delay for retries.
        
        Args:
            retry_count: Current retry attempt number (unused)
            base_delay: Fixed delay in seconds
            
        Returns:
            Delay in seconds before next retry
        """
        return base_delay


# Global instance
background_processor = EnhancedBackgroundProcessor() 