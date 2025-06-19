import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from .services.ephemeris import (
    get_julian_day,
    get_planet_positions,
    get_ascendant_and_houses,
    SIGN_NAMES
)
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
        time_str: Time string in HH:MM format
        tz_str: Timezone string (e.g., 'America/New_York')
    
    Returns:
        Tuple of (UTC date string, UTC time string)
    
    Raises:
        ValueError: If date/time format is invalid
        pytz.exceptions.UnknownTimeZoneError: If timezone is invalid
    """
    try:
        local_tz = pytz.timezone(tz_str)
        naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
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
                
        # Date validation
        try:
            datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            return {}, "Invalid date format. Use YYYY-MM-DD"
            
        # Time validation
        try:
            datetime.strptime(data['time'], '%H:%M')
        except ValueError:
            return {}, "Invalid time format. Use HH:MM"
            
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
            'time': data['time'],
            'latitude': lat,
            'longitude': lon,
            'location': data.get('location', f"{lat}, {lon}"),
            'timezone_str': timezone_str,
            'zodiac_type': data['zodiac_type'],
            'house_system': data['house_system'],
            'model_name': data['model_name'],
            'temperature': temp,
            'max_tokens': tokens
        }, None
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return {}, f"Validation error: {str(e)}"

def calculate_chart_data(utc_date: str, utc_time: str, lat: float, lon: float, zodiac_type: str, house_system: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Calculate chart data using ephemeris.
    
    Returns:
        Tuple of (chart data dict, error message if any)
    """
    try:
        jd = get_julian_day(utc_date, utc_time)
        positions = get_planet_positions(jd, lat, lon, zodiac_type=zodiac_type)
        asc, houses, house_signs = get_ascendant_and_houses(jd, lat, lon, house_system=house_system)

        return {
            'julian_day': jd,
            'positions': positions,
            'ascendant': asc,
            'houses': houses,
            'house_signs': house_signs,
            'birth_date': utc_date,
            'birth_time': utc_time,
            'location': lon
        }, None
    except Exception as e:
        logger.error(f"Chart calculation failed: {e}")
        return {}, f"Chart calculation failed: {str(e)}"

def generate_planet_interpretations(
    chart_data: Dict[str, Any],
    utc_date: str,
    utc_time: str,
    location: str,
    model_name: str,
    temperature: float,
    max_tokens: int
) -> Dict[str, str]:
    """
    Generate interpretations for each planet.
    """
    planet_results = {}
    asc_sign = chart_data['ascendant'].get("sign", "")
    asc_sign_index = SIGN_NAMES.index(asc_sign) if asc_sign in SIGN_NAMES else 0

    for planet, pos in chart_data['positions'].items():
        try:
            logger.debug(f"Generating interpretation for {planet}...")
            # Extract position data
            abs_degree = pos.get("absolute_degree", 0.0)
            sign = pos.get("sign", "")
            degree_in_sign = pos.get("degree_in_sign", 0.0)
            retrograde_status = pos.get("retrograde", "")
            
            # Calculate house
            sign_index = SIGN_NAMES.index(sign) if sign in SIGN_NAMES else 0
            house = ((int(abs_degree) // 30 - asc_sign_index) % 12) + 1

            # Get and format prompt
            prompt_template = prompt_manager.get_planet_prompt(planet)
            if not prompt_template:
                logger.warning(f"No prompt template found for {planet}")
                continue

            prompt = prompt_template.format(
                date=utc_date,
                time=utc_time,
                location=location,
                sign=sign,
                house=house,
                position=abs_degree,
                retrograde_status=retrograde_status,
                aspect_summary="",  # TODO: Add aspect calculation
                dignity_status=""   # TODO: Add dignity calculation
            )

            logger.debug(f"Calling AI for {planet} with model {model_name}...")
            # Generate interpretation
            interpretation = generate_interpretation(
                prompt,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            planet_results[planet] = interpretation
            logger.debug(f"Successfully generated interpretation for {planet}")
            
        except Exception as e:
            logger.error(f"Error generating interpretation for {planet}: {e}")
            planet_results[planet] = f"Failed to generate interpretation: {str(e)}"

    return planet_results

def generate_master_interpretation(
    chart_data: Dict[str, Any],
    utc_date: str,
    utc_time: str,
    location: str,
    model_name: str,
    temperature: float,
    max_tokens: int
) -> str:
    """
    Generate master chart interpretation.
    """
    try:
        # Extract planetary positions
        positions = chart_data['positions']
        ascendant = chart_data['ascendant']
        houses = chart_data['houses']
        
        # Format planetary positions
        planet_data = {}
        for planet in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']:
            pos = positions.get(planet, {})
            sign = pos.get('sign', '')
            house = pos.get('house', 1)
            planet_data[f'{planet.lower()}_sign'] = sign
            planet_data[f'{planet.lower()}_house'] = house
        
        # Format ascendant and midheaven
        asc_sign = ascendant.get('sign', '')
        asc_degree = ascendant.get('degree_in_sign', 0)
        
        # Compute MC from the 10th house cusp (index 9)
        mc_degree = houses[9]
        mc_sign = chart_data['house_signs'][9]
        
        # Format aspects and dignities (placeholders for now)
        aspects = "No major aspects"  # TODO: Add aspect calculation
        dignities = "No special dignities"  # TODO: Add dignity calculation
        
        # Prepare all required keys for the master prompt
        master_prompt_data = {
            'date': utc_date,
            'time': utc_time,
            'location': location,
            'sun_sign': planet_data['sun_sign'],
            'sun_house': planet_data['sun_house'],
            'moon_sign': planet_data['moon_sign'],
            'moon_house': planet_data['moon_house'],
            'mercury_sign': planet_data['mercury_sign'],
            'mercury_house': planet_data['mercury_house'],
            'venus_sign': planet_data['venus_sign'],
            'venus_house': planet_data['venus_house'],
            'mars_sign': planet_data['mars_sign'],
            'mars_house': planet_data['mars_house'],
            'jupiter_sign': planet_data['jupiter_sign'],
            'jupiter_house': planet_data['jupiter_house'],
            'saturn_sign': planet_data['saturn_sign'],
            'saturn_house': planet_data['saturn_house'],
            'uranus_sign': planet_data['uranus_sign'],
            'uranus_house': planet_data['uranus_house'],
            'neptune_sign': planet_data['neptune_sign'],
            'neptune_house': planet_data['neptune_house'],
            'pluto_sign': planet_data['pluto_sign'],
            'pluto_house': planet_data['pluto_house'],
            'ascendant': f"{asc_sign} {asc_degree}°",
            'midheaven': f"{mc_sign} {mc_degree}°",
            'aspects': aspects,
            'dignities': dignities
        }

        # Debug log all master prompt data
        logger.debug(f"Master prompt data: {master_prompt_data}")

        # Check for missing or None values
        missing_keys = [k for k, v in master_prompt_data.items() if v is None or v == '']
        if missing_keys:
            logger.error(f"Missing or empty values for master prompt: {missing_keys}")
            return f"Failed to generate master interpretation: Missing or empty values for {', '.join(missing_keys)}"

        # Format chart data into prompt
        prompt = prompt_manager.format_master_prompt(**master_prompt_data)
        
        if not prompt:
            raise ValueError("Failed to format master prompt")
        
        logger.debug(f"Calling AI for master interpretation with model {model_name}...")
        # Generate interpretation
        result = generate_interpretation(
            prompt,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        logger.debug("Successfully generated master interpretation")
        return result
        
    except Exception as e:
        logger.error(f"Error generating master interpretation: {e}")
        return f"Failed to generate master interpretation: {str(e)}"

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
            chart_data, error = calculate_chart_data(
                utc_date,
                utc_time,
                params['latitude'],
                params['longitude'],
                params['zodiac_type'],
                params['house_system']
            )
            if error:
                return JsonResponse({"success": False, "error": error}, status=500)
            logger.debug(f"Calculated chart data: {chart_data}")
            
            # Generate interpretations
            logger.debug("Starting planet interpretations generation...")
            planet_interpretations = generate_planet_interpretations(
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
            master_interpretation = generate_master_interpretation(
                chart_data,
                utc_date,
                utc_time,
                params['location'],
                params['model_name'],
                params['temperature'],
                params['max_tokens']
            )
            logger.debug("Generated master interpretation")
            
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
        # Get available models
        available_models = prompt_manager.get_available_models()
        
        return render(request, 'chart_form.html', {
            'available_models': available_models
        })

@ensure_csrf_cookie
@require_http_methods(["POST"])
def generate_chart(request):
    """
    API endpoint for chart generation.
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
            
        # Convert to UTC
        utc_date, utc_time = local_to_utc(
            params['date'],
            params['time'],
            params['timezone_str']
        )
        logger.debug(f"Converted to UTC: {utc_date} {utc_time}")
        
        # Calculate chart data
        chart_data, error = calculate_chart_data(
            utc_date,
            utc_time,
            params['latitude'],
            params['longitude'],
            params['zodiac_type'],
            params['house_system']
        )
        if error:
            return JsonResponse({"success": False, "error": error}, status=500)
        logger.debug(f"Calculated chart data: {chart_data}")
        
        # Generate interpretations
        logger.debug("Starting planet interpretations generation...")
        planet_interpretations = generate_planet_interpretations(
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
        master_interpretation = generate_master_interpretation(
            chart_data,
            utc_date,
            utc_time,
            params['location'],
            params['model_name'],
            params['temperature'],
            params['max_tokens']
        )
        logger.debug("Generated master interpretation")
        
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
