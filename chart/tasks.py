import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from celery import shared_task, current_task
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

from .services.chart_orchestrator import ChartOrchestrator
from ai_integration.openrouter_api import generate_interpretation, get_available_models
from .prompts import prompt_manager

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='chart.tasks.generate_chart_task')
def generate_chart_task(self, chart_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task for generating complete astrological charts with interpretations.

    Args:
        chart_params: Dictionary containing chart generation parameters

    Returns:
        Dictionary containing chart data and interpretations
    """
    task_id = self.request.id
    logger.info(f"Starting chart generation task {task_id}")

    try:
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Calculating ephemeris data...', 'progress': 10}
        )

        # Extract parameters
        utc_date = chart_params['utc_date']
        utc_time = chart_params['utc_time']
        latitude = chart_params['latitude']
        longitude = chart_params['longitude']
        zodiac_type = chart_params['zodiac_type']
        house_system = chart_params['house_system']
        model_name = chart_params['model_name']
        temperature = chart_params['temperature']
        max_tokens = chart_params['max_tokens']
        location = chart_params['location']

        # Calculate chart data using new orchestrator
        orchestrator = ChartOrchestrator()
        
        # Parse datetime
        try:
            dt = datetime.strptime(f"{utc_date} {utc_time}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.strptime(f"{utc_date} {utc_time}", "%Y-%m-%d %H:%M")
        
        # Calculate complete chart
        chart_data = orchestrator.calculate_complete_chart(
            dt, latitude, longitude,
            house_system=house_system.capitalize(),
            include_aspects=True,
            include_dignities=True
        )
        
        # Add additional data for compatibility
        chart_data.update({
            'birth_date': utc_date,
            'birth_time': utc_time,
            'location': location
        })

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Generating planet interpretations...', 'progress': 30}
        )

        # Generate planet interpretations
        planet_interpretations = {}
        planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']

        for i, planet in enumerate(planets):
            if planet in chart_data.get('planets', {}):
                try:
                    planet_data = chart_data['planets'][planet]
                    prompt = prompt_manager.format_planet_prompt(
                        planet,
                        date=utc_date,
                        time=utc_time,
                        location=location,
                        sign=planet_data.get('sign', ''),
                        house=planet_data.get('house', 1),
                        position=planet_data.get('absolute_degree', 0.0),
                        retrograde_status=planet_data.get('retrograde', ''),
                        aspect_summary="",  # TODO: Add aspect calculation
                        dignity_status=""   # TODO: Add dignity calculation
                    )
                    interpretation = generate_interpretation(
                        prompt, model_name, temperature, max_tokens
                    )
                    planet_interpretations[planet] = interpretation

                    # Update progress for each planet
                    progress = 30 + (i + 1) * (40 / len(planets))
                    self.update_state(
                        state='PROGRESS',
                        meta={'status': f'Generated {planet} interpretation...', 'progress': int(progress)}
                    )

                except Exception as e:
                    logger.error(f"Error generating {planet} interpretation: {e}")
                    planet_interpretations[planet] = f"Error generating {planet} interpretation: {str(e)}"

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Generating master interpretation...', 'progress': 80}
        )

        # Generate master interpretation
        try:
            planets = chart_data.get('planets', {})
            houses_data = chart_data.get('houses', {})
            ascendant = houses_data.get('ascendant', {})
            mc = houses_data.get('mc', {})
            
            master_prompt_data = {
                'date': utc_date,
                'time': utc_time,
                'location': location,
                'sun_sign': planets.get('Sun', {}).get('sign', ''),
                'sun_house': planets.get('Sun', {}).get('house', 1),
                'moon_sign': planets.get('Moon', {}).get('sign', ''),
                'moon_house': planets.get('Moon', {}).get('house', 1),
                'mercury_sign': planets.get('Mercury', {}).get('sign', ''),
                'mercury_house': planets.get('Mercury', {}).get('house', 1),
                'venus_sign': planets.get('Venus', {}).get('sign', ''),
                'venus_house': planets.get('Venus', {}).get('house', 1),
                'mars_sign': planets.get('Mars', {}).get('sign', ''),
                'mars_house': planets.get('Mars', {}).get('house', 1),
                'jupiter_sign': planets.get('Jupiter', {}).get('sign', ''),
                'jupiter_house': planets.get('Jupiter', {}).get('house', 1),
                'saturn_sign': planets.get('Saturn', {}).get('sign', ''),
                'saturn_house': planets.get('Saturn', {}).get('house', 1),
                'uranus_sign': planets.get('Uranus', {}).get('sign', ''),
                'uranus_house': planets.get('Uranus', {}).get('house', 1),
                'neptune_sign': planets.get('Neptune', {}).get('sign', ''),
                'neptune_house': planets.get('Neptune', {}).get('house', 1),
                'pluto_sign': planets.get('Pluto', {}).get('sign', ''),
                'pluto_house': planets.get('Pluto', {}).get('house', 1),
                'ascendant': ascendant.get('sign', '') + ' ' + str(ascendant.get('degree_in_sign', 0)) + '°',
                'midheaven': mc.get('sign', '') + ' ' + str(mc.get('degree_in_sign', 0)) + '°',
                'aspects': '',  # TODO: Add aspect calculation
                'dignities': ''  # TODO: Add dignity calculation
            }
            master_prompt = prompt_manager.format_master_prompt(**master_prompt_data)
            master_interpretation = generate_interpretation(
                master_prompt, model_name, temperature, max_tokens
            )
        except Exception as e:
            logger.error(f"Error generating master interpretation: {e}")
            master_interpretation = f"Error generating master interpretation: {str(e)}"

        # Prepare final result
        result = {
            'success': True,
            'chart_data': chart_data,
            'planet_interpretations': planet_interpretations,
            'master_interpretation': master_interpretation,
            'task_id': task_id,
            'completed_at': timezone.now().isoformat()
        }

        # Cache the result
        cache_key = f"chart_result_{task_id}"
        cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour

        logger.info(f"Completed chart generation task {task_id}")
        return result

    except Exception as e:
        logger.error(f"Error in chart generation task {task_id}: {e}")
        error_result = {
            'success': False,
            'error': str(e),
            'task_id': task_id,
            'completed_at': timezone.now().isoformat()
        }

        # Cache the error result
        cache_key = f"chart_result_{task_id}"
        cache.set(cache_key, error_result, timeout=3600)

        return error_result


@shared_task(bind=True, name='chart.tasks.generate_interpretation_task')
def generate_interpretation_task(self, chart_data: Dict[str, Any], interpretation_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task for generating AI interpretations of existing chart data.

    Args:
        chart_data: Pre-calculated chart data
        interpretation_params: Parameters for interpretation generation

    Returns:
        Dictionary containing interpretations
    """
    task_id = self.request.id
    logger.info(f"Starting interpretation generation task {task_id}")

    try:
        # Extract parameters
        model_name = interpretation_params['model_name']
        temperature = interpretation_params['temperature']
        max_tokens = interpretation_params['max_tokens']
        interpretation_type = interpretation_params.get('interpretation_type', 'comprehensive')

        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Generating interpretations...', 'progress': 20}
        )

        # Generate interpretations based on type
        if interpretation_type == 'planets_only':
            # Generate only planet interpretations
            planet_interpretations = {}
            planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']

            for i, planet in enumerate(planets):
                if planet in chart_data.get('planetary_positions', {}):
                    try:
                        prompt = prompt_manager.format_planet_prompt(
                            planet,
                            date=chart_data.get('birth_date', ''),
                            time=chart_data.get('birth_time', ''),
                            location=chart_data.get('location', ''),
                            sign=chart_data['planetary_positions'][planet].get('sign', ''),
                            house=chart_data['planetary_positions'][planet].get('house', 1),
                            position=chart_data['planetary_positions'][planet].get('absolute_degree', 0.0),
                            retrograde_status=chart_data['planetary_positions'][planet].get('retrograde', ''),
                            aspect_summary="",  # TODO: Add aspect calculation
                            dignity_status=""   # TODO: Add dignity calculation
                        )
                        interpretation = generate_interpretation(
                            prompt, model_name, temperature, max_tokens
                        )
                        planet_interpretations[planet] = interpretation

                        progress = 20 + (i + 1) * (60 / len(planets))
                        self.update_state(
                            state='PROGRESS',
                            meta={'status': f'Generated {planet} interpretation...', 'progress': int(progress)}
                        )

                    except Exception as e:
                        logger.error(f"Error generating {planet} interpretation: {e}")
                        planet_interpretations[planet] = f"Error generating {planet} interpretation: {str(e)}"

            result = {
                'success': True,
                'planet_interpretations': planet_interpretations,
                'task_id': task_id,
                'completed_at': timezone.now().isoformat()
            }

        elif interpretation_type == 'master_only':
            # Generate only master interpretation
            try:
                master_prompt_data = {
                    'date': chart_data.get('birth_date', ''),
                    'time': chart_data.get('birth_time', ''),
                    'location': chart_data.get('location', ''),
                    'sun_sign': chart_data['planetary_positions'].get('Sun', {}).get('sign', ''),
                    'sun_house': chart_data['planetary_positions'].get('Sun', {}).get('house', 1),
                    'moon_sign': chart_data['planetary_positions'].get('Moon', {}).get('sign', ''),
                    'moon_house': chart_data['planetary_positions'].get('Moon', {}).get('house', 1),
                    'mercury_sign': chart_data['planetary_positions'].get('Mercury', {}).get('sign', ''),
                    'mercury_house': chart_data['planetary_positions'].get('Mercury', {}).get('house', 1),
                    'venus_sign': chart_data['planetary_positions'].get('Venus', {}).get('sign', ''),
                    'venus_house': chart_data['planetary_positions'].get('Venus', {}).get('house', 1),
                    'mars_sign': chart_data['planetary_positions'].get('Mars', {}).get('sign', ''),
                    'mars_house': chart_data['planetary_positions'].get('Mars', {}).get('house', 1),
                    'jupiter_sign': chart_data['planetary_positions'].get('Jupiter', {}).get('sign', ''),
                    'jupiter_house': chart_data['planetary_positions'].get('Jupiter', {}).get('house', 1),
                    'saturn_sign': chart_data['planetary_positions'].get('Saturn', {}).get('sign', ''),
                    'saturn_house': chart_data['planetary_positions'].get('Saturn', {}).get('house', 1),
                    'uranus_sign': chart_data['planetary_positions'].get('Uranus', {}).get('sign', ''),
                    'uranus_house': chart_data['planetary_positions'].get('Uranus', {}).get('house', 1),
                    'neptune_sign': chart_data['planetary_positions'].get('Neptune', {}).get('sign', ''),
                    'neptune_house': chart_data['planetary_positions'].get('Neptune', {}).get('house', 1),
                    'pluto_sign': chart_data['planetary_positions'].get('Pluto', {}).get('sign', ''),
                    'pluto_house': chart_data['planetary_positions'].get('Pluto', {}).get('house', 1),
                    'ascendant': chart_data['ascendant'].get('sign', '') + ' ' + str(chart_data['ascendant'].get('degree_in_sign', 0.0)) + '°',
                    'midheaven': str(chart_data['house_signs'].get(10, '')) + ' ' + str(chart_data['house_cusps'].get(9, 0.0)) + '°' if len(chart_data.get('house_signs', {})) > 10 and len(chart_data.get('house_cusps', [])) > 9 else '',
                    'aspects': '',  # TODO: Add aspect calculation
                    'dignities': ''  # TODO: Add dignity calculation
                }
                master_prompt = prompt_manager.format_master_prompt(**master_prompt_data)
                master_interpretation = generate_interpretation(
                    master_prompt, model_name, temperature, max_tokens
                )

                result = {
                    'success': True,
                    'master_interpretation': master_interpretation,
                    'task_id': task_id,
                    'completed_at': timezone.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error generating master interpretation: {e}")
                result = {
                    'success': False,
                    'error': f"Error generating master interpretation: {str(e)}",
                    'task_id': task_id,
                    'completed_at': timezone.now().isoformat()
                }

        else:
            # Generate comprehensive interpretation (both planets and master)
            planet_interpretations = {}
            planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']

            for i, planet in enumerate(planets):
                if planet in chart_data.get('planetary_positions', {}):
                    try:
                        prompt = prompt_manager.format_planet_prompt(
                            planet,
                            date=chart_data.get('birth_date', ''),
                            time=chart_data.get('birth_time', ''),
                            location=chart_data.get('location', ''),
                            sign=chart_data['planetary_positions'][planet].get('sign', ''),
                            house=chart_data['planetary_positions'][planet].get('house', 1),
                            position=chart_data['planetary_positions'][planet].get('absolute_degree', 0.0),
                            retrograde_status=chart_data['planetary_positions'][planet].get('retrograde', ''),
                            aspect_summary="",  # TODO: Add aspect calculation
                            dignity_status=""   # TODO: Add dignity calculation
                        )
                        interpretation = generate_interpretation(
                            prompt, model_name, temperature, max_tokens
                        )
                        planet_interpretations[planet] = interpretation

                        progress = 20 + (i + 1) * (40 / len(planets))
                        self.update_state(
                            state='PROGRESS',
                            meta={'status': f'Generated {planet} interpretation...', 'progress': int(progress)}
                        )

                    except Exception as e:
                        logger.error(f"Error generating {planet} interpretation: {e}")
                        planet_interpretations[planet] = f"Error generating {planet} interpretation: {str(e)}"

            # Generate master interpretation
            self.update_state(
                state='PROGRESS',
                meta={'status': 'Generating master interpretation...', 'progress': 80}
            )

            try:
                master_prompt_data = {
                    'date': chart_data.get('birth_date', ''),
                    'time': chart_data.get('birth_time', ''),
                    'location': chart_data.get('location', ''),
                    'sun_sign': chart_data['planetary_positions'].get('Sun', {}).get('sign', ''),
                    'sun_house': chart_data['planetary_positions'].get('Sun', {}).get('house', 1),
                    'moon_sign': chart_data['planetary_positions'].get('Moon', {}).get('sign', ''),
                    'moon_house': chart_data['planetary_positions'].get('Moon', {}).get('house', 1),
                    'mercury_sign': chart_data['planetary_positions'].get('Mercury', {}).get('sign', ''),
                    'mercury_house': chart_data['planetary_positions'].get('Mercury', {}).get('house', 1),
                    'venus_sign': chart_data['planetary_positions'].get('Venus', {}).get('sign', ''),
                    'venus_house': chart_data['planetary_positions'].get('Venus', {}).get('house', 1),
                    'mars_sign': chart_data['planetary_positions'].get('Mars', {}).get('sign', ''),
                    'mars_house': chart_data['planetary_positions'].get('Mars', {}).get('house', 1),
                    'jupiter_sign': chart_data['planetary_positions'].get('Jupiter', {}).get('sign', ''),
                    'jupiter_house': chart_data['planetary_positions'].get('Jupiter', {}).get('house', 1),
                    'saturn_sign': chart_data['planetary_positions'].get('Saturn', {}).get('sign', ''),
                    'saturn_house': chart_data['planetary_positions'].get('Saturn', {}).get('house', 1),
                    'uranus_sign': chart_data['planetary_positions'].get('Uranus', {}).get('sign', ''),
                    'uranus_house': chart_data['planetary_positions'].get('Uranus', {}).get('house', 1),
                    'neptune_sign': chart_data['planetary_positions'].get('Neptune', {}).get('sign', ''),
                    'neptune_house': chart_data['planetary_positions'].get('Neptune', {}).get('house', 1),
                    'pluto_sign': chart_data['planetary_positions'].get('Pluto', {}).get('sign', ''),
                    'pluto_house': chart_data['planetary_positions'].get('Pluto', {}).get('house', 1),
                    'ascendant': chart_data['ascendant'].get('sign', '') + ' ' + str(chart_data['ascendant'].get('degree_in_sign', 0.0)) + '°',
                    'midheaven': str(chart_data['house_signs'].get(10, '')) + ' ' + str(chart_data['house_cusps'].get(9, 0.0)) + '°' if len(chart_data.get('house_signs', {})) > 10 and len(chart_data.get('house_cusps', [])) > 9 else '',
                    'aspects': '',  # TODO: Add aspect calculation
                    'dignities': ''  # TODO: Add dignity calculation
                }
                master_prompt = prompt_manager.format_master_prompt(**master_prompt_data)
                master_interpretation = generate_interpretation(
                    master_prompt, model_name, temperature, max_tokens
                )

                result = {
                    'success': True,
                    'planet_interpretations': planet_interpretations,
                    'master_interpretation': master_interpretation,
                    'task_id': task_id,
                    'completed_at': timezone.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error generating master interpretation: {e}")
                result = {
                    'success': False,
                    'error': f"Error generating master interpretation: {str(e)}",
                    'task_id': task_id,
                    'completed_at': timezone.now().isoformat()
                }

        # Cache the result
        cache_key = f"interpretation_result_{task_id}"
        cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour

        logger.info(f"Completed interpretation generation task {task_id}")
        return result

    except Exception as e:
        logger.error(f"Error in interpretation generation task {task_id}: {e}")
        error_result = {
            'success': False,
            'error': str(e),
            'task_id': task_id,
            'completed_at': timezone.now().isoformat()
        }

        # Cache the error result
        cache_key = f"interpretation_result_{task_id}"
        cache.set(cache_key, error_result, timeout=3600)

        return error_result


@shared_task(bind=True, name='chart.tasks.calculate_ephemeris_task')
def calculate_ephemeris_task(self, ephemeris_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Background task for calculating ephemeris data only.

    Args:
        ephemeris_params: Parameters for ephemeris calculation

    Returns:
        Dictionary containing ephemeris data
    """
    task_id = self.request.id
    logger.info(f"Starting ephemeris calculation task {task_id}")

    try:
        # Extract parameters
        utc_date = ephemeris_params['utc_date']
        utc_time = ephemeris_params['utc_time']
        latitude = ephemeris_params['latitude']
        longitude = ephemeris_params['longitude']
        zodiac_type = ephemeris_params['zodiac_type']
        house_system = ephemeris_params['house_system']

        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Calculating ephemeris data...', 'progress': 50}
        )

        # Calculate ephemeris data
        jd = get_julian_day(utc_date, utc_time)
        positions = get_planet_positions(jd, latitude, longitude, zodiac_type=zodiac_type)
        asc, houses, house_signs = get_ascendant_and_houses(jd, latitude, longitude, house_system=house_system)

        result = {
            'success': True,
            'julian_day': jd,
            'positions': positions,
            'ascendant': asc,
            'houses': houses,
            'house_signs': house_signs,
            'task_id': task_id,
            'completed_at': timezone.now().isoformat()
        }

        # Cache the result
        cache_key = f"ephemeris_result_{task_id}"
        cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour

        logger.info(f"Completed ephemeris calculation task {task_id}")
        return result

    except Exception as e:
        logger.error(f"Error in ephemeris calculation task {task_id}: {e}")
        error_result = {
            'success': False,
            'error': str(e),
            'task_id': task_id,
            'completed_at': timezone.now().isoformat()
        }

        # Cache the error result
        cache_key = f"ephemeris_result_{task_id}"
        cache.set(cache_key, error_result, timeout=3600)

        return error_result


@shared_task(name='chart.tasks.cleanup_old_tasks')
def cleanup_old_tasks():
    """
    Periodic task to clean up old task results from cache and database.
    """
    logger.info("Starting cleanup of old tasks")

    try:
        # Clean up old cached results (older than 24 hours)
        cutoff_time = timezone.now() - timedelta(hours=24)

        # This is a simplified cleanup - in production you might want to scan all cache keys
        # For now, we'll rely on Redis TTL to handle most cleanup

        # Clean up old task results from database
        from django_celery_results.models import TaskResult

        old_results = TaskResult.objects.filter(
            date_done__lt=cutoff_time
        )
        deleted_count = old_results.count()
        old_results.delete()

        logger.info(f"Cleaned up {deleted_count} old task results")
        return {'success': True, 'deleted_count': deleted_count}

    except Exception as e:
        logger.error(f"Error during task cleanup: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(name='chart.tasks.health_check')
def health_check():
    """
    Periodic task to check system health and report metrics.
    """
    logger.info("Running health check")

    try:
        # Check Redis connection
        redis_healthy = False
        try:
            cache.set('health_check', 'ok', timeout=60)
            redis_healthy = cache.get('health_check') == 'ok'
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")

        # Check database connection
        db_healthy = False
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_healthy = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        # Get task queue statistics
        from celery import current_app
        inspect = current_app.control.inspect()

        stats = {
            'redis_healthy': redis_healthy,
            'db_healthy': db_healthy,
            'timestamp': timezone.now().isoformat()
        }

        # Try to get queue stats (might fail if no workers are running)
        try:
            active_tasks = inspect.active()
            reserved_tasks = inspect.reserved()
            stats['active_tasks'] = len(active_tasks) if active_tasks else 0
            stats['reserved_tasks'] = len(reserved_tasks) if reserved_tasks else 0
        except Exception as e:
            logger.warning(f"Could not get queue stats: {e}")
            stats['queue_stats_available'] = False

        logger.info(f"Health check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error during health check: {e}")
        return {'success': False, 'error': str(e)}
