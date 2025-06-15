import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from chart.prompts import PLANETARY_PROMPTS, MASTER_CHART_PROMPT
from chart.services import ephemeris
from chart.services import openrouter_api

@csrf_exempt
def chart_form(request):
    if request.method == 'GET':
        return render(request, 'chart_form.html')

@csrf_exempt
def generate_chart(request):
    if request.method == 'GET':
        date = request.GET.get('date')
        time = request.GET.get('time')
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
        location = request.GET.get('location', '')

        # Calculate Julian Day
        jd = ephemeris.get_julian_day(date, time)

        # Get planet positions AND ascendant/house cusps/signs
        positions = ephemeris.get_planet_positions(jd, lat, lon)
        asc, houses, house_signs = ephemeris.get_ascendant_and_houses(jd, lat, lon)

        planet_results = {}

        # Ascendant sign and index for whole sign calculation
        asc_sign = asc["sign"] if isinstance(asc, dict) else ""
        asc_sign_index = ephemeris.SIGN_NAMES.index(asc_sign) if asc_sign in ephemeris.SIGN_NAMES else 0

        for planet, pos in positions.items():
            if isinstance(pos, dict):
                abs_degree = pos.get("absolute_degree", 0.0)
                sign = pos.get("sign", "")
                degree_in_sign = pos.get("degree_in_sign", 0.0)
            else:
                abs_degree = pos
                sign = ""
                degree_in_sign = 0.0

            # Whole sign house calculation
            sign_index = ephemeris.SIGN_NAMES.index(sign) if sign in ephemeris.SIGN_NAMES else 0
            house = ((int(abs_degree) // 30 - asc_sign_index) % 12) + 1

            prompt_template = PLANETARY_PROMPTS.get(planet)
            if not prompt_template:
                continue

            # Fill all possible template variables, use safe .format()
            try:
                prompt = prompt_template.format(
                    date=date,
                    time=time,
                    location=location,
                    abs_degree=abs_degree,
                    sign=sign,
                    degree_in_sign=degree_in_sign,
                    house=house,
                    position=abs_degree  # legacy key for backward compatibility
                )
            except KeyError as e:
                prompt = f"[ERROR: Missing variable {e.args[0]} in prompt template for {planet}]"

            interpretation = openrouter_api.generate_interpretation(prompt)
            planet_results[planet] = {
                "absolute_degree": abs_degree,
                "sign": sign,
                "degree_in_sign": degree_in_sign,
                "house": house,
                "interpretation": interpretation
            }

        # Add ascendant and house info to output
        houses_out = []
        for i, cusp in enumerate(houses):
            sign = house_signs.get(i, "") if isinstance(house_signs, dict) else (house_signs[i] if len(house_signs) > i else "")
            houses_out.append({
                "house": i + 1,
                "cusp_degree": cusp,
                "sign": sign
            })

        asc_info = {
            "absolute_degree": asc.get("absolute_degree", 0.0) if isinstance(asc, dict) else 0.0,
            "sign": asc.get("sign", "") if isinstance(asc, dict) else "",
            "degree_in_sign": asc.get("degree_in_sign", 0.0) if isinstance(asc, dict) else 0.0
        }

        # Ensure SYNTHESIS_CORE_END is defined to prevent KeyError
        master_prompt_kwargs = {
            "date": date,
            "time": time,
            "location": location,
            "chart": planet_results,
            "SYNTHESIS_CORE_END": ""
        }

        try:
            chart_summary = openrouter_api.generate_interpretation(
                MASTER_CHART_PROMPT.format(**master_prompt_kwargs)
            )
        except KeyError as e:
            chart_summary = f"[ERROR: Missing variable {e.args[0]} in MASTER_CHART_PROMPT]"

        return JsonResponse({
            "julian_day": jd,
            "ascendant": asc_info,
            "houses": houses_out,
            "chart": planet_results,
            "chart_summary": chart_summary,
        })
