"""
Celery Tasks for Background Processing

This module provides Celery tasks for handling expensive operations asynchronously:
- Chart generation and calculations
- AI interpretation generation
- Plugin processing
- Result caching and storage
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .services.chart_orchestrator import ChartOrchestrator
from .services.caching import ephemeris_cache, ai_cache
from .models import Chart, TaskStatus
from ai_integration.openrouter_api import generate_interpretation
from .prompts import prompt_manager

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_chart_task(self, chart_params: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Background task for chart generation and calculations.
    
    Args:
        chart_params: Chart generation parameters
        user_id: Optional user ID for tracking
        
    Returns:
        Chart data and metadata
    """
    task_id = self.request.id
    
    try:
        # Update task status
        TaskStatus.objects.update_or_create(
            task_id=task_id,
            defaults={
                'task_type': 'chart_generation',
                'state': 'PROGRESS',
                'progress': 10,
                'status_message': 'Starting chart calculation...',
                'parameters': chart_params,
                'user_id': user_id,
                'started_at': timezone.now()
            }
        )
        
        # Extract parameters
        date = chart_params['date']
        time_str = chart_params['time']
        latitude = chart_params['latitude']
        longitude = chart_params['longitude']
        zodiac_type = chart_params['zodiac_type']
        house_system = chart_params['house_system']
        timezone_str = chart_params['timezone_str']
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'progress': 20, 'status': 'Calculating planetary positions...'}
        )
        
        # Calculate chart data
        orchestrator = ChartOrchestrator()
        dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
        
        chart_data = orchestrator.calculate_complete_chart(
            dt, latitude, longitude,
            house_system=house_system.capitalize(),
            include_aspects=True,
            include_dignities=True
        )
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'progress': 60, 'status': 'Chart calculation completed'}
        )
        
        # Cache the result
        birth_data = {
            'date': date,
            'time': time_str,
            'latitude': latitude,
            'longitude': longitude,
            'timezone': timezone_str,
            'zodiac_type': zodiac_type,
            'house_system': house_system
        }
        ephemeris_cache.cache_ephemeris_calculation(birth_data, chart_data)
        
        # Update task status
        TaskStatus.objects.filter(task_id=task_id).update(
            state='SUCCESS',
            progress=100,
            status_message='Chart generation completed successfully',
            result={'chart_data': chart_data},
            completed_at=timezone.now()
        )
        
        return {
            'success': True,
            'chart_data': chart_data,
            'task_id': task_id,
            'completed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Chart generation task failed: {exc}")
        
        # Update task status
        TaskStatus.objects.filter(task_id=task_id).update(
            state='FAILURE',
            status_message=f'Chart generation failed: {str(exc)}',
            error_message=str(exc),
            completed_at=timezone.now()
        )
        
        # Retry the task
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_planet_interpretations_task(self, chart_data: Dict[str, Any], 
                                       interpretation_params: Dict[str, Any],
                                       user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Background task for generating planet interpretations.
    
    Args:
        chart_data: Chart data from previous calculation
        interpretation_params: AI interpretation parameters
        user_id: Optional user ID for tracking
        
    Returns:
        Planet interpretations
    """
    task_id = self.request.id
    
    try:
        # Update task status
        TaskStatus.objects.update_or_create(
            task_id=task_id,
            defaults={
                'task_type': 'interpretation',
                'state': 'PROGRESS',
                'progress': 0,
                'status_message': 'Starting planet interpretations...',
                'parameters': interpretation_params,
                'user_id': user_id,
                'started_at': timezone.now()
            }
        )
        
        # Extract parameters
        model_name = interpretation_params['model_name']
        temperature = interpretation_params['temperature']
        max_tokens = interpretation_params['max_tokens']
        date = interpretation_params['date']
        time_str = interpretation_params['time']
        location = interpretation_params['location']
        
        # Get planetary positions
        positions = chart_data.get('planets', {})
        interpretations = {}
        total_planets = len([p for p in positions.keys() if p in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']])
        current_planet = 0
        
        for planet, pos in positions.items():
            if planet in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']:
                try:
                    current_planet += 1
                    progress = int((current_planet / total_planets) * 80) + 10
                    
                    # Update progress
                    self.update_state(
                        state='PROGRESS',
                        meta={'progress': progress, 'status': f'Generating {planet} interpretation...'}
                    )
                    
                    # Get aspects for this planet
                    planet_aspects = pos.get('aspects', [])
                    aspect_summary = ""
                    if planet_aspects:
                        aspect_descriptions = []
                        for aspect in planet_aspects:
                            aspect_type = aspect.get('type', '')
                            aspect_planet = aspect.get('planet', '')
                            aspect_orb = aspect.get('orb', 0)
                            if aspect_type and aspect_planet:
                                aspect_descriptions.append(f"{aspect_type} {aspect_planet} (orb: {aspect_orb:.1f}°)")
                        aspect_summary = "; ".join(aspect_descriptions)
                    
                    # Get dignity status
                    dignity_status = pos.get('dignity', 'Neutral')
                    planet_house = pos.get('house', 1)
                    
                    # Generate prompt
                    prompt = prompt_manager.format_planet_prompt(
                        planet,
                        date=date,
                        time=time_str,
                        location=location,
                        sign=pos.get('sign', ''),
                        house=planet_house,
                        position=pos.get('absolute_degree', 0.0),
                        retrograde_status=pos.get('retrograde', ''),
                        aspect_summary=aspect_summary,
                        dignity_status=dignity_status
                    )
                    
                    if not prompt:
                        interpretations[planet] = f"Unable to generate interpretation for {planet} due to missing prompt data."
                        continue
                    
                    # Generate interpretation
                    interpretation = generate_interpretation(
                        prompt, model_name, temperature, max_tokens
                    )
                    
                    interpretations[planet] = interpretation
                    
                    # Small delay to avoid overwhelming the AI API
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error generating interpretation for {planet}: {e}")
                    interpretations[planet] = f"Error generating interpretation for {planet}: {str(e)}"
        
        # Cache the interpretations
        interpretation_key = {
            'chart_data': chart_data,
            'model_name': model_name,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'interpretation_type': 'planetary'
        }
        ai_cache.cache_interpretation(interpretation_key, interpretations, model_name, temperature)
        
        # Update task status
        TaskStatus.objects.filter(task_id=task_id).update(
            state='SUCCESS',
            progress=100,
            status_message='Planet interpretations completed successfully',
            result={'interpretations': interpretations},
            completed_at=timezone.now()
        )
        
        return {
            'success': True,
            'interpretations': interpretations,
            'task_id': task_id,
            'completed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Planet interpretations task failed: {exc}")
        
        # Update task status
        TaskStatus.objects.filter(task_id=task_id).update(
            state='FAILURE',
            status_message=f'Planet interpretations failed: {str(exc)}',
            error_message=str(exc),
            completed_at=timezone.now()
        )
        
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_master_interpretation_task(self, chart_data: Dict[str, Any],
                                      interpretation_params: Dict[str, Any],
                                      user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Background task for generating master interpretation.
    
    Args:
        chart_data: Chart data from previous calculation
        interpretation_params: AI interpretation parameters
        user_id: Optional user ID for tracking
        
    Returns:
        Master interpretation
    """
    task_id = self.request.id
    
    try:
        # Update task status
        TaskStatus.objects.update_or_create(
            task_id=task_id,
            defaults={
                'task_type': 'interpretation',
                'state': 'PROGRESS',
                'progress': 0,
                'status_message': 'Starting master interpretation...',
                'parameters': interpretation_params,
                'user_id': user_id,
                'started_at': timezone.now()
            }
        )
        
        # Extract parameters
        model_name = interpretation_params['model_name']
        temperature = interpretation_params['temperature']
        max_tokens = interpretation_params['max_tokens']
        date = interpretation_params['date']
        time_str = interpretation_params['time']
        location = interpretation_params['location']
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'progress': 30, 'status': 'Preparing master interpretation data...'}
        )
        
        # Prepare chart data for master interpretation
        positions = chart_data.get('planets', {})
        houses_data = chart_data.get('houses', {})
        ascendant = houses_data.get('ascendant', {})
        houses = houses_data.get('cusps', {})
        
        # Build master prompt data
        asc_sign = ascendant.get('sign', '')
        asc_deg = ascendant.get('degree_in_sign', 0.0)
        ascendant_str = f"{asc_sign} {asc_deg}°"
        
        midheaven_str = ''
        if isinstance(houses, list) and len(houses) > 9:
            mh = houses[9]
            if isinstance(mh, (float, int)):
                midheaven_str = f"{mh}°"
            else:
                try:
                    midheaven_str = f"{float(mh)}°"
                except Exception:
                    midheaven_str = ''
        
        # Get aspects for master interpretation
        all_aspects = chart_data.get('aspects', {})
        aspect_summary = ""
        if all_aspects:
            aspect_descriptions = []
            for planet, aspects in all_aspects.items():
                for aspect in aspects:
                    aspect_type = aspect.get('type', '')
                    aspect_planet = aspect.get('planet', '')
                    aspect_orb = aspect.get('orb', 0)
                    if aspect_type and aspect_planet:
                        aspect_descriptions.append(f"{planet} {aspect_type} {aspect_planet} (orb: {aspect_orb:.1f}°)")
            aspect_summary = "; ".join(aspect_descriptions[:10])
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'progress': 60, 'status': 'Generating master interpretation...'}
        )
        
        # Build master prompt data
        master_prompt_data = {
            'date': str(date),
            'time': str(time_str),
            'location': str(location),
            'sun_sign': str(positions.get('Sun', {}).get('sign', '')),
            'sun_house': str(positions.get('Sun', {}).get('house', 1)),
            'moon_sign': str(positions.get('Moon', {}).get('sign', '')),
            'moon_house': str(positions.get('Moon', {}).get('house', 1)),
            'mercury_sign': str(positions.get('Mercury', {}).get('sign', '')),
            'mercury_house': str(positions.get('Mercury', {}).get('house', 1)),
            'venus_sign': str(positions.get('Venus', {}).get('sign', '')),
            'venus_house': str(positions.get('Venus', {}).get('house', 1)),
            'mars_sign': str(positions.get('Mars', {}).get('sign', '')),
            'mars_house': str(positions.get('Mars', {}).get('house', 1)),
            'jupiter_sign': str(positions.get('Jupiter', {}).get('sign', '')),
            'jupiter_house': str(positions.get('Jupiter', {}).get('house', 1)),
            'saturn_sign': str(positions.get('Saturn', {}).get('sign', '')),
            'saturn_house': str(positions.get('Saturn', {}).get('house', 1)),
            'uranus_sign': str(positions.get('Uranus', {}).get('sign', '')),
            'uranus_house': str(positions.get('Uranus', {}).get('house', 1)),
            'neptune_sign': str(positions.get('Neptune', {}).get('sign', '')),
            'neptune_house': str(positions.get('Neptune', {}).get('house', 1)),
            'pluto_sign': str(positions.get('Pluto', {}).get('sign', '')),
            'pluto_house': str(positions.get('Pluto', {}).get('house', 1)),
            'ascendant': ascendant_str,
            'midheaven': midheaven_str,
            'aspects': aspect_summary,
            'dignities': ''
        }
        
        # Ensure all values are strings
        master_prompt_data = {k: str(v) for k, v in master_prompt_data.items()}
        
        # Generate prompt
        prompt = prompt_manager.format_master_prompt(**master_prompt_data)
        
        if not prompt:
            interpretation = "Unable to generate master interpretation due to missing prompt data."
        else:
            # Generate interpretation
            interpretation = generate_interpretation(
                prompt, model_name, temperature, max_tokens
            )
        
        # Cache the interpretation
        interpretation_key = {
            'chart_data': chart_data,
            'model_name': model_name,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'interpretation_type': 'master'
        }
        ai_cache.cache_interpretation(interpretation_key, interpretation, model_name, temperature)
        
        # Update task status
        TaskStatus.objects.filter(task_id=task_id).update(
            state='SUCCESS',
            progress=100,
            status_message='Master interpretation completed successfully',
            result={'interpretation': interpretation},
            completed_at=timezone.now()
        )
        
        return {
            'success': True,
            'interpretation': interpretation,
            'task_id': task_id,
            'completed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Master interpretation task failed: {exc}")
        
        # Update task status
        TaskStatus.objects.filter(task_id=task_id).update(
            state='FAILURE',
            status_message=f'Master interpretation failed: {str(exc)}',
            error_message=str(exc),
            completed_at=timezone.now()
        )
        
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_plugin_tasks_task(self, chart_data: Dict[str, Any],
                            plugin_params: Dict[str, Any],
                            user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Background task for processing plugin operations (aspects, houses, etc.).
    
    Args:
        chart_data: Chart data from previous calculation
        plugin_params: Plugin-specific parameters
        user_id: Optional user ID for tracking
        
    Returns:
        Plugin results
    """
    task_id = self.request.id
    
    try:
        # Update task status
        TaskStatus.objects.update_or_create(
            task_id=task_id,
            defaults={
                'task_type': 'plugin_processing',
                'state': 'PROGRESS',
                'progress': 0,
                'status_message': 'Starting plugin processing...',
                'parameters': plugin_params,
                'user_id': user_id,
                'started_at': timezone.now()
            }
        )
        
        results = {}
        
        # Process Aspect Generator plugin
        if plugin_params.get('aspects_enabled', False):
            try:
                self.update_state(
                    state='PROGRESS',
                    meta={'progress': 30, 'status': 'Processing aspects...'}
                )
                
                from plugins import get_plugin_manager
                plugin_manager = get_plugin_manager()
                aspect_plugin = plugin_manager.get_plugin('aspect_generator')
                
                if aspect_plugin:
                    aspect_orb = plugin_params.get('aspect_orb', 8.0)
                    aspect_results = aspect_plugin.calculate_aspects(chart_data, orb=aspect_orb)
                    
                    # Add AI interpretations
                    model_name = plugin_params.get('model_name', 'gpt-4')
                    temperature = plugin_params.get('temperature', 0.7)
                    max_tokens = plugin_params.get('max_tokens', 1000)
                    
                    for aspect in aspect_results:
                        aspect['interpretation'] = aspect_plugin.generate_aspect_interpretation(
                            aspect, chart_data, model_name, temperature, max_tokens
                        )
                    
                    results['aspects'] = aspect_results
                    
            except Exception as e:
                logger.error(f"Error processing aspects: {e}")
                results['aspects'] = []
        
        # Process House Generator plugin
        if plugin_params.get('houses_enabled', False):
            try:
                self.update_state(
                    state='PROGRESS',
                    meta={'progress': 70, 'status': 'Processing houses...'}
                )
                
                from plugins import get_plugin_manager
                plugin_manager = get_plugin_manager()
                house_plugin = plugin_manager.get_plugin('house_generator')
                
                if house_plugin:
                    include_planets = plugin_params.get('include_house_planets', True)
                    model_name = plugin_params.get('model_name', 'gpt-4')
                    temperature = plugin_params.get('temperature', 0.7)
                    max_tokens = plugin_params.get('max_tokens', 1000)
                    
                    house_results = house_plugin.generate_house_interpretations(
                        chart_data, include_planets, model_name, temperature, max_tokens
                    )
                    
                    results['houses'] = house_results
                    
            except Exception as e:
                logger.error(f"Error processing houses: {e}")
                results['houses'] = []
        
        # Update task status
        TaskStatus.objects.filter(task_id=task_id).update(
            state='SUCCESS',
            progress=100,
            status_message='Plugin processing completed successfully',
            result=results,
            completed_at=timezone.now()
        )
        
        return {
            'success': True,
            'results': results,
            'task_id': task_id,
            'completed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Plugin processing task failed: {exc}")
        
        # Update task status
        TaskStatus.objects.filter(task_id=task_id).update(
            state='FAILURE',
            status_message=f'Plugin processing failed: {str(exc)}',
            error_message=str(exc),
            completed_at=timezone.now()
        )
        
        raise self.retry(exc=exc)


@shared_task(bind=True)
def cleanup_expired_tasks_task(self):
    """
    Background task to cleanup expired task status records.
    """
    try:
        # Delete tasks older than 7 days
        cutoff_date = timezone.now() - timezone.timedelta(days=7)
        deleted_count = TaskStatus.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} expired task records")
        
        return {
            'success': True,
            'deleted_count': deleted_count
        }
        
    except Exception as exc:
        logger.error(f"Task cleanup failed: {exc}")
        return {
            'success': False,
            'error': str(exc)
        }


# Utility functions for task management
def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task status information
    """
    try:
        task_status = TaskStatus.objects.get(task_id=task_id)
        return {
            'task_id': task_status.task_id,
            'state': task_status.state,
            'progress': task_status.progress,
            'status_message': task_status.status_message,
            'created_at': task_status.created_at.isoformat(),
            'started_at': task_status.started_at.isoformat() if task_status.started_at else None,
            'completed_at': task_status.completed_at.isoformat() if task_status.completed_at else None,
            'result': task_status.result,
            'error_message': task_status.error_message
        }
    except TaskStatus.DoesNotExist:
        return None


def cancel_task(task_id: str) -> bool:
    """
    Cancel a running task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        True if task was cancelled successfully
    """
    try:
        # Revoke the Celery task
        from celery import current_app
        current_app.control.revoke(task_id, terminate=True)
        
        # Update task status
        TaskStatus.objects.filter(task_id=task_id).update(
            state='CANCELLED',
            status_message='Task cancelled by user',
            completed_at=timezone.now()
        )
        
        return True
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return False 