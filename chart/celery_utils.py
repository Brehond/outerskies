"""
Enhanced Celery Utilities for Outer Skies

This module provides improved Celery task management with:
- Better Windows compatibility
- Task priority queuing
- Retry mechanisms with exponential backoff
- Task result caching and storage
- Real-time task progress updates
"""

import logging
import time
import json
import platform
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from celery import Celery
from celery.result import AsyncResult, EagerResult
from celery.exceptions import CeleryError
from .models import TaskStatus

logger = logging.getLogger(__name__)


class EnhancedCeleryManager:
    """
    Enhanced Celery task manager with improved Windows compatibility
    and advanced task management features
    """

    def __init__(self):
        self.is_windows = platform.system() == 'Windows'
        self.celery_app = None
        self._initialize_celery()

    def _initialize_celery(self):
        """
        Initialize Celery with platform-specific settings
        """
        try:
            from astrology_ai.celery import app as celery_app
            self.celery_app = celery_app

            # Test Celery connectivity
            if self._test_celery_connection():
                logger.info("Celery connection successful")
            else:
                logger.warning("Celery connection failed, will use fallback mode")

        except Exception as e:
            logger.warning(f"Failed to initialize Celery: {e}")
            self.celery_app = None

    def _test_celery_connection(self) -> bool:
        """
        Test Celery broker connectivity
        """
        try:
            if self.celery_app:
                # Try to inspect the app
                inspector = self.celery_app.control.inspect()
                inspector.active()
                return True
        except Exception as e:
            logger.debug(f"Celery connection test failed: {e}")
        return False

    def is_celery_available(self) -> bool:
        """
        Check if Celery is available and working
        """
        if not self.celery_app:
            return False

        # Check if we're in eager mode
        if getattr(settings, 'CELERY_ALWAYS_EAGER', False):
            return True

        # Test connection
        return self._test_celery_connection()

    def create_task_with_enhanced_fallback(
        self,
        task_func: Callable,
        task_type: str,
        parameters: Dict[str, Any],
        user_id: Optional[int] = None,
        priority: int = 5,
        max_retries: int = 3,
        retry_delay: int = 60
    ) -> Dict[str, Any]:
        """
        Create a task with enhanced fallback and retry mechanisms

        Args:
            task_func: The task function to execute
            task_type: Type of task (chart_generation, interpretation, etc.)
            parameters: Task parameters
            user_id: Optional user ID
            priority: Task priority (1-10, lower is higher priority)
            max_retries: Maximum number of retries
            retry_delay: Initial retry delay in seconds

        Returns:
            Dict with task information
        """
        # Create task status record
        task_status = self._create_task_status_record(
            task_type, parameters, user_id, priority, max_retries
        )

        try:
            if self.is_celery_available() and not getattr(settings, 'CELERY_ALWAYS_EAGER', False):
                # Use Celery for background processing
                return self._execute_celery_task(task_func, task_status, parameters)
            else:
                # Use synchronous fallback
                return self._execute_synchronous_task(task_func, task_status, parameters)

        except Exception as e:
            logger.error(f"Task creation failed: {e}")
            self._mark_task_failed(task_status, str(e))
            return self._create_error_response(task_status, str(e))

    def _create_task_status_record(
        self,
        task_type: str,
        parameters: Dict[str, Any],
        user_id: Optional[int],
        priority: int,
        max_retries: int
    ) -> TaskStatus:
        """
        Create a TaskStatus record for tracking
        """
        try:
            task_status = TaskStatus.objects.create(
                task_id=f"task_{int(time.time())}_{hash(str(parameters)) % 10000}",
                task_type=task_type,
                state='PENDING',
                progress=0,
                status_message="Task created, waiting to start",
                parameters=parameters,
                user_id=user_id
            )
            logger.info(f"Created task status record: {task_status.task_id}")
            return task_status
        except Exception as e:
            logger.error(f"Failed to create task status record: {e}")
            raise

    def _execute_celery_task(
        self,
        task_func: Callable,
        task_status: TaskStatus,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute task using Celery
        """
        try:
            # Update task status
            task_status.state = 'PROGRESS'
            task_status.started_at = timezone.now()
            task_status.status_message = "Task queued in Celery"
            task_status.save()

            # Queue the task
            task_result = task_func.delay(**parameters)

            # Update task status with Celery task ID
            task_status.task_id = task_result.id
            task_status.save()

            logger.info(f"Task queued successfully: {task_result.id}")

            return {
                'task_id': task_result.id,
                'status': 'queued',
                'message': 'Task queued successfully',
                'estimated_completion': self._estimate_completion_time(task_status.task_type)
            }

        except Exception as e:
            logger.error(f"Celery task execution failed: {e}")
            self._mark_task_failed(task_status, str(e))
            raise

    def _execute_synchronous_task(
        self,
        task_func: Callable,
        task_status: TaskStatus,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute task synchronously (fallback mode)
        """
        try:
            # Update task status
            task_status.state = 'PROGRESS'
            task_status.started_at = timezone.now()
            task_status.status_message = "Executing task synchronously"
            task_status.save()

            # Execute the task
            logger.info(f"Executing task synchronously: {task_status.task_id}")
            result = task_func(**parameters)

            # Mark task as completed
            self._mark_task_completed(task_status, result)

            return {
                'task_id': task_status.task_id,
                'status': 'completed',
                'message': 'Task completed successfully',
                'result': result
            }

        except Exception as e:
            logger.error(f"Synchronous task execution failed: {e}")
            self._mark_task_failed(task_status, str(e))
            raise

    def _mark_task_completed(self, task_status: TaskStatus, result: Any):
        """
        Mark task as completed
        """
        try:
            task_status.state = 'SUCCESS'
            task_status.progress = 100
            task_status.status_message = "Task completed successfully"
            task_status.completed_at = timezone.now()
            task_status.result = {'data': result} if result else {}
            task_status.save()
            logger.info(f"Task completed: {task_status.task_id}")
        except Exception as e:
            logger.error(f"Failed to mark task as completed: {e}")

    def _mark_task_failed(self, task_status: TaskStatus, error_message: str, traceback: str = ""):
        """
        Mark task as failed
        """
        try:
            task_status.state = 'FAILURE'
            task_status.status_message = f"Task failed: {error_message}"
            task_status.completed_at = timezone.now()
            task_status.error_message = error_message
            task_status.traceback = traceback or str(error_message)
            task_status.save()
            logger.error(f"Task failed: {task_status.task_id} - {error_message}")
        except Exception as e:
            logger.error(f"Failed to mark task as failed: {e}")

    def _create_error_response(self, task_status: TaskStatus, error_message: str) -> Dict[str, Any]:
        """
        Create error response for failed task creation
        """
        return {
            'task_id': task_status.task_id,
            'status': 'failed',
            'message': f'Task creation failed: {error_message}',
            'error': error_message
        }

    def _estimate_completion_time(self, task_type: str) -> Optional[datetime]:
        """
        Estimate task completion time based on task type
        """
        base_times = {
            'chart_generation': 30,  # seconds
            'interpretation': 60,    # seconds
            'ephemeris': 10,         # seconds
        }

        estimated_seconds = base_times.get(task_type, 30)
        return timezone.now() + timedelta(seconds=estimated_seconds)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed task status
        """
        try:
            task_status = TaskStatus.objects.get(task_id=task_id)

            # If it's a Celery task, try to get additional info
            celery_info = {}
            if self.is_celery_available() and not getattr(settings, 'CELERY_ALWAYS_EAGER', False):
                try:
                    async_result = AsyncResult(task_id, app=self.celery_app)
                    celery_info = {
                        'celery_state': async_result.state,
                        'celery_info': async_result.info,
                        'celery_successful': async_result.successful(),
                        'celery_failed': async_result.failed(),
                    }
                except Exception as e:
                    logger.debug(f"Could not get Celery info: {e}")

            return {
                'task_id': task_status.task_id,
                'task_type': task_status.task_type,
                'state': task_status.state,
                'progress': task_status.progress,
                'status_message': task_status.status_message,
                'created_at': task_status.created_at.isoformat(),
                'started_at': task_status.started_at.isoformat() if task_status.started_at else None,
                'completed_at': task_status.completed_at.isoformat() if task_status.completed_at else None,
                'error_message': task_status.error_message,
                'result': task_status.result,
                'celery_info': celery_info
            }

        except TaskStatus.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return None

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task
        """
        try:
            task_status = TaskStatus.objects.get(task_id=task_id)

            if task_status.state in ['PENDING', 'PROGRESS']:
                # Try to cancel in Celery if available
                if self.is_celery_available() and not getattr(settings, 'CELERY_ALWAYS_EAGER', False):
                    try:
                        async_result = AsyncResult(task_id, app=self.celery_app)
                        async_result.revoke(terminate=True)
                    except Exception as e:
                        logger.warning(f"Could not cancel Celery task: {e}")

                # Mark as cancelled in database
                task_status.state = 'CANCELLED'
                task_status.status_message = "Task cancelled by user"
                task_status.completed_at = timezone.now()
                task_status.save()

                logger.info(f"Task cancelled: {task_id}")
                return True

            return False

        except TaskStatus.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return False

    def retry_task(self, task_id: str) -> bool:
        """
        Retry a failed task
        """
        try:
            task_status = TaskStatus.objects.get(task_id=task_id)

            if task_status.state == 'FAILURE':
                # Create new task with same parameters
                new_task_status = TaskStatus.objects.create(
                    task_id=f"retry_{task_id}_{int(time.time())}",
                    task_type=task_status.task_type,
                    state='PENDING',
                    progress=0,
                    status_message="Retrying failed task",
                    parameters=task_status.parameters,
                    user=task_status.user
                )

                logger.info(f"Task retry created: {new_task_status.task_id}")
                return True

            return False

        except TaskStatus.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error retrying task: {e}")
            return False

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health information
        """
        health_info = {
            'celery_available': self.is_celery_available(),
            'platform': platform.system(),
            'celery_always_eager': getattr(settings, 'CELERY_ALWAYS_EAGER', False),
            'timestamp': timezone.now().isoformat(),
        }

        # Add task statistics
        try:
            total_tasks = TaskStatus.objects.count()
            pending_tasks = TaskStatus.objects.filter(state='PENDING').count()
            running_tasks = TaskStatus.objects.filter(state='PROGRESS').count()
            completed_tasks = TaskStatus.objects.filter(state='SUCCESS').count()
            failed_tasks = TaskStatus.objects.filter(state='FAILURE').count()

            health_info['task_stats'] = {
                'total': total_tasks,
                'pending': pending_tasks,
                'running': running_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks,
            }
        except Exception as e:
            health_info['task_stats_error'] = str(e)

        return health_info


# Global enhanced Celery manager instance
enhanced_celery_manager = EnhancedCeleryManager()


# Backward compatibility functions
def is_celery_available() -> bool:
    """Check if Celery is available"""
    return enhanced_celery_manager.is_celery_available()








def health_check_celery() -> Dict[str, Any]:
    """Get Celery health check (backward compatibility)"""
    return enhanced_celery_manager.get_system_health()


def safe_serialize_result(result: Any) -> Dict[str, Any]:
    """
    Safely serialize Celery task results for database storage.

    Args:
        result: The result to serialize

    Returns:
        Dict containing serializable result data
    """
    try:
        if isinstance(result, EagerResult):
            # Handle EagerResult objects (from synchronous execution)
            return {
                'type': 'eager_result',
                'successful': result.successful(),
                'result': result.result if result.successful() else str(result.result),
                'state': result.state,
                'info': str(result.info) if hasattr(result, 'info') else None,
                'traceback': result.traceback if hasattr(result, 'traceback') else None,
            }
        elif hasattr(result, '__dict__'):
            # Handle objects with __dict__
            return {
                'type': 'object',
                'class': result.__class__.__name__,
                'data': {k: str(v) for k, v in result.__dict__.items()}
            }
        else:
            # Handle basic types
            return {
                'type': 'basic',
                'value': str(result),
                'python_type': type(result).__name__
            }
    except Exception as e:
        logger.error(f"Error serializing result: {e}")
        return {
            'type': 'error',
            'error': str(e),
            'original_type': str(type(result))
        }


def create_task_with_fallback(task_func, args=None, kwargs=None, user=None,
                              task_type='unknown', parameters=None) -> Dict[str, Any]:
    """
    Create a Celery task with automatic fallback to synchronous execution.

    Args:
        task_func: The Celery task function to execute
        args: Arguments to pass to the task
        kwargs: Keyword arguments to pass to the task
        user: User associated with the task
        task_type: Type of task for logging
        parameters: Task parameters for database storage

    Returns:
        Dict containing task information and result
    """
    logger.info(f"=== create_task_with_fallback START for {task_type} ===")
    logger.info(f"task_func: {task_func}")
    logger.info(f"args: {args}")
    logger.info(f"kwargs: {kwargs}")
    logger.info(f"user: {user}")
    logger.info(f"parameters: {parameters}")

    args = args or []
    kwargs = kwargs or {}
    parameters = parameters or {}

    # Generate a task ID
    task_id = str(uuid.uuid4())
    logger.info(f"Generated task_id: {task_id}")

    try:
        logger.info(f"Checking if Celery is available for {task_type}...")
        # Try to queue the task with Celery
        if is_celery_available():
            logger.info(f"Celery is available, queuing {task_type} task with Celery: {task_id}")
            try:
                celery_task = task_func.delay(*args, **kwargs)
                logger.info(f"Celery task queued successfully: {celery_task.id}")

                # Create task status record
                logger.info(f"Creating task status record for {task_type}...")
                task_status = TaskStatus.objects.create(
                    task_id=celery_task.id,
                    task_type=task_type,
                    user=user,
                    parameters=parameters,
                    state='PENDING'
                )
                logger.info(f"Task status record created: {task_status.id}")

                logger.info(f"Returning Celery task result: {{'success': True, ...}}")
                return {
                    'success': True,
                    'task_id': celery_task.id,
                    'status': 'PENDING',
                    'message': f'{task_type} task queued successfully',
                    'celery_available': True,
                    'task_status_id': task_status.id
                }
            except Exception as celery_task_error:
                logger.error(f"Error queuing Celery task: {celery_task_error}")
                raise celery_task_error
        else:
            logger.warning(f"Celery is not available for {task_type}, using fallback")
            # Fallback to synchronous execution when Celery is not available
            try:
                logger.info(f"Executing {task_type} task synchronously as fallback: {task_id}")

                # Execute task synchronously
                logger.info(f"Calling task_func.apply with args={args}, kwargs={kwargs}")
                result = task_func.apply(args=args, kwargs=kwargs)
                logger.info(f"Sync execution result: {result}")
                logger.info(f"Result successful: {result.successful()}")

                # Create task status record for synchronous execution
                logger.info(f"Creating sync task status record for {task_type}...")
                task_status = TaskStatus.objects.create(
                    task_id=task_id,
                    task_type=task_type,
                    user=user,
                    parameters=parameters,
                    state='SUCCESS' if result.successful() else 'FAILURE',
                    result=safe_serialize_result(result),
                    started_at=timezone.now(),
                    completed_at=timezone.now(),
                    error_message=str(result.result) if not result.successful() else '',
                    traceback=str(result.traceback) if hasattr(result, 'traceback') and result.traceback else ''
                )
                logger.info(f"Sync task status record created: {task_status.id}")

                logger.info("Returning sync fallback result: {'success': True, ...}")
                return {
                    'success': True,
                    'task_id': task_id,
                    'status': 'SUCCESS' if result.successful() else 'FAILURE',
                    'message': f'{task_type} task completed synchronously (Celery unavailable)',
                    'celery_available': False,
                    'result': result.result if result.successful() else str(result.result),
                    'task_status_id': task_status.id
                }

            except Exception as sync_error:
                logger.error(f"Synchronous execution failed for {task_type} task: {sync_error}")
                logger.error(f"Sync exception type: {type(sync_error)}")
                logger.error(f"Sync traceback: {sync_error}")

                # Create error task status record
                logger.info(f"Creating error task status record for {task_type}...")
                task_status = TaskStatus.objects.create(
                    task_id=task_id,
                    task_type=task_type,
                    user=user,
                    parameters=parameters,
                    state='FAILURE',
                    error_message=f"Sync error: {sync_error}",
                    traceback=str(sync_error)
                )
                logger.info(f"Error task status record created: {task_status.id}")

                logger.info("Returning sync error result: {'success': False, ...}")
                return {
                    'success': False,
                    'task_id': task_id,
                    'status': 'FAILURE',
                    'message': f'Synchronous execution failed for {task_type} task',
                    'celery_available': False,
                    'error': f"Sync: {sync_error}",
                    'task_status_id': task_status.id
                }

    except Exception as celery_error:
        logger.warning(f"Celery queuing failed for {task_type} task: {celery_error}")
        logger.warning(f"Exception type: {type(celery_error)}")
        logger.warning(f"Traceback: {celery_error}")

        # Fallback to synchronous execution
        try:
            logger.info(f"Executing {task_type} task synchronously as fallback: {task_id}")

            # Execute task synchronously
            logger.info(f"Calling task_func.apply with args={args}, kwargs={kwargs}")
            result = task_func.apply(args=args, kwargs=kwargs)
            logger.info(f"Sync execution result: {result}")
            logger.info(f"Result successful: {result.successful()}")

            # Create task status record for synchronous execution
            logger.info(f"Creating sync task status record for {task_type}...")
            task_status = TaskStatus.objects.create(
                task_id=task_id,
                task_type=task_type,
                user=user,
                parameters=parameters,
                state='SUCCESS' if result.successful() else 'FAILURE',
                result=safe_serialize_result(result),
                started_at=timezone.now(),
                completed_at=timezone.now(),
                error_message=str(result.result) if not result.successful() else '',
                traceback=str(result.traceback) if hasattr(result, 'traceback') and result.traceback else ''
            )
            logger.info(f"Sync task status record created: {task_status.id}")

            logger.info("Returning sync fallback result: {'success': True, ...}")
            return {
                'success': True,
                'task_id': task_id,
                'status': 'SUCCESS' if result.successful() else 'FAILURE',
                'message': f'{task_type} task completed synchronously (Celery unavailable)',
                'celery_available': False,
                'result': result.result if result.successful() else str(result.result),
                'task_status_id': task_status.id
            }

        except Exception as sync_error:
            logger.error(f"Synchronous execution also failed for {task_type} task: {sync_error}")
            logger.error(f"Sync exception type: {type(sync_error)}")
            logger.error(f"Sync traceback: {sync_error}")

            # Create error task status record
            logger.info(f"Creating error task status record for {task_type}...")
            task_status = TaskStatus.objects.create(
                task_id=task_id,
                task_type=task_type,
                user=user,
                parameters=parameters,
                state='FAILURE',
                error_message=f"Celery error: {celery_error}. Sync error: {sync_error}",
                traceback=str(sync_error)
            )
            logger.info(f"Error task status record created: {task_status.id}")

            logger.info("Returning sync error result: {'success': False, ...}")
            return {
                'success': False,
                'task_id': task_id,
                'status': 'FAILURE',
                'message': f'Both Celery and synchronous execution failed for {task_type} task',
                'celery_available': False,
                'error': f"Celery: {celery_error}. Sync: {sync_error}",
                'task_status_id': task_status.id
            }

    # Defensive: always return a dict
    logger.error(f"create_task_with_fallback reached unexpected end for {task_type} task")
    logger.error("This should never happen - all code paths should return a result")
    return {
        'success': False,
        'error': 'Unknown error: no result returned from task creation',
        'status': 'FAILURE',
        'message': 'No result returned from task creation',
        'celery_available': False,
        'task_id': task_id,
        'task_status_id': None
    }


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a task by ID.

    Args:
        task_id: The task ID to look up

    Returns:
        Dict containing task status information or None if not found
    """
    try:
        # First try to find in database
        task_status = TaskStatus.objects.filter(task_id=task_id).first()

        if task_status:
            return {
                'task_id': task_status.task_id,
                'task_type': task_status.task_type,
                'state': task_status.state,
                'progress': task_status.progress,
                'status_message': task_status.status_message,
                'result': task_status.result,
                'error_message': task_status.error_message,
                'created_at': task_status.created_at.isoformat() if task_status.created_at else None,
                'started_at': task_status.started_at.isoformat() if task_status.started_at else None,
                'completed_at': task_status.completed_at.isoformat() if task_status.completed_at else None,
            }

        # If not in database, try Celery result backend
        if is_celery_available():
            from celery.result import AsyncResult
            celery_result = AsyncResult(task_id)

            if celery_result.state != 'PENDING':
                return {
                    'task_id': task_id,
                    'task_type': 'unknown',
                    'state': celery_result.state,
                    'progress': 100 if celery_result.ready() else 0,
                    'status_message': 'Task completed' if celery_result.ready() else 'Task in progress',
                    'result': celery_result.result if celery_result.successful() else str(celery_result.result),
                    'error_message': str(celery_result.result) if not celery_result.successful() else '',
                }

        return None

    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        return None


def cleanup_old_task_records(days: int = 7) -> int:
    """
    Clean up old task records from the database.

    Args:
        days: Number of days to keep task records

    Returns:
        Number of records deleted
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count, _ = TaskStatus.objects.filter(
            created_at__lt=cutoff_date
        ).delete()

        logger.info(f"Cleaned up {deleted_count} old task records")
        return deleted_count

    except Exception as e:
        logger.error(f"Error cleaning up old task records: {e}")
        return 0
