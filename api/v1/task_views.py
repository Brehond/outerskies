"""
Task Management API Views

Provides endpoints for managing background tasks, checking status, and retrieving results.
"""

import logging
import json
from typing import Dict, Any, Optional
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from chart.tasks import (
    generate_chart_task,
    generate_planet_interpretations_task,
    generate_master_interpretation_task,
    process_plugin_tasks_task,
    get_task_status,
    cancel_task
)
from chart.models import TaskStatus
from api.utils.error_handler import handle_api_error

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_chart_generation(request):
    """
    Start background chart generation task.
    
    Request body:
    {
        "date": "2024-01-01",
        "time": "12:00:00",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone_str": "America/New_York",
        "zodiac_type": "tropical",
        "house_system": "placidus"
    }
    
    Returns:
    {
        "success": true,
        "task_id": "task-uuid",
        "status": "queued",
        "message": "Chart generation started"
    }
    """
    try:
        # Validate required fields
        required_fields = ['date', 'time', 'latitude', 'longitude', 'timezone_str', 'zodiac_type', 'house_system']
        for field in required_fields:
            if field not in request.data:
                return Response({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Start the task
        task = generate_chart_task.delay(
            chart_params=request.data,
            user_id=request.user.id
        )
        
        return Response({
            'success': True,
            'task_id': task.id,
            'status': 'queued',
            'message': 'Chart generation started successfully'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error starting chart generation: {e}")
        return handle_api_error(e, 'Failed to start chart generation')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_interpretation_generation(request):
    """
    Start background interpretation generation task.
    
    Request body:
    {
        "chart_data": {...},
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000,
        "date": "2024-01-01",
        "time": "12:00:00",
        "location": "New York, NY",
        "interpretation_type": "planets" | "master" | "both"
    }
    
    Returns:
    {
        "success": true,
        "task_id": "task-uuid",
        "status": "queued",
        "message": "Interpretation generation started"
    }
    """
    try:
        # Validate required fields
        required_fields = ['chart_data', 'model_name', 'temperature', 'max_tokens', 'date', 'time', 'location']
        for field in required_fields:
            if field not in request.data:
                return Response({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        interpretation_type = request.data.get('interpretation_type', 'both')
        chart_data = request.data['chart_data']
        interpretation_params = {
            'model_name': request.data['model_name'],
            'temperature': request.data['temperature'],
            'max_tokens': request.data['max_tokens'],
            'date': request.data['date'],
            'time': request.data['time'],
            'location': request.data['location']
        }
        
        task_ids = []
        
        # Start planet interpretations task
        if interpretation_type in ['planets', 'both']:
            planet_task = generate_planet_interpretations_task.delay(
                chart_data=chart_data,
                interpretation_params=interpretation_params,
                user_id=request.user.id
            )
            task_ids.append({
                'type': 'planets',
                'task_id': planet_task.id
            })
        
        # Start master interpretation task
        if interpretation_type in ['master', 'both']:
            master_task = generate_master_interpretation_task.delay(
                chart_data=chart_data,
                interpretation_params=interpretation_params,
                user_id=request.user.id
            )
            task_ids.append({
                'type': 'master',
                'task_id': master_task.id
            })
        
        return Response({
            'success': True,
            'tasks': task_ids,
            'status': 'queued',
            'message': f'Interpretation generation started for {interpretation_type}'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error starting interpretation generation: {e}")
        return handle_api_error(e, 'Failed to start interpretation generation')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_plugin_processing(request):
    """
    Start background plugin processing task.
    
    Request body:
    {
        "chart_data": {...},
        "aspects_enabled": true,
        "houses_enabled": true,
        "aspect_orb": 8.0,
        "include_house_planets": true,
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    Returns:
    {
        "success": true,
        "task_id": "task-uuid",
        "status": "queued",
        "message": "Plugin processing started"
    }
    """
    try:
        # Validate required fields
        if 'chart_data' not in request.data:
            return Response({
                'success': False,
                'error': 'Missing required field: chart_data'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Start the task
        task = process_plugin_tasks_task.delay(
            chart_data=request.data['chart_data'],
            plugin_params=request.data,
            user_id=request.user.id
        )
        
        return Response({
            'success': True,
            'task_id': task.id,
            'status': 'queued',
            'message': 'Plugin processing started successfully'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error starting plugin processing: {e}")
        return handle_api_error(e, 'Failed to start plugin processing')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_status_view(request, task_id):
    """
    Get the status of a background task.
    
    Returns:
    {
        "success": true,
        "task": {
            "task_id": "task-uuid",
            "state": "SUCCESS" | "PROGRESS" | "FAILURE" | "CANCELLED",
            "progress": 75,
            "status_message": "Processing...",
            "created_at": "2024-01-01T12:00:00Z",
            "started_at": "2024-01-01T12:00:01Z",
            "completed_at": null,
            "result": {...},
            "error_message": null
        }
    }
    """
    try:
        # Get task status
        task_info = get_task_status(task_id)
        
        if not task_info:
            return Response({
                'success': False,
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user has permission to view this task
        try:
            task_status = TaskStatus.objects.get(task_id=task_id)
            if task_status.user_id and task_status.user_id != request.user.id:
                raise PermissionDenied("You don't have permission to view this task")
        except TaskStatus.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'task': task_info
        }, status=status.HTTP_200_OK)
        
    except PermissionDenied:
        return Response({
            'success': False,
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return handle_api_error(e, 'Failed to get task status')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_task_view(request, task_id):
    """
    Cancel a running background task.
    
    Returns:
    {
        "success": true,
        "message": "Task cancelled successfully"
    }
    """
    try:
        # Check if user has permission to cancel this task
        try:
            task_status = TaskStatus.objects.get(task_id=task_id)
            if task_status.user_id and task_status.user_id != request.user.id:
                raise PermissionDenied("You don't have permission to cancel this task")
        except TaskStatus.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Cancel the task
        success = cancel_task(task_id)
        
        if success:
            return Response({
                'success': True,
                'message': 'Task cancelled successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Failed to cancel task'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except PermissionDenied:
        return Response({
            'success': False,
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        return handle_api_error(e, 'Failed to cancel task')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_tasks(request):
    """
    List all tasks for the current user.
    
    Query parameters:
    - state: Filter by task state (PENDING, PROGRESS, SUCCESS, FAILURE, CANCELLED)
    - task_type: Filter by task type (chart_generation, interpretation, plugin_processing)
    - limit: Maximum number of tasks to return (default: 20)
    - offset: Number of tasks to skip (default: 0)
    
    Returns:
    {
        "success": true,
        "tasks": [
            {
                "task_id": "task-uuid",
                "task_type": "chart_generation",
                "state": "SUCCESS",
                "progress": 100,
                "status_message": "Completed successfully",
                "created_at": "2024-01-01T12:00:00Z",
                "completed_at": "2024-01-01T12:01:00Z"
            }
        ],
        "total": 50,
        "limit": 20,
        "offset": 0
    }
    """
    try:
        # Get query parameters
        state_filter = request.GET.get('state')
        task_type_filter = request.GET.get('task_type')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        # Build query
        queryset = TaskStatus.objects.filter(user_id=request.user.id)
        
        if state_filter:
            queryset = queryset.filter(state=state_filter)
        
        if task_type_filter:
            queryset = queryset.filter(task_type=task_type_filter)
        
        # Get total count
        total = queryset.count()
        
        # Get paginated results
        tasks = queryset.order_by('-created_at')[offset:offset + limit]
        
        # Serialize tasks
        task_list = []
        for task in tasks:
            task_list.append({
                'task_id': task.task_id,
                'task_type': task.task_type,
                'state': task.state,
                'progress': task.progress,
                'status_message': task.status_message,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'has_result': bool(task.result),
                'has_error': bool(task.error_message)
            })
        
        return Response({
            'success': True,
            'tasks': task_list,
            'total': total,
            'limit': limit,
            'offset': offset
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing user tasks: {e}")
        return handle_api_error(e, 'Failed to list tasks')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_result(request, task_id):
    """
    Get the result of a completed task.
    
    Returns:
    {
        "success": true,
        "result": {...},
        "task_info": {
            "task_id": "task-uuid",
            "state": "SUCCESS",
            "completed_at": "2024-01-01T12:01:00Z"
        }
    }
    """
    try:
        # Get task status
        task_info = get_task_status(task_id)
        
        if not task_info:
            return Response({
                'success': False,
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user has permission to view this task
        try:
            task_status = TaskStatus.objects.get(task_id=task_id)
            if task_status.user_id and task_status.user_id != request.user.id:
                raise PermissionDenied("You don't have permission to view this task")
        except TaskStatus.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if task is completed
        if task_info['state'] not in ['SUCCESS', 'FAILURE', 'CANCELLED']:
            return Response({
                'success': False,
                'error': 'Task is not completed yet',
                'task_info': task_info
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Return result
        return Response({
            'success': True,
            'result': task_info.get('result'),
            'error_message': task_info.get('error_message'),
            'task_info': {
                'task_id': task_info['task_id'],
                'state': task_info['state'],
                'completed_at': task_info['completed_at']
            }
        }, status=status.HTTP_200_OK)
        
    except PermissionDenied:
        return Response({
            'success': False,
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        logger.error(f"Error getting task result: {e}")
        return handle_api_error(e, 'Failed to get task result')


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_task(request, task_id):
    """
    Delete a task record (only for completed tasks).
    
    Returns:
    {
        "success": true,
        "message": "Task deleted successfully"
    }
    """
    try:
        # Check if user has permission to delete this task
        try:
            task_status = TaskStatus.objects.get(task_id=task_id)
            if task_status.user_id and task_status.user_id != request.user.id:
                raise PermissionDenied("You don't have permission to delete this task")
        except TaskStatus.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Only allow deletion of completed tasks
        if task_status.state not in ['SUCCESS', 'FAILURE', 'CANCELLED']:
            return Response({
                'success': False,
                'error': 'Can only delete completed tasks'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete the task
        task_status.delete()
        
        return Response({
            'success': True,
            'message': 'Task deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except PermissionDenied:
        return Response({
            'success': False,
            'error': 'Permission denied'
        }, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return handle_api_error(e, 'Failed to delete task') 