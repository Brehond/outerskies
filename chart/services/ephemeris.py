import swisseph as swe
import datetime
import math

# Zodiac sign names, in order
SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

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

def get_julian_day(date_str, time_str):
    """
    Convert a date (YYYY-MM-DD) and time (HH:MM) to Julian Day in Universal Time.
    """
    year, month, day = map(int, date_str.split('-'))
    hour, minute = map(int, time_str.split(':'))
    ut = hour + minute / 60.0
    jd = swe.julday(year, month, day, ut)
    return jd

def get_planet_positions(jd, lat, lon):
    """
    Return a dict of planetary ecliptic longitudes at the given Julian Day and observer location.
    """
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    positions = {}
    observer = (lon, lat, 0)  # longitude, latitude, altitude
    for planet, code in PLANET_CODES.items():
        pos, _ = swe.calc_ut(jd, code, flags)
        positions[planet] = pos[0]  # ecliptic longitude
    return positions

def get_ascendant(jd, lat, lon):
    """
    Calculate the Ascendant (rising sign) in degrees.
    """
    # swe_houses returns (cusps, ascmc)
    # ascmc[0] is Ascendant
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')  # Placidus system; can use 'W' for Whole Sign
    asc = ascmc[0]  # Ascendant in degrees (0-360)
    return asc

def get_ascendant_sign(asc):
    """
    Given an ascendant in degrees, return the sign name.
    """
    sign_index = int(asc // 30) % 12
    return SIGN_NAMES[sign_index]

def get_whole_sign_houses(asc, positions):
    """
    Given Ascendant degrees and planet positions, return dict of house -> sign.
    Uses the Whole Sign Houses system (first house starts at 0 deg of ascendant's sign).
    """
    houses = {}
    asc_sign_index = int(asc // 30) % 12
    for i in range(12):
        house_num = i + 1
        sign_index = (asc_sign_index + i) % 12
        houses[house_num] = SIGN_NAMES[sign_index]
    return houses

def get_ascendant_and_houses(jd, lat, lon, planet_positions=None):
    """
    Returns: ascendant degree, list of house cusp degrees, dict of house_num -> sign_name (whole sign)
    """
    asc = get_ascendant(jd, lat, lon)
    if planet_positions is None:
        planet_positions = {}
    houses = get_whole_sign_houses(asc, planet_positions)
    # For debugging: Calculate actual house cusp degrees
    cusps, _ = swe.houses(jd, lat, lon, b'P')  # Placidus cusps (could use for comparison)
    house_cusps = list(cusps)  # List of 12 house cusp degrees
    return asc, house_cusps, houses

def get_sign_from_longitude(longitude):
    """
    Convert an ecliptic longitude (0-360) to a sign name and degree within sign.
    """
    sign_index = int(longitude // 30) % 12
    sign_name = SIGN_NAMES[sign_index]
    deg_in_sign = longitude % 30
    return sign_name, deg_in_sign

# Optional: function to produce chart summary/debug
def get_chart_data(date_str, time_str, lat, lon):
    jd = get_julian_day(date_str, time_str)
    positions = get_planet_positions(jd, lat, lon)
    asc, house_cusps, house_signs = get_ascendant_and_houses(jd, lat, lon, positions)
    asc_sign = get_ascendant_sign(asc)
    planet_signs = {}
    for planet, pos in positions.items():
        sign_name, deg_in_sign = get_sign_from_longitude(pos)
        planet_signs[planet] = {'sign': sign_name, 'deg': deg_in_sign}
    return {
        "jd": jd,
        "ascendant": asc,
        "asc_sign": asc_sign,
        "house_cusps": house_cusps,
        "house_signs": house_signs,
        "planet_positions": positions,
        "planet_signs": planet_signs,
    }
