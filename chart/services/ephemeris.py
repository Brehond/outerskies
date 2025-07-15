"""
DEPRECATED: This module is now a thin wrapper around the new service architecture.
All core logic has been moved to chart/services/planetary_calculator.py, house_calculator.py, aspect_calculator.py, dignity_calculator.py, caching_service.py, and chart_orchestrator.py.

Use ChartOrchestrator for all new chart calculations.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Union

from .chart_orchestrator import ChartOrchestrator

logger = logging.getLogger(__name__)

# --- Deprecated Utility Functions (kept for backward compatibility) ---

def get_julian_day(date_str: str, time_str: str) -> float:
    """
    Convert date (yyyy-mm-dd) and time (hh:mm or hh:mm:ss) to Julian Day (float).
    """
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    from swisseph import julday
    return julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0 + dt.second / 3600.0)

# --- New Delegation Functions ---

orchestrator = ChartOrchestrator()

def get_planet_positions(jd: float) -> Dict[str, Any]:
    """
    Get planetary positions for a given Julian Day.
    Delegates to PlanetaryCalculator.
    """
    return orchestrator._calculate_planetary_positions(jd)

def get_ascendant_and_houses(jd: float, lat: float, lon: float, house_system: str = "Placidus") -> Dict[str, Any]:
    """
    Get house cusps and ascendant for a given Julian Day and location.
    Delegates to HouseCalculator.
    """
    return orchestrator._calculate_houses(jd, lat, lon, house_system)

def get_chart_data(date: str, time: str, lat: float, lon: float, timezone: str = "UTC", zodiac_type: str = "tropical", house_system: str = "Placidus") -> Dict[str, Any]:
    """
    Get a complete chart for the given birth data.
    Delegates to ChartOrchestrator.
    """
    # Parse datetime
    try:
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    return orchestrator.calculate_complete_chart(dt, lat, lon, house_system=house_system)

# --- Deprecated: All other logic has been removed. Use the new services. ---
