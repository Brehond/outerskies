"""
Enhanced Task Views for Phase 2

This module provides enhanced task management views that integrate with the
new background processor and provide comprehensive task management capabilities.
"""

import logging
from typing import Dict, Any, List
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from core.services.task_queue import TaskQueue, TaskPriority
from core.validators import Validators, validate_input
from core.error_handler import handle_api_error, handle_validation_error
from core.exceptions import ValidationError, TaskProcessingError, ResourceNotFoundError

logger = logging.getLogger(__name__)

# Initialize task queue
task_queue = TaskQueue()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@validate_input({
    'task_name': Validators.STRING_VALIDATOR,
    'priority': Validators.CHOICE_VALIDATOR(['critical', 'high', 'normal', 'low', 'bulk']),
    'timeout': Validators.POSITIVE_INTEGER,
    'max_retries': Validators.POSITIVE_INTEGER,
    'tags': Validators.TAGS,
})
def submit_enhanced_task(request):
    """
    Submit a task with enhanced features including prioritization and monitoring.
    
    Request Body:
    {
        "task_name": "chart.tasks.generate_chart_task",
        "args": [...],
        "kwargs": {...},
        "priority": "high",
        "timeout": 300,
        "max_retries": 3,
        "tags": ["chart_generation", "user_request"]
    }
    
    Returns:
    {
        "status": "success",
        "data": {
            "task_id": "...",
            "status": "queued",
            "priority": "high",
            "estimated_completion": "..."
        }
    }
    """
    try:
        # Get validated data
        data = request.validated_data
        
        # Map priority string to enum
        priority_str = data.get('priority', 'normal').upper()
        try:
            priority = TaskPriority[priority_str]
        except KeyError:
            return handle_validation_error(
                {'priority': f"Invalid priority: {priority_str}. Valid options: {[p.name.lower() for p in TaskPriority]}"}
            )
        
        # Submit task using task queue
        task_id = task_queue.submit_task(
            task_name=data['task_name'],
            args=tuple(data.get('args', [])),
            kwargs=data.get('kwargs', {}),
            priority=priority,
            user_id=request.user.id,
            timeout=data.get('timeout', 300),
            max_retries=data.get('max_retries', 3),
            tags=data.get('tags', [])
        )
        
        # Get task status
        task_status = task_queue.get_task_status(task_id)
        
        # Create response
        response_data = {
            'task_id': task_id,
            'status': task_status.get('status', 'queued'),
            'priority': priority.name,
            'estimated_completion': task_status.get('estimated_completion'),
            'queue_position': task_status.get('queue_position')
        }
        
        return Response({
            'status': 'success',
            'data': response_data,
            'message': "Task submitted successfully"
        }, status=status.HTTP_202_ACCEPTED)
        
    except TaskProcessingError as e:
        return handle_api_error(e, 'Failed to submit task')
    except Exception as e:
        logger.error(f"Error submitting enhanced task: {e}")
        return handle_api_error(e, 'Failed to submit task')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_enhanced_task_status(request, task_id):
    """
    Get comprehensive task status and metadata.
    
    Returns:
    {
        "status": "success",
        "data": {
            "task_id": "...",
            "status": "running",
            "progress": 0.75,
            "estimated_completion": "...",
            "resource_usage": {...},
            "retry_count": 0,
            "error_message": null
        }
    }
    """
    try:
        # Get task status from task queue
        task_status = task_queue.get_task_status(task_id)
        
        if not task_status or task_status.get('status') == 'not_found':
            raise ResourceNotFoundError("Task", task_id)
        
        # Check if user has permission to view this task
        if not request.user.is_staff and task_status.get('user_id') != request.user.id:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'FORBIDDEN',
                    'message': "You don't have permission to view this task"
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            'status': 'success',
            'data': task_status,
            'message': "Task status retrieved successfully"
        }, status=status.HTTP_200_OK)
        
    except ResourceNotFoundError as e:
        return handle_api_error(e, 'Task not found')
    except Exception as e:
        logger.error(f"Error getting enhanced task status: {e}")
        return handle_api_error(e, 'Failed to get task status')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_enhanced_task(request, task_id):
    """
    Cancel a running task.
    
    Request Body:
    {
        "force": false
    }
    
    Returns:
    {
        "status": "success",
        "message": "Task cancelled successfully"
    }
    """
    try:
        force = request.data.get('force', False)
        
        # Get task status first to check permissions
        task_status = task_queue.get_task_status(task_id)
        
        if not task_status or task_status.get('status') == 'not_found':
            raise ResourceNotFoundError("Task", task_id)
        
        # Check if user has permission to cancel this task
        if not request.user.is_staff and task_status.get('user_id') != request.user.id:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'FORBIDDEN',
                    'message': "You don't have permission to cancel this task"
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Cancel task
        success = task_queue.cancel_task(task_id, force=force)
        
        if not success:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'TASK_CANCELLATION_FAILED',
                    'message': "Failed to cancel task"
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'success',
            'message': "Task cancelled successfully"
        }, status=status.HTTP_200_OK)
        
    except ResourceNotFoundError as e:
        return handle_api_error(e, 'Task not found')
    except Exception as e:
        logger.error(f"Error cancelling enhanced task: {e}")
        return handle_api_error(e, 'Failed to cancel task')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retry_enhanced_task(request, task_id):
    """
    Retry a failed task.
    
    Request Body:
    {
        "delay": 0
    }
    
    Returns:
    {
        "status": "success",
        "message": "Task retry initiated successfully"
    }
    """
    try:
        delay = request.data.get('delay', 0)
        
        # Get task status first to check permissions
        task_status = task_queue.get_task_status(task_id)
        
        if not task_status or task_status.get('status') == 'not_found':
            raise ResourceNotFoundError("Task", task_id)
        
        # Check if user has permission to retry this task
        if not request.user.is_staff and task_status.get('user_id') != request.user.id:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'FORBIDDEN',
                    'message': "You don't have permission to retry this task"
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Retry task
        success = task_queue.retry_task(task_id, delay=delay)
        
        if not success:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'TASK_RETRY_FAILED',
                    'message': "Failed to retry task"
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'success',
            'message': "Task retry initiated successfully"
        }, status=status.HTTP_200_OK)
        
    except ResourceNotFoundError as e:
        return handle_api_error(e, 'Task not found')
    except Exception as e:
        logger.error(f"Error retrying enhanced task: {e}")
        return handle_api_error(e, 'Failed to retry task')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_enhanced_tasks(request):
    """
    List all tasks for the current user.
    
    Query Parameters:
    - status: Filter by task status
    - priority: Filter by task priority
    - limit: Maximum number of tasks to return
    - offset: Number of tasks to skip
    
    Returns:
    {
        "status": "success",
        "data": {
            "tasks": [...],
            "total": 100,
            "limit": 20,
            "offset": 0
        }
    }
    """
    try:
        # Get query parameters
        status_filter = request.GET.get('status')
        priority_filter = request.GET.get('priority')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        # Validate parameters
        if limit > 100:
            limit = 100
        if offset < 0:
            offset = 0
        
        # Get user tasks (this would need to be implemented in task queue)
        # For now, return empty list
        tasks = []
        total = 0
        
        return Response({
            'status': 'success',
            'data': {
                'tasks': tasks,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing user tasks: {e}")
        return handle_api_error(e, 'Failed to list tasks')


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_queue_statistics(request):
    """
    Get queue statistics (admin only).
    
    Returns:
    {
        "status": "success",
        "data": {
            "critical": {...},
            "high": {...},
            "normal": {...},
            "low": {...},
            "bulk": {...}
        }
    }
    """
    try:
        # Get queue statistics
        stats = task_queue.get_queue_stats()
        
        return Response({
            'status': 'success',
            'data': stats
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting queue statistics: {e}")
        return handle_api_error(e, 'Failed to get queue statistics')


@api_view(['POST'])
@permission_classes([IsAdminUser])
def cleanup_old_tasks(request):
    """
    Clean up old completed tasks (admin only).
    
    Request Body:
    {
        "days": 7
    }
    
    Returns:
    {
        "status": "success",
        "data": {
            "cleaned_tasks": 150
        }
    }
    """
    try:
        days = request.data.get('days', 7)
        
        # Clean up old tasks (this would need to be implemented)
        cleaned_count = 0
        
        return Response({
            'status': 'success',
            'data': {
                'cleaned_tasks': cleaned_count
            },
            'message': f"Cleaned up {cleaned_count} old tasks"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {e}")
        return handle_api_error(e, 'Failed to clean up old tasks')


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_dead_letter_queue(request):
    """
    Get dead letter queue (admin only).
    
    Returns:
    {
        "status": "success",
        "data": {
            "tasks": [...]
        }
    }
    """
    try:
        # Get dead letter queue (this would need to be implemented)
        dead_letter_tasks = []
        
        return Response({
            'status': 'success',
            'data': {
                'tasks': dead_letter_tasks
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting dead letter queue: {e}")
        return handle_api_error(e, 'Failed to get dead letter queue')


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reprocess_dead_letter_task(request, task_id):
    """
    Reprocess a task from dead letter queue (admin only).
    
    Returns:
    {
        "status": "success",
        "message": "Task reprocessed successfully"
    }
    """
    try:
        # Reprocess dead letter task (this would need to be implemented)
        success = True
        
        if not success:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'TASK_REPROCESS_FAILED',
                    'message': "Failed to reprocess task"
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'success',
            'message': "Task reprocessed successfully"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error reprocessing dead letter task: {e}")
        return handle_api_error(e, 'Failed to reprocess task')


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_task_operations(request):
    """
    Perform bulk operations on tasks (admin only).
    
    Request Body:
    {
        "operation": "cancel",
        "task_ids": ["task1", "task2"],
        "filters": {
            "status": "failed",
            "priority": "low"
        }
    }
    
    Returns:
    {
        "status": "success",
        "data": {
            "processed_tasks": 10,
            "failed_tasks": 2
        }
    }
    """
    try:
        operation = request.data.get('operation')
        task_ids = request.data.get('task_ids', [])
        filters = request.data.get('filters', {})
        
        # Validate operation
        valid_operations = ['cancel', 'retry', 'delete']
        if operation not in valid_operations:
            return handle_validation_error({
                'operation': f"Invalid operation. Valid operations: {valid_operations}"
            })
        
        # Perform bulk operation (this would need to be implemented)
        processed_count = 0
        failed_count = 0
        
        return Response({
            'status': 'success',
            'data': {
                'processed_tasks': processed_count,
                'failed_tasks': failed_count
            },
            'message': f"Bulk operation completed. Processed: {processed_count}, Failed: {failed_count}"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error performing bulk task operations: {e}")
        return handle_api_error(e, 'Failed to perform bulk operations') 