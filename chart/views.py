import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from .services.chart_orchestrator import ChartOrchestrator
from .services.planetary_calculator import PlanetaryCalculator
from .services.caching import ephemeris_cache, ai_cache, user_cache
from .services.business_logic import subscription_logic, customer_lifecycle
from ai_integration.openrouter_api import generate_interpretation, get_available_models
from .prompts import prompt_manager
import pytz
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import re
from django.core.cache import cache
from django.conf import settings
from django.core.exceptions import PermissionDenied
import os
import hashlib
from django.contrib.admin.views.decorators import staff_member_required
from monitoring.health_checks import get_system_health
from monitoring.performance_monitor import get_performance_summary

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEZONE = "America/Halifax"

# Rate limiting settings
RATE_LIMIT_PERIOD = 3600  # 1 hour in seconds
RATE_LIMIT_MAX_REQUESTS = 10  # Maximum requests per period


def local_to_utc(date_str: str, time_str: str, tz_str: str) -> Tuple[str, str]:
    """
    Convert local date/time (and timezone string) to UTC date and time strings.

    Args:
        date_str: Date string in YYYY-MM-DD format
        time_str: Time string in HH:MM or HH:MM:SS format, or datetime.time object
        tz_str: Timezone string (e.g., 'America/New_York')

    Returns:
        Tuple of (UTC date string, UTC time string)

    Raises:
        ValueError: If date/time format is invalid
        pytz.exceptions.UnknownTimeZoneError: If timezone is invalid
    """
    try:
        local_tz = pytz.timezone(tz_str)
        
        # Convert time_str to string if it's a datetime.time object
        if hasattr(time_str, 'strftime'):
            # It's a datetime.time object
            time_str = time_str.strftime('%H:%M:%S')
        else:
            # It's already a string, ensure it's a string
            time_str = str(time_str)
        
        # Clean up time string - remove any trailing :00 if present
        cleaned_time = time_str.rstrip(':00')
        
        # Try different time formats
        time_formats = ['%H:%M:%S', '%H:%M']
        naive_dt = None
        
        for fmt in time_formats:
            try:
                naive_dt = datetime.strptime(f"{date_str} {cleaned_time}", f"%Y-%m-%d {fmt}")
                break
            except ValueError:
                continue
        
        if naive_dt is None:
            raise ValueError(f"Invalid time format: {time_str}. Use HH:MM or HH:MM:SS")
        
        local_dt = local_tz.localize(naive_dt)
        utc_dt = local_dt.astimezone(pytz.utc)
        return utc_dt.strftime("%Y-%m-%d"), utc_dt.strftime("%H:%M")
    except ValueError as e:
        logger.error(f"Invalid date/time format: {e}")
        raise ValueError(f"Invalid date/time format: {e}")
    except pytz.exceptions.UnknownTimeZoneError as e:
        logger.error(f"Invalid timezone: {e}")
        raise ValueError(f"Invalid timezone: {e}")


def get_coordinates(location: str) -> Tuple[float, float]:
    """
    Extract coordinates from location string or use provided lat/lon.
    For now, just returns a placeholder - in production, you'd use a geocoding service.
    """
    # This is a simplified version - in production you'd integrate with a geocoding API
    # For now, just return default coordinates if location is provided
    return 45.5, -64.3  # Default coordinates for testing


def validate_input(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Validate input data for chart generation.

    Returns:
        Tuple of (validated data dict, error message if any)
    """
    try:
        # Handle both form data and JSON data
        if isinstance(data, dict):
            # Check if we have latitude/longitude directly
            if 'latitude' in data and 'longitude' in data:
                try:
                    lat = float(data['latitude'])
                    lon = float(data['longitude'])
                except ValueError:
                    return {}, "Invalid latitude/longitude values"
            elif 'location' in data:
                try:
                    lat, lon = get_coordinates(data['location'])
                except Exception as e:
                    return {}, f"Invalid location: {str(e)}"
            else:
                return {}, "Missing location or latitude/longitude"
        else:
            return {}, "Invalid data format"

        # Required fields (adjusted for form data)
        required_fields = ['date', 'time', 'zodiac_type', 'house_system', 'model_name', 'temperature', 'max_tokens']
        for field in required_fields:
            if field not in data:
                return {}, f"Missing required field: {field}"

        # Handle timezone field (can be 'timezone' or 'timezone_str')
        timezone_str = data.get('timezone_str') or data.get('timezone')
        if not timezone_str:
            return {}, "Missing timezone field"

        # Set default interpretation type if not provided
        interpretation_type = data.get('interpretation_type', 'comprehensive')

        # Date validation
        try:
            datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            return {}, "Invalid date format. Use YYYY-MM-DD"

        # Time validation
        try:
            # Convert time to string if it's a datetime.time object
            time_value = data['time']
            if hasattr(time_value, 'strftime'):
                # It's a datetime.time object
                time_value = time_value.strftime('%H:%M:%S')
            else:
                # It's already a string, ensure it's a string
                time_value = str(time_value)
            
            # Clean up time string - remove any trailing :00 if present
            cleaned_time = time_value.rstrip(':00')
            
            # Try different time formats
            time_formats = ['%H:%M:%S', '%H:%M']
            time_valid = False
            
            for fmt in time_formats:
                try:
                    datetime.strptime(cleaned_time, fmt)
                    time_valid = True
                    break
                except ValueError:
                    continue
            
            if not time_valid:
                return {}, "Invalid time format. Use HH:MM or HH:MM:SS"
        except Exception:
            return {}, "Invalid time format. Use HH:MM or HH:MM:SS"

        # Timezone validation
        try:
            pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            return {}, "Invalid timezone"

        # Zodiac type validation
        if data['zodiac_type'] not in ['tropical', 'sidereal']:
            return {}, "Invalid zodiac type. Use 'tropical' or 'sidereal'"

        # House system validation
        if data['house_system'] not in ['placidus', 'whole_sign']:
            return {}, "Invalid house system. Use 'placidus' or 'whole_sign'"

        # Model validation
        available_models = get_available_models()
        if data['model_name'] not in available_models:
            return {}, f"Invalid model name. Available models: {', '.join(available_models)}"

        # Temperature validation
        try:
            temp = float(data['temperature'])
            if not (0 <= temp <= 1):
                return {}, "Temperature must be between 0 and 1"
        except ValueError:
            return {}, "Invalid temperature value"

        # Max tokens validation
        try:
            tokens = int(data['max_tokens'])
            if not (100 <= tokens <= 4000):
                return {}, "Max tokens must be between 100 and 4000"
        except ValueError:
            return {}, "Invalid max tokens value"

        # All validations passed
        return {
            'date': data['date'],
            'time': time_value,  # Use the processed time value
            'latitude': lat,
            'longitude': lon,
            'location': data.get('location', f"{lat}, {lon}"),
            'timezone_str': timezone_str,
            'zodiac_type': data['zodiac_type'],
            'house_system': data['house_system'],
            'model_name': data['model_name'],
            'temperature': temp,
            'max_tokens': tokens,
            'interpretation_type': interpretation_type
        }, None

    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return {}, f"Validation error: {str(e)}"


def calculate_chart_data_with_caching(utc_date: str, utc_time: str, lat: float, lon: float,
                                      zodiac_type: str, house_system: str, timezone_str: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Calculate chart data using ephemeris with caching support.

    Returns:
        Tuple of (chart data dict, error message if any)
    """
    try:
        # Create birth data for caching
        birth_data = {
            'date': utc_date,
            'time': utc_time,
            'latitude': lat,
            'longitude': lon,
            'timezone': timezone_str,
            'zodiac_type': zodiac_type,
            'house_system': house_system
        }

        # Try to get from cache first
        cached_result = ephemeris_cache.get_ephemeris_calculation(birth_data)
        if cached_result:
            logger.info(f"Using cached chart data for {utc_date} {utc_time}")
            return cached_result, None

        # Calculate if not in cache
        logger.info(f"Calculating chart data for {utc_date} {utc_time}")
        
        # Use the new orchestrator
        orchestrator = ChartOrchestrator()
        
        # Parse datetime
        try:
            dt = datetime.strptime(f"{utc_date} {utc_time}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.strptime(f"{utc_date} {utc_time}", "%Y-%m-%d %H:%M")
        
        # Calculate complete chart
        chart_data = orchestrator.calculate_complete_chart(
            dt, lat, lon, 
            house_system=house_system.capitalize(),
            include_aspects=True,
            include_dignities=True
        )
        
        # Cache the result
        ephemeris_cache.cache_ephemeris_calculation(birth_data, chart_data)

        return chart_data, None

    except Exception as e:
        logger.error(f"Error calculating chart data: {e}")
        return {}, str(e)


def generate_planet_interpretations_with_caching(
    chart_data: Dict[str, Any],
    utc_date: str,
    utc_time: str,
    location: str,
    model_name: str,
    temperature: float,
    max_tokens: int
) -> Dict[str, str]:
    """
    Generate planet interpretations with caching support.
    """
    try:
        # Create cache key for interpretations
        interpretation_key = {
            'chart_data': chart_data,
            'model_name': model_name,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'interpretation_type': 'planetary'
        }

        # Try to get from cache
        cached_interpretations = ai_cache.get_interpretation(
            interpretation_key, model_name, temperature
        )
        if cached_interpretations:
            logger.info("Using cached planet interpretations")
            return cached_interpretations

        # Generate if not in cache
        logger.info("Generating planet interpretations")
        interpretations = {}

        # Get planetary positions (new structure)
        positions = chart_data.get('planets', {})

        for planet, pos in positions.items():
            if planet in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']:
                try:
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

                    # Debug logging for planet house positions
                    planet_house = pos.get('house', 1)
                    logger.debug(f"Planet {planet} - house: {planet_house}, sign: {pos.get('sign', '')}, position: {pos.get('absolute_degree', 0.0)}")

                    # Get planet-specific prompt
                    prompt = prompt_manager.format_planet_prompt(
                        planet,
                        date=utc_date,
                        time=utc_time,
                        location=location,
                        sign=pos.get('sign', ''),
                        house=planet_house,
                        position=pos.get('absolute_degree', 0.0),
                        retrograde_status=pos.get('retrograde', ''),
                        aspect_summary=aspect_summary,
                        dignity_status=dignity_status
                    )

                    # Check if prompt is empty or None
                    if not prompt:
                        logger.warning(f"Empty prompt generated for {planet}, using fallback")
                        interpretations[planet] = f"Unable to generate interpretation for {planet} due to missing prompt data."
                        continue

                    # Generate interpretation
                    interpretation = generate_interpretation(
                        prompt, model_name, temperature, max_tokens
                    )

                    interpretations[planet] = interpretation

                except Exception as e:
                    logger.error(f"Error generating interpretation for {planet}: {e}")
                    interpretations[planet] = f"Error generating interpretation for {planet}: {str(e)}"

        # Cache the interpretations
        ai_cache.cache_interpretation(interpretation_key, interpretations, model_name, temperature)

        return interpretations

    except Exception as e:
        logger.error(f"Error in generate_planet_interpretations_with_caching: {e}")
        return {"error": f"Failed to generate interpretations: {str(e)}"}


def generate_master_interpretation_with_caching(
    chart_data: Dict[str, Any],
    utc_date: str,
    utc_time: str,
    location: str,
    model_name: str,
    temperature: float,
    max_tokens: int
) -> str:
    """
    Generate master interpretation with caching support.
    """
    try:
        # Create cache key for master interpretation
        interpretation_key = {
            'chart_data': chart_data,
            'model_name': model_name,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'interpretation_type': 'master'
        }

        # Try to get from cache
        cached_interpretation = ai_cache.get_interpretation(
            interpretation_key, model_name, temperature
        )
        if cached_interpretation:
            logger.info("Using cached master interpretation")
            return cached_interpretation

        # Generate if not in cache
        logger.info("Generating master interpretation")

        # Get master prompt (new structure)
        positions = chart_data.get('planets', {})
        houses_data = chart_data.get('houses', {})
        ascendant = houses_data.get('ascendant', {})
        houses = houses_data.get('cusps', {})

        # Debug logging to see what we're getting
        logger.debug(f"Chart data keys: {list(chart_data.keys())}")
        logger.debug(f"Planetary positions keys: {list(positions.keys())}")
        logger.debug(f"Sun data: {positions.get('Sun', {})}")
        logger.debug(f"Moon data: {positions.get('Moon', {})}")
        logger.debug(f"Mercury data: {positions.get('Mercury', {})}")
        logger.debug(f"Venus data: {positions.get('Venus', {})}")
        logger.debug(f"Mars data: {positions.get('Mars', {})}")
        logger.debug(f"Jupiter data: {positions.get('Jupiter', {})}")
        logger.debug(f"Saturn data: {positions.get('Saturn', {})}")
        logger.debug(f"Uranus data: {positions.get('Uranus', {})}")
        logger.debug(f"Neptune data: {positions.get('Neptune', {})}")
        logger.debug(f"Pluto data: {positions.get('Pluto', {})}")

        try:
            asc_sign = ascendant.get('sign', '')
            asc_deg = ascendant.get('degree_in_sign', 0.0)
            if not isinstance(asc_sign, str):
                asc_sign = str(asc_sign)
            if not isinstance(asc_deg, (float, int)):
                try:
                    asc_deg = float(asc_deg)
                except Exception:
                    asc_deg = 0.0
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
                aspect_summary = "; ".join(aspect_descriptions[:10])  # Limit to first 10 aspects

            master_prompt_data = {
                'date': str(utc_date),
                'time': str(utc_time),
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
                'dignities': ''  # TODO: Add dignity calculation
            }
        except TypeError as e:
            logger.error(f"TypeError constructing master_prompt_data: {e}")
            logger.error(f"positions: {positions}")
            logger.error(f"ascendant: {ascendant}")
            logger.error(f"houses: {houses}")
            raise

        # Ensure all values are strings
        master_prompt_data = {k: str(v) for k, v in master_prompt_data.items()}

        # Log types and values for debugging
        for k, v in master_prompt_data.items():
            logger.info(f"master_prompt_data[{k!r}] = {v!r} (type: {type(v)})")

        prompt = prompt_manager.format_master_prompt(**master_prompt_data)

        # Check if prompt is empty or None
        if not prompt:
            logger.warning("Empty prompt generated for master interpretation, using fallback")
            return "Unable to generate master interpretation due to missing prompt data."

        # Generate interpretation
        interpretation = generate_interpretation(
            prompt, model_name, temperature, max_tokens
        )

        # Cache the interpretation
        ai_cache.cache_interpretation(interpretation_key, interpretation, model_name, temperature)

        return interpretation

    except Exception as e:
        logger.error(f"Error in generate_master_interpretation_with_caching: {e}")
        return f"Error generating master interpretation: {str(e)}"


def check_rate_limit(request):
    """
    Check if the request exceeds rate limits.

    Args:
        request: The HTTP request

    Returns:
        bool: True if rate limit is exceeded
    """
    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    # Create cache key
    cache_key = f'rate_limit_{ip}'

    # Get current count
    count = cache.get(cache_key, 0)

    if count >= RATE_LIMIT_MAX_REQUESTS:
        return True

    # Increment count
    cache.set(cache_key, count + 1, RATE_LIMIT_PERIOD)
    return False


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def chart_form(request):
    """
    Handle chart form display and submission.
    """
    if request.method == "POST":
        try:
            # Parse JSON data
            data = json.loads(request.body)
            logger.debug(f"Received form data: {data}")

            # Validate input
            params, error = validate_input(data)
            if error:
                return JsonResponse({"success": False, "error": error}, status=400)

            # Convert to UTC
            utc_date, utc_time = local_to_utc(
                params['date'],
                params['time'],
                params['timezone_str']
            )
            logger.debug(f"Converted to UTC: {utc_date} {utc_time}")

            # Calculate chart data
            chart_data, error = calculate_chart_data_with_caching(
                utc_date,
                utc_time,
                params['latitude'],
                params['longitude'],
                params['zodiac_type'],
                params['house_system'],
                params['timezone_str']
            )
            if error:
                return JsonResponse({"success": False, "error": error}, status=500)
            logger.debug(f"Calculated chart data: {chart_data}")

            # Generate interpretations
            logger.debug("Starting planet interpretations generation...")
            planet_interpretations = generate_planet_interpretations_with_caching(
                chart_data,
                utc_date,
                utc_time,
                params['location'],
                params['model_name'],
                params['temperature'],
                params['max_tokens']
            )
            logger.debug("Generated planet interpretations")

            logger.debug("Starting master interpretation generation...")
            master_interpretation = generate_master_interpretation_with_caching(
                chart_data,
                utc_date,
                utc_time,
                params['location'],
                params['model_name'],
                params['temperature'],
                params['max_tokens']
            )
            logger.debug("Generated master interpretation")

            # Plugin integration - Aspect Generator
            aspect_results = []
            aspect_orb = None
            aspects_enabled = False
            try:
                aspect_orb = float(data.get('aspect_orb', 8.0))
            except Exception:
                aspect_orb = 8.0
            aspects_enabled = str(data.get('aspects_enabled', 'true')).lower() in ['true', '1', 'yes', 'on']
            if aspects_enabled:
                try:
                    from plugins import get_plugin_manager
                    plugin_manager = get_plugin_manager()
                    aspect_plugin = plugin_manager.get_plugin('aspect_generator')
                    if aspect_plugin:
                        aspect_results = aspect_plugin.calculate_aspects(chart_data, orb=aspect_orb)
                        # Add AI interpretations using the same settings as main chart generation
                        for aspect in aspect_results:
                            aspect['interpretation'] = aspect_plugin.generate_aspect_interpretation(
                                aspect,
                                chart_data,
                                model_name=params['model_name'],
                                temperature=params['temperature'],
                                max_tokens=params['max_tokens']
                            )
                except Exception as e:
                    logger.error(f"Error generating aspects: {e}")
                    aspect_results = []

            # Plugin integration - House Generator
            house_results = []
            houses_enabled = False
            include_house_planets = False
            houses_enabled = str(data.get('houses_enabled', 'true')).lower() in ['true', '1', 'yes', 'on']
            include_house_planets = str(data.get('include_house_planets', 'true')).lower() in ['true', '1', 'yes', 'on']
            if houses_enabled:
                try:
                    from plugins import get_plugin_manager
                    plugin_manager = get_plugin_manager()
                    house_plugin = plugin_manager.get_plugin('house_generator')
                    if house_plugin:
                        house_results = house_plugin.generate_house_interpretations(
                            chart_data,
                            include_planets=include_house_planets,
                            model_name=params['model_name'],
                            temperature=params['temperature'],
                            max_tokens=params['max_tokens']
                        )
                except Exception as e:
                    logger.error(f"Error generating houses: {e}")
                    house_results = []

            form_data = data

            # Create a unique key for caching
            request_params = json.dumps(sorted(data.items()), sort_keys=True)
            request_hash = hashlib.md5(request_params.encode('utf-8')).hexdigest()
            cache_key = f'chart_results_{request_hash}'

            # Store the new results in the session
            results_to_cache = {
                'chart_data': chart_data,
                'master_interpretation': master_interpretation,
                'planet_interpretations': planet_interpretations,
                'form_data': form_data,
                'aspects': aspect_results,
                'houses': house_results,
            }
            request.session[cache_key] = results_to_cache

            # Return results
            return JsonResponse({
                "success": True,
                "interpretation": {
                    "master": master_interpretation,
                    "planets": planet_interpretations
                },
                "chart_data": chart_data
            })

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON data: {e}")
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON data"
            }, status=400)

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }, status=500)

    else:  # GET request
        aspect_results = []
        house_results = []

        # Check if we have query parameters for displaying results
        if request.GET.get('date') and request.GET.get('time'):
            try:
                # Create a unique key for the current request's parameters to use for caching
                request_params = json.dumps(sorted(request.GET.items()), sort_keys=True)
                request_hash = hashlib.md5(request_params.encode('utf-8')).hexdigest()
                cache_key = f'chart_results_{request_hash}'

                # Check if we have cached results in the session
                cached_results = request.session.get(cache_key)

                if cached_results:
                    logger.info(f"Using cached chart results for key: {cache_key}")
                    chart_data = cached_results['chart_data']
                    master_interpretation = cached_results['master_interpretation']
                    planet_interpretations = cached_results['planet_interpretations']
                    form_data = cached_results['form_data']
                    aspect_results = cached_results.get('aspects', [])
                    house_results = cached_results.get('houses', [])
                else:
                    logger.info(f"No cached results found. Calculating new chart for key: {cache_key}")
                    # Extract parameters from query string
                    data = {
                        'date': request.GET.get('date'),
                        'time': request.GET.get('time'),
                        'latitude': float(request.GET.get('latitude', 0)),
                        'longitude': float(request.GET.get('longitude', 0)),
                        'location': request.GET.get('location', ''),
                        'timezone': request.GET.get('timezone', 'America/Halifax'),
                        'zodiac_type': request.GET.get('zodiac_type', 'tropical'),
                        'house_system': request.GET.get('house_system', 'whole_sign'),
                        'model_name': request.GET.get('model_name', 'gpt-4'),
                        'interpretation_type': request.GET.get('interpretation_type', 'comprehensive'),
                        'temperature': 0.7,
                        'max_tokens': 1000
                    }

                    # Validate input
                    params, error = validate_input(data)
                    if error:
                        return render(request, 'chart_form.html', {
                            'available_models': prompt_manager.get_available_models(),
                            'error_message': error
                        })

                    # Convert to UTC
                    utc_date, utc_time = local_to_utc(
                        params['date'],
                        params['time'],
                        params['timezone_str']
                    )

                    # Calculate chart data
                    chart_data, error = calculate_chart_data_with_caching(
                        utc_date,
                        utc_time,
                        params['latitude'],
                        params['longitude'],
                        params['zodiac_type'],
                        params['house_system'],
                        params['timezone_str']
                    )
                    if error:
                        return render(request, 'chart_form.html', {
                            'available_models': prompt_manager.get_available_models(),
                            'error_message': error
                        })

                    # Generate interpretations
                    planet_interpretations = generate_planet_interpretations_with_caching(
                        chart_data,
                        utc_date,
                        utc_time,
                        params['location'],
                        params['model_name'],
                        params['temperature'],
                        params['max_tokens']
                    )

                    master_interpretation = generate_master_interpretation_with_caching(
                        chart_data,
                        utc_date,
                        utc_time,
                        params['location'],
                        params['model_name'],
                        params['temperature'],
                        params['max_tokens']
                    )

                    # Plugin integration - Aspect Generator
                    aspect_orb = None
                    aspects_enabled = False
                    try:
                        aspect_orb = float(data.get('aspect_orb', 8.0))
                    except Exception:
                        aspect_orb = 8.0
                    aspects_enabled = str(data.get('aspects_enabled', 'true')).lower() in ['true', '1', 'yes', 'on']
                    if aspects_enabled:
                        try:
                            from plugins import get_plugin_manager
                            plugin_manager = get_plugin_manager()
                            aspect_plugin = plugin_manager.get_plugin('aspect_generator')
                            if aspect_plugin:
                                aspect_results = aspect_plugin.calculate_aspects(chart_data, orb=aspect_orb)
                                # Add AI interpretations using the same settings as main chart generation
                                for aspect in aspect_results:
                                    aspect['interpretation'] = aspect_plugin.generate_aspect_interpretation(
                                        aspect,
                                        chart_data,
                                        model_name=params['model_name'],
                                        temperature=params['temperature'],
                                        max_tokens=params['max_tokens']
                                    )
                        except Exception as e:
                            logger.error(f"Error generating aspects: {e}")
                            aspect_results = []

                    # Plugin integration - House Generator
                    houses_enabled = False
                    include_house_planets = False
                    houses_enabled = str(data.get('houses_enabled', 'true')).lower() in ['true', '1', 'yes', 'on']
                    include_house_planets = str(data.get('include_house_planets', 'true')).lower() in ['true', '1', 'yes', 'on']
                    if houses_enabled:
                        try:
                            from plugins import get_plugin_manager
                            plugin_manager = get_plugin_manager()
                            house_plugin = plugin_manager.get_plugin('house_generator')
                            if house_plugin:
                                house_results = house_plugin.generate_house_interpretations(
                                    chart_data,
                                    include_planets=include_house_planets,
                                    model_name=params['model_name'],
                                    temperature=params['temperature'],
                                    max_tokens=params['max_tokens']
                                )
                        except Exception as e:
                            logger.error(f"Error generating houses: {e}")
                            house_results = []

                    form_data = data

                    # Store the new results in the session
                    results_to_cache = {
                        'chart_data': chart_data,
                        'master_interpretation': master_interpretation,
                        'planet_interpretations': planet_interpretations,
                        'form_data': form_data,
                        'aspects': aspect_results,
                        'houses': house_results,
                    }
                    request.session[cache_key] = results_to_cache

                # Return results from cache or new calculation
                return render(request, 'chart_form.html', {
                    'available_models': prompt_manager.get_available_models(),
                    'chart_data': chart_data,
                    'master_interpretation': master_interpretation,
                    'planet_interpretations': planet_interpretations,
                    'form_data': form_data,
                    'aspects': aspect_results,
                    'houses': house_results,
                })

            except Exception as e:
                logger.error(f"Error processing GET request with parameters: {e}")
                return render(request, 'chart_form.html', {
                    'available_models': prompt_manager.get_available_models(),
                    'error_message': f"Error processing request: {str(e)}",
                    'aspects': aspect_results,
                    'houses': house_results,
                })
        else:
            # Regular form display
            available_models = prompt_manager.get_available_models()

            return render(request, 'chart_form.html', {
                'available_models': available_models
            })


@csrf_exempt
@ensure_csrf_cookie
@require_http_methods(["POST"])
def generate_chart(request):
    """
    API endpoint for chart generation with business logic integration.
    """
    try:
        # Check if API key is available
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.error("OpenRouter API key not found in environment variables")
            return JsonResponse({
                "success": False,
                "error": "AI service not configured. Please contact support."
            }, status=500)

        # Check rate limit
        if check_rate_limit(request):
            logger.warning(f"Rate limit exceeded for IP: {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                "success": False,
                "error": "Rate limit exceeded. Please try again later."
            }, status=429)

        # Parse JSON data (not form data)
        data = json.loads(request.body)
        logger.debug(f"Received API request data: {data}")

        # Validate input
        params, error = validate_input(data)
        if error:
            return JsonResponse({"success": False, "error": error}, status=400)

        # Check user limits using business logic
        if request.user.is_authenticated:
            user = request.user
            
            # Check chart generation limits
            if not subscription_logic.check_user_limits(user, 'chart_generation'):
                return JsonResponse({
                    "success": False,
                    "error": "Chart generation limit exceeded",
                    "message": "You have reached your monthly chart generation limit. Please upgrade your plan for unlimited charts."
                }, status=429)

        # Convert to UTC
        utc_date, utc_time = local_to_utc(
            params['date'],
            params['time'],
            params['timezone_str']
        )
        logger.debug(f"Converted to UTC: {utc_date} {utc_time}")

        # Calculate chart data
        chart_data, error = calculate_chart_data_with_caching(
            utc_date,
            utc_time,
            params['latitude'],
            params['longitude'],
            params['zodiac_type'],
            params['house_system'],
            params['timezone_str']
        )
        if error:
            return JsonResponse({"success": False, "error": error}, status=500)
        logger.debug(f"Calculated chart data: {chart_data}")

        # Track chart generation usage
        if request.user.is_authenticated:
            subscription_logic.track_usage(request.user, 'chart_generation')

        # Check interpretation limits before generating
        if request.user.is_authenticated:
            user = request.user
            
            # Check AI interpretation limits
            if not subscription_logic.check_user_limits(user, 'ai_interpretation'):
                return JsonResponse({
                    "success": False,
                    "error": "AI interpretation limit exceeded",
                    "message": "You have reached your monthly AI interpretation limit. Please upgrade your plan for unlimited interpretations."
                }, status=429)

        # Generate interpretations
        logger.debug("Starting planet interpretations generation...")
        planet_interpretations = generate_planet_interpretations_with_caching(
            chart_data,
            utc_date,
            utc_time,
            params['location'],
            params['model_name'],
            params['temperature'],
            params['max_tokens']
        )
        logger.debug("Generated planet interpretations")

        logger.debug("Starting master interpretation generation...")
        master_interpretation = generate_master_interpretation_with_caching(
            chart_data,
            utc_date,
            utc_time,
            params['location'],
            params['model_name'],
            params['temperature'],
            params['max_tokens']
        )
        logger.debug("Generated master interpretation")

        # Track AI interpretation usage
        if request.user.is_authenticated:
            subscription_logic.track_usage(request.user, 'ai_interpretation')

        # Plugin integration - Aspect Generator
        aspect_results = []
        aspect_orb = None
        aspects_enabled = False
        try:
            aspect_orb = float(data.get('aspect_orb', 8.0))
        except Exception:
            aspect_orb = 8.0
        aspects_enabled = str(data.get('aspects_enabled', 'true')).lower() in ['true', '1', 'yes', 'on']
        if aspects_enabled:
            try:
                from plugins import get_plugin_manager
                plugin_manager = get_plugin_manager()
                aspect_plugin = plugin_manager.get_plugin('aspect_generator')
                if aspect_plugin:
                    aspect_results = aspect_plugin.calculate_aspects(chart_data, orb=aspect_orb)
                    # Add AI interpretations using the same settings as main chart generation
                    for aspect in aspect_results:
                        aspect['interpretation'] = aspect_plugin.generate_aspect_interpretation(
                            aspect,
                            chart_data,
                            model_name=params['model_name'],
                            temperature=params['temperature'],
                            max_tokens=params['max_tokens']
                        )
                    logger.debug(f"Generated {len(aspect_results)} aspect interpretations")
            except Exception as e:
                logger.error(f"Error generating aspects: {e}")
                aspect_results = []

        # Plugin integration - House Generator
        house_results = []
        houses_enabled = False
        include_house_planets = False
        houses_enabled = str(data.get('houses_enabled', 'true')).lower() in ['true', '1', 'yes', 'on']
        include_house_planets = str(data.get('include_house_planets', 'true')).lower() in ['true', '1', 'yes', 'on']
        if houses_enabled:
            try:
                from plugins import get_plugin_manager
                plugin_manager = get_plugin_manager()
                house_plugin = plugin_manager.get_plugin('house_generator')
                if house_plugin:
                    house_results = house_plugin.generate_house_interpretations(
                        chart_data,
                        include_planets=include_house_planets,
                        model_name=params['model_name'],
                        temperature=params['temperature'],
                        max_tokens=params['max_tokens']
                    )
                    logger.debug(f"Generated {len(house_results)} house interpretations")
            except Exception as e:
                logger.error(f"Error generating houses: {e}")
                house_results = []

        # Return results
        return JsonResponse({
            "success": True,
            "interpretation": {
                "master": master_interpretation,
                "planets": planet_interpretations
            },
            "chart_data": chart_data,
            "aspects": aspect_results,
            "houses": house_results
        })

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data: {e}")
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON data"
        }, status=400)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }, status=500)


@staff_member_required
def system_dashboard(request):
    health = get_system_health()
    performance = get_performance_summary(60)
    return render(request, 'system_dashboard.html', {
        'health': health,
        'performance': performance
    })
