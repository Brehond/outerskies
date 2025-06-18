import logging
import swisseph as swe
import datetime
from typing import Dict, List, Tuple, Union, Any

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
    Convert date (yyyy-mm-dd) and time (hh:mm) to Julian Day (float).
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        time_str: Time string in HH:MM format
    
    Returns:
        Julian Day as float
    
    Raises:
        ValueError: If date/time format is invalid
    """
    try:
        dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
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
            'placidus': 'P',
            'whole_sign': 'W',
        }
        hs_code = hs_map.get(house_system, 'P')
        houses, ascmc = swe.houses(jd, lat, lon, hs_code.encode('utf-8'))
        asc_long = ascmc[0]
        asc_sign, asc_deg_in_sign = get_sign_from_longitude(asc_long)
        asc = {
            "absolute_degree": asc_long,
            "sign": asc_sign,
            "degree_in_sign": asc_deg_in_sign
        }
        house_signs = {}
        for i, cusp in enumerate(houses):
            sign, _ = get_sign_from_longitude(cusp)
            house_signs[i] = sign
        return asc, houses, house_signs
    except ValueError as e:
        logger.error(f"Invalid house system: {e}")
        raise ValueError(f"Invalid house system: {e}")
    except Exception as e:
        logger.error(f"Error calculating houses: {e}")
        raise Exception(f"Error calculating houses: {e}")

def get_planet_positions(jd: float, lat: float, lon: float, zodiac_type: str = 'tropical') -> Dict[str, Dict[str, Any]]:
    """
    Calculate planetary positions.
    zodiac_type: 'tropical' or 'sidereal'
    """
    try:
        # Set sidereal mode if needed
        if zodiac_type == 'sidereal':
            swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
            flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
        else:
            swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY, 0, 0)  # Reset to default
            flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        positions = {}
        for planet, code in PLANET_CODES.items():
            pos, _ = swe.calc_ut(jd, code, flags)
            longitude = pos[0]
            sign, deg_in_sign = get_sign_from_longitude(longitude)
            retrograde = pos[3] < 0
            positions[planet] = {
                "absolute_degree": longitude,
                "sign": sign,
                "degree": deg_in_sign,  # Changed from degree_in_sign to match prompt
                "retrograde": retrograde,
                "house": 1  # Default to house 1, will be calculated later
            }
        # Calculate aspects
        aspects = calculate_aspects(positions)
        # Add aspects and dignity to each planet's data
        for planet, pos in positions.items():
            pos["aspects"] = aspects[planet]
            pos["dignity"] = calculate_dignity(planet, pos["sign"])
        return positions
    except Exception as e:
        logger.error(f"Error calculating planet positions: {e}")
        raise Exception(f"Error calculating planet positions: {e}")

def get_chart_data(
    date: str,
    time: str,
    lat: float,
    lon: float
) -> Dict[str, Any]:
    """
    Calculate complete chart data.
    
    Args:
        date: Date string in YYYY-MM-DD format
        time: Time string in HH:MM format
        lat: Latitude in degrees
        lon: Longitude in degrees
    
    Returns:
        Dict containing all chart data
    
    Raises:
        ValueError: If date/time format is invalid
        Exception: For Swiss Ephemeris calculation errors
    """
    try:
        jd = get_julian_day(date, time)
        positions = get_planet_positions(jd, lat, lon)
        asc, houses, house_signs = get_ascendant_and_houses(jd, lat, lon)
        
        # Calculate houses for each planet
        asc_sign_index = SIGN_NAMES.index(asc["sign"])
        for planet, pos in positions.items():
            sign_index = SIGN_NAMES.index(pos["sign"])
            house = ((sign_index - asc_sign_index) % 12) + 1
            pos["house"] = house
        
        return {
            "julian_day": jd,
            "positions": positions,
            "ascendant": asc,
            "houses": houses,
            "house_signs": house_signs
        }
    except Exception as e:
        logger.error(f"Error calculating chart data: {e}")
        raise Exception(f"Error calculating chart data: {e}")

