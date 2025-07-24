"""
Focused Task Queue Service

A simplified, focused task queue service that provides essential task management
functionality without the complexity of the full background processor.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from celery import current_app
from celery.result import AsyncResult
from celery.exceptions import MaxRetriesExceededError

from core.exceptions import TaskProcessingError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BULK = 4


class TaskStatus(Enum):
    """Task status tracking."""
    PENDING = 'pending'
    QUEUED = 'queued'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRYING = 'retrying'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'


@dataclass
class TaskInfo:
    """Task information for tracking."""
    task_id: str
    task_name: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300
    user_id: Optional[int] = None
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    tags: List[str] = None
    
    def __post_init__(self):
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


class TaskQueue:
    """
    Focused task queue service for essential task management.
    """
    
    def __init__(self):
        self.task_queues = {
            TaskPriority.CRITICAL: 'critical',
            TaskPriority.HIGH: 'high',
            TaskPriority.NORMAL: 'normal',
            TaskPriority.LOW: 'low',
            TaskPriority.BULK: 'bulk'
        }
        self.cache_prefix = 'task_queue:'
        self.cache_timeout = 3600  # 1 hour
    
    def submit_task(self, task_name: str, args: Tuple = None, kwargs: Dict = None,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   user_id: Optional[int] = None,
                   timeout: int = 300,
                   max_retries: int = 3,
                   tags: List[str] = None) -> str:
        """
        Submit a task to the queue.
        
        Args:
            task_name: Name of the task to execute
            args: Task arguments
            kwargs: Task keyword arguments
            priority: Task priority level
            user_id: User ID associated with the task
            timeout: Task timeout in seconds
            max_retries: Maximum number of retries
            tags: Tags for task categorization
            
        Returns:
            Task ID
            
        Raises:
            TaskProcessingError: If task submission fails
        """
        try:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Create task info
            task_info = TaskInfo(
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
            
            # Store task info
            self._store_task_info(task_info)
            
            # Submit to Celery
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
            task_info.status = TaskStatus.QUEUED
            self._update_task_info(task_info)
            
            logger.info(f"Task submitted: {task_id} ({task_name}) with priority {priority.name}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to submit task {task_name}: {e}")
            raise TaskProcessingError(f"Failed to submit task: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status and information.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Task status dictionary
            
        Raises:
            ResourceNotFoundError: If task not found
        """
        # Get task info from cache
        task_info = self._get_task_info(task_id)
        if not task_info:
            raise ResourceNotFoundError("Task", task_id)
        
        # Get Celery result
        celery_result = AsyncResult(task_id)
        
        # Update status based on Celery result
        task_info.status = self._map_celery_status(celery_result.status)
        
        # Update timestamps
        if celery_result.status == 'RUNNING' and not task_info.started_at:
            task_info.started_at = datetime.now()
        elif celery_result.status in ['SUCCESS', 'FAILURE'] and not task_info.completed_at:
            task_info.completed_at = datetime.now()
        
        # Update error message if failed
        if celery_result.status == 'FAILURE':
            task_info.error_message = str(celery_result.info)
        
        # Update result data if successful
        if celery_result.status == 'SUCCESS':
            task_info.result_data = celery_result.result
        
        # Update retry count
        if hasattr(celery_result, 'retries'):
            task_info.retry_count = celery_result.retries
        
        # Store updated info
        self._update_task_info(task_info)
        
        # Return status dictionary
        status_dict = task_info.to_dict()
        status_dict.update({
            'celery_status': celery_result.status,
            'queue_position': self._get_queue_position(task_id, task_info.priority),
            'estimated_completion': self._estimate_completion(task_info)
        })
        
        return status_dict
    
    def cancel_task(self, task_id: str, force: bool = False) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task ID to cancel
            force: Force cancellation even if task is running
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            # Get task info
            task_info = self._get_task_info(task_id)
            if not task_info:
                return False
            
            # Check if task can be cancelled
            if task_info.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            # Revoke task in Celery
            celery_result = AsyncResult(task_id)
            celery_result.revoke(terminate=force)
            
            # Update task status
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = datetime.now()
            self._update_task_info(task_info)
            
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
            True if retry initiated successfully, False otherwise
        """
        try:
            # Get task info
            task_info = self._get_task_info(task_id)
            if not task_info:
                return False
            
            # Check if task can be retried
            if task_info.status != TaskStatus.FAILED:
                return False
            
            # Check retry limit
            if task_info.retry_count >= task_info.max_retries:
                return False
            
            # Retry task
            celery_result = AsyncResult(task_id)
            celery_result.retry(countdown=delay)
            
            # Update task status
            task_info.status = TaskStatus.RETRYING
            task_info.retry_count += 1
            self._update_task_info(task_info)
            
            logger.info(f"Task retry initiated: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry task {task_id}: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Queue statistics dictionary
        """
        stats = {}
        
        for priority, queue_name in self.task_queues.items():
            # Get active tasks
            active_tasks = self._get_active_tasks_by_queue(queue_name)
            
            # Get failed tasks
            failed_tasks = self._get_failed_tasks_by_queue(queue_name)
            
            stats[priority.name.lower()] = {
                'active_tasks': len(active_tasks),
                'failed_tasks': len(failed_tasks),
                'avg_processing_time': self._calculate_avg_processing_time(queue_name)
            }
        
        return stats
    
    def _store_task_info(self, task_info: TaskInfo):
        """Store task info in cache."""
        cache_key = f"{self.cache_prefix}{task_info.task_id}"
        cache.set(cache_key, task_info.to_dict(), self.cache_timeout)
    
    def _get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Get task info from cache."""
        cache_key = f"{self.cache_prefix}{task_id}"
        data = cache.get(cache_key)
        
        if data:
            # Convert back to TaskInfo object
            data['priority'] = TaskPriority(data['priority'])
            data['status'] = TaskStatus(data['status'])
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            
            if data.get('started_at'):
                data['started_at'] = datetime.fromisoformat(data['started_at'])
            if data.get('completed_at'):
                data['completed_at'] = datetime.fromisoformat(data['completed_at'])
            
            return TaskInfo(**data)
        
        return None
    
    def _update_task_info(self, task_info: TaskInfo):
        """Update task info in cache."""
        self._store_task_info(task_info)
    
    def _map_celery_status(self, celery_status: str) -> TaskStatus:
        """Map Celery status to our TaskStatus enum."""
        status_mapping = {
            'PENDING': TaskStatus.PENDING,
            'STARTED': TaskStatus.RUNNING,
            'SUCCESS': TaskStatus.SUCCESS,
            'FAILURE': TaskStatus.FAILED,
            'RETRY': TaskStatus.RETRYING,
            'REVOKED': TaskStatus.CANCELLED,
        }
        return status_mapping.get(celery_status, TaskStatus.PENDING)
    
    def _get_queue_position(self, task_id: str, priority: TaskPriority) -> Optional[int]:
        """Get task position in queue (simplified implementation)."""
        # This is a simplified implementation
        # In a real system, you'd query the actual queue
        return None
    
    def _estimate_completion(self, task_info: TaskInfo) -> Optional[str]:
        """Estimate task completion time (simplified implementation)."""
        if task_info.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return None
        
        # Simple estimation based on task type and priority
        base_time = 60  # 1 minute base
        priority_multiplier = {
            TaskPriority.CRITICAL: 0.5,
            TaskPriority.HIGH: 0.8,
            TaskPriority.NORMAL: 1.0,
            TaskPriority.LOW: 1.5,
            TaskPriority.BULK: 2.0
        }
        
        estimated_seconds = base_time * priority_multiplier.get(task_info.priority, 1.0)
        estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
        
        return estimated_completion.isoformat()
    
    def _get_active_tasks_by_queue(self, queue_name: str) -> List[str]:
        """Get active tasks in a queue (simplified implementation)."""
        # This is a simplified implementation
        # In a real system, you'd query the actual queue
        return []
    
    def _get_failed_tasks_by_queue(self, queue_name: str) -> List[str]:
        """Get failed tasks in a queue (simplified implementation)."""
        # This is a simplified implementation
        # In a real system, you'd query the actual queue
        return []
    
    def _calculate_avg_processing_time(self, queue_name: str) -> float:
        """Calculate average processing time for a queue (simplified implementation)."""
        # This is a simplified implementation
        # In a real system, you'd calculate from actual task data
        return 120.0  # 2 minutes default 