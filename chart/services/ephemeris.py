import logging
import swisseph as swe
import datetime
from typing import Dict, List, Tuple, Union, Any
from .caching import ephemeris_cache

logger = logging.getLogger(__name__)

# Define planet code mapping (Sun=0, Moon=1, etc. as per Swiss Ephemeris)
PLANET_CODES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Define aspect orbs (in degrees)
ASPECT_ORBS = {
    "Conjunction": 10,
    "Opposition": 10,
    "Trine": 10,
    "Square": 8,
    "Sextile": 6,
    "Quincunx": 3
}

# Define dignity rulerships
DIGNITY_RULERSHIPS = {
    "Sun": {"Ruler": "Leo", "Exaltation": "Aries", "Fall": "Libra", "Detriment": "Aquarius"},
    "Moon": {"Ruler": "Cancer", "Exaltation": "Taurus", "Fall": "Scorpio", "Detriment": "Capricorn"},
    "Mercury": {"Ruler": ["Gemini", "Virgo"], "Exaltation": "Virgo", "Fall": "Pisces", "Detriment": ["Sagittarius", "Pisces"]},
    "Venus": {"Ruler": ["Taurus", "Libra"], "Exaltation": "Pisces", "Fall": "Virgo", "Detriment": ["Aries", "Scorpio"]},
    "Mars": {"Ruler": ["Aries", "Scorpio"], "Exaltation": "Capricorn", "Fall": "Cancer", "Detriment": ["Taurus", "Libra"]},
    "Jupiter": {"Ruler": ["Sagittarius", "Pisces"], "Exaltation": "Cancer", "Fall": "Capricorn", "Detriment": ["Gemini", "Virgo"]},
    "Saturn": {"Ruler": ["Capricorn", "Aquarius"], "Exaltation": "Libra", "Fall": "Aries", "Detriment": ["Cancer", "Leo"]},
    "Uranus": {"Ruler": "Aquarius", "Exaltation": "Scorpio", "Fall": "Taurus", "Detriment": "Leo"},
    "Neptune": {"Ruler": "Pisces", "Exaltation": "Cancer", "Fall": "Capricorn", "Detriment": "Virgo"},
    "Pluto": {"Ruler": "Scorpio", "Exaltation": "Aries", "Fall": "Libra", "Detriment": "Taurus"}
}


def get_julian_day(date_str: str, time_str: str) -> float:
    """
    Convert date (yyyy-mm-dd) and time (hh:mm or hh:mm:ss) to Julian Day (float).

    Args:
        date_str: Date string in YYYY-MM-DD format
        time_str: Time string in HH:MM or HH:MM:SS format

    Returns:
        Julian Day as float

    Raises:
        ValueError: If date/time format is invalid
    """
    try:
        # Clean up time string - remove any trailing :00 if present
        cleaned_time = time_str.rstrip(':00')
        
        # Try different time formats
        time_formats = ['%H:%M:%S', '%H:%M']
        dt = None
        
        for fmt in time_formats:
            try:
                dt = datetime.datetime.strptime(f"{date_str} {cleaned_time}", f"%Y-%m-%d {fmt}")
                break
            except ValueError:
                continue
        
        if dt is None:
            raise ValueError(f"Invalid time format: {time_str}. Use HH:MM or HH:MM:SS")
        
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)
    except ValueError as e:
        logger.error(f"Invalid date/time format: {e}")
        raise ValueError(f"Invalid date/time format: {e}")


def get_sign_from_longitude(longitude: float) -> Tuple[str, float]:
    """
    Convert ecliptic longitude to (sign, degree_in_sign)

    Args:
        longitude: Ecliptic longitude in degrees

    Returns:
        Tuple of (sign name, degree within sign)
    """
    sign_index = int(longitude // 30) % 12
    deg_in_sign = longitude % 30
    return SIGN_NAMES[sign_index], deg_in_sign


def calculate_aspects(positions: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Calculate aspects between planets.

    Args:
        positions: Dict of planet positions

    Returns:
        Dict mapping planets to their aspects
    """
    aspects = {}

    for planet1, pos1 in positions.items():
        aspects[planet1] = []
        for planet2, pos2 in positions.items():
            if planet1 != planet2:
                diff = abs(pos1["absolute_degree"] - pos2["absolute_degree"])
                if diff > 180:
                    diff = 360 - diff

                # Check for aspects
                if diff <= ASPECT_ORBS["Conjunction"]:
                    aspects[planet1].append({
                        "planet": planet2,
                        "type": "Conjunction",
                        "orb": diff
                    })
                elif abs(diff - 180) <= ASPECT_ORBS["Opposition"]:
                    aspects[planet1].append({
                        "planet": planet2,
                        "type": "Opposition",
                        "orb": abs(diff - 180)
                    })
                elif abs(diff - 120) <= ASPECT_ORBS["Trine"]:
                    aspects[planet1].append({
                        "planet": planet2,
                        "type": "Trine",
                        "orb": abs(diff - 120)
                    })
                elif abs(diff - 90) <= ASPECT_ORBS["Square"]:
                    aspects[planet1].append({
                        "planet": planet2,
                        "type": "Square",
                        "orb": abs(diff - 90)
                    })
                elif abs(diff - 60) <= ASPECT_ORBS["Sextile"]:
                    aspects[planet1].append({
                        "planet": planet2,
                        "type": "Sextile",
                        "orb": abs(diff - 60)
                    })
                elif abs(diff - 150) <= ASPECT_ORBS["Quincunx"]:
                    aspects[planet1].append({
                        "planet": planet2,
                        "type": "Quincunx",
                        "orb": abs(diff - 150)
                    })

    return aspects


def calculate_dignity(planet: str, sign: str) -> str:
    """
    Calculate dignity status for a planet in a sign.

    Args:
        planet: Planet name
        sign: Sign name

    Returns:
        Dignity status string
    """
    dignities = DIGNITY_RULERSHIPS.get(planet, {})

    if isinstance(dignities.get("Ruler"), list):
        if sign in dignities["Ruler"]:
            return "Ruler"
    elif sign == dignities.get("Ruler"):
        return "Ruler"

    if sign == dignities.get("Exaltation"):
        return "Exaltation"

    if isinstance(dignities.get("Detriment"), list):
        if sign in dignities["Detriment"]:
            return "Detriment"
    elif sign == dignities.get("Detriment"):
        return "Detriment"

    if sign == dignities.get("Fall"):
        return "Fall"

    return "Neutral"


def get_ascendant_and_houses(
    jd: float,
    lat: float,
    lon: float,
    house_system: str = "W"
) -> Tuple[Dict[str, Any], List[float], Dict[int, str]]:
    """
    Calculate ascendant and house cusps.
    house_system: 'P' for Placidus, 'W' for Whole Sign, etc.
    """
    try:
        # Map user-friendly names to Swiss Ephemeris codes
        hs_map = {
            'placidus': b'P',
            'whole_sign': b'W',
        }
        hs_code = hs_map.get(house_system, b'P')
        logger.info(f"Calling swe.houses with jd={jd}, lat={lat}, lon={lon}, house_system={house_system} (code={hs_code})")
        houses, ascmc = swe.houses(jd, lat, lon, hs_code)
        logger.info(f"swe.houses returned houses={houses}, ascmc={ascmc}")
        # Validate that we got valid house data
        if not houses or len(houses) < 12:
            logger.error(f"Invalid house cusps data: {houses} (jd={jd}, lat={lat}, lon={lon}, house_system={house_system})")
            logger.error(f"houses type: {type(houses)}, length: {len(houses) if houses else 'None'}")
            raise ValueError("Invalid house cusps data")

        logger.info(f"House cusps validation passed. First 12 cusps: {houses[:12]}")

        asc_long = ascmc[0]
        asc_sign, asc_deg_in_sign = get_sign_from_longitude(asc_long)
        asc = {
            "absolute_degree": asc_long,
            "sign": asc_sign,
            "degree_in_sign": asc_deg_in_sign
        }

        # Create house signs dictionary (1-indexed to match astrological convention)
        house_signs = {}
        for i in range(12):  # Houses 1-12 (0-indexed in array)
            cusp = houses[i]
            sign, _ = get_sign_from_longitude(cusp)
            house_signs[i + 1] = sign  # Convert to 1-indexed

        return asc, houses, house_signs
    except ValueError as e:
        logger.error(f"Invalid house system: {e}")
        raise ValueError(f"Invalid house system: {e}")
    except Exception as e:
        logger.error(f"Error calculating houses: {e}")
        raise Exception(f"Error calculating houses: {e}")


def get_planet_positions(jd: float, lat: float, lon: float, zodiac_type: str = 'tropical', house_system: str = 'placidus') -> Dict[str, Dict[str, Any]]:
    """
    Get planetary positions with caching support.

    Args:
        jd: Julian Day
        lat: Latitude
        lon: Longitude
        zodiac_type: 'tropical' or 'sidereal'
        house_system: House system to use for house position calculation

    Returns:
        Dict of planetary positions
    """
    positions = {}

    # Map user-friendly house system names to Swiss Ephemeris codes (same as get_ascendant_and_houses)
    hs_map = {
        'placidus': b'P',
        'whole_sign': b'W',
    }
    hs_code = hs_map.get(house_system, b'P')

    # Calculate houses first to get house cusps for house position calculation
    try:
        houses, ascmc = swe.houses(jd, lat, lon, hs_code)
        armc = ascmc[2]  # Right Ascension of Medium Coeli
        eps = 23.4367  # Use standard mean obliquity of the ecliptic
        logger.debug(f"Successfully calculated houses: {houses[:12]}")  # Log first 12 house cusps
    except Exception as e:
        logger.error(f"Error calculating houses for house positions: {e}")
        # Fallback to default values
        armc = 0
        eps = 23.4367
        houses = None

    for planet_name, planet_code in PLANET_CODES.items():
        try:
            # Get planet position
            result = swe.calc_ut(jd, planet_code)
            longitude = result[0][0]
            latitude = result[0][1]
            distance = result[0][2]

            # Convert to sign and degree
            sign, deg_in_sign = get_sign_from_longitude(longitude)

            # Calculate dignity
            dignity = calculate_dignity(planet_name, sign)

            # Calculate house position using swe_house_pos
            try:
                house_position = swe.house_pos(armc, lat, eps, [longitude, latitude], hs_code)
                house_number = int(house_position)
                if house_number < 1:
                    house_number = 1
                elif house_number > 12:
                    house_number = 12
                logger.debug(f"Calculated house position for {planet_name}: {house_position:.2f} (House {house_number})")
            except Exception as e:
                logger.warning(f"Error calculating house position for {planet_name}: {e}")
                logger.warning(f"Parameters: armc={armc}, lat={lat}, eps={eps}, hs_code={hs_code}, pos=[{longitude}, {latitude}]")
                # Try to calculate house manually using house cusps as fallback
                try:
                    if houses is not None and len(houses) >= 12:
                        # Find which house the planet falls into
                        house_number = 1  # Default to house 1
                        for i in range(12):
                            cusp1 = houses[i]
                            cusp2 = houses[(i + 1) % 12] if i < 11 else houses[0] + 360
                            if i == 11 and cusp2 < cusp1:
                                cusp2 += 360
                            if cusp1 <= longitude < cusp2 or (i == 11 and longitude >= cusp1):
                                house_number = i + 1
                                break
                        logger.info(f"Fallback house calculation for {planet_name}: House {house_number} (longitude: {longitude:.2f}°, cusps: {houses[:12]})")
                    else:
                        logger.warning(f"No house cusps available for fallback calculation for {planet_name}")
                        house_number = 1
                except Exception as fallback_error:
                    logger.error(f"Fallback house calculation also failed for {planet_name}: {fallback_error}")
                    house_number = 1

            positions[planet_name] = {
                "absolute_degree": longitude,
                "latitude": latitude,
                "distance": distance,
                "sign": sign,
                "degree_in_sign": deg_in_sign,
                "dignity": dignity,
                "house": house_number,
                "retrograde": result[0][3] < 0  # Negative speed indicates retrograde
            }

        except Exception as e:
            logger.error(f"Error calculating position for {planet_name}: {e}")
            positions[planet_name] = {
                "error": str(e),
                "absolute_degree": 0,
                "sign": "Unknown",
                "degree_in_sign": 0,
                "house": 1
            }

    return positions


def get_chart_data(
    date: str,
    time: str,
    lat: float,
    lon: float,
    timezone: str = "UTC",
    zodiac_type: str = "tropical",
    house_system: str = "placidus"
) -> Dict[str, Any]:
    """
    Get complete chart data with caching support.

    Args:
        date: Date string in YYYY-MM-DD format
        time: Time string in HH:MM format
        lat: Latitude
        lon: Longitude
        timezone: Timezone string
        zodiac_type: 'tropical' or 'sidereal'
        house_system: 'placidus' or 'whole_sign'

    Returns:
        Complete chart data dictionary
    """
    # Create birth data for caching
    birth_data = {
        'date': date,
        'time': time,
        'latitude': lat,
        'longitude': lon,
        'timezone': timezone,
        'zodiac_type': zodiac_type,
        'house_system': house_system
    }

    # Try to get from cache first
    cached_result = ephemeris_cache.get_ephemeris_calculation(birth_data)
    if cached_result:
        logger.info(f"Using cached ephemeris data for {date} {time}")
        return cached_result

    # Calculate if not in cache
    logger.info(f"Calculating ephemeris data for {date} {time}")

    try:
        # Convert to Julian Day
        jd = get_julian_day(date, time)

        # Get planetary positions
        planetary_positions = get_planet_positions(jd, lat, lon, zodiac_type, house_system)

        # Get ascendant and houses
        ascendant, house_cusps, house_signs = get_ascendant_and_houses(jd, lat, lon, house_system)

        # Calculate aspects
        aspects = calculate_aspects(planetary_positions)

        # Add aspects to planetary positions for easier access in interpretations
        for planet_name, planet_data in planetary_positions.items():
            if planet_name in aspects:
                planet_data['aspects'] = aspects[planet_name]
            else:
                planet_data['aspects'] = []

        # Compile complete chart data
        chart_data = {
            "julian_day": jd,
            "birth_data": birth_data,
            "planetary_positions": planetary_positions,
            "ascendant": ascendant,
            "house_cusps": house_cusps,
            "house_signs": house_signs,
            "aspects": aspects,
            "calculated_at": datetime.datetime.now().isoformat(),
            "zodiac_type": zodiac_type,
            "house_system": house_system
        }

        # Cache the result
        ephemeris_cache.cache_ephemeris_calculation(birth_data, chart_data)

        return chart_data

    except Exception as e:
        logger.error(f"Error calculating chart data: {e}")
        raise
