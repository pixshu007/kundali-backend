from flask import Flask, request, jsonify, url_for
from flask_cors import CORS
import swisseph as swe
from datetime import datetime, timedelta, timezone
from geopy.geocoders import Nominatim
import matplotlib
matplotlib.use('Agg')  # Use Agg backend for non-GUI environments
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os
import time
import logging
import json
import re
import math

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

swe.set_sid_mode(swe.SIDM_LAHIRI)
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://astrologerinranchi.com"}}, supports_credentials=True)

# Geolocation cache
geolocation_cache = {}

@app.route('/kundali', methods=['OPTIONS'])
def handle_options():
    response = jsonify({"status": "ok"})
    response.headers['Access-Control-Allow-Origin'] = 'https://astrologerinranchi.com'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

STATIC_FOLDER = "static"

def sanitize_filename(filename):
    invalid_chars = r'[<>:"/\\|?*]+'
    sanitized = re.sub(invalid_chars, '-', filename)
    sanitized = sanitized.strip().strip('.')
    return sanitized

# Define planet symbols and their colors
planet_symbols = {
    "सूर्य": ("सु", "darkred"),
    "चंद्र": ("च", "navy"),
    "मंगल": ("मं", "darkorange"),
    "बुध": ("बु", "forestgreen"),
    "बृहस्पति": ("गु", "darkgoldenrod"),
    "शुक्र": ("शु", "magenta"),
    "शनि": ("श", "darkslategray"),
    "राहु": ("रा", "purple"),
    "केतु": ("के", "teal")
}

# Rashi lord mapping
rashi_lord = {
    "मेष": "मंगल",
    "वृष": "शुक्र",
    "मिथुन": "बुध",
    "कर्क": "चंद्र",
    "सिंह": "सूर्य",
    "कन्या": "बुध",
    "तुला": "शुक्र",
    "वृश्चिक": "मंगल",
    "धनु": "बृहस्पति",
    "मकर": "शनि",
    "कुंभ": "शनि",
    "मीन": "बृहस्पति"
}

# Planet to gemstone mapping (derived from provided dictionaries)
planet_to_gemstone = {
    "मंगल": "मूँगा रक्त इटालियन 7 रत्ती सोना या चाँदी में",
    "शुक्र": "बज्रमणि सफ़ेद / ब्राउन डायमंड 5 रत्ती / हीरा 50 सेंट",
    "बुध": "पन्ना ब्राज़ीली / पेरिडॉट / ग्रीन तुरमुली 5+ रत्ती चाँदी या प्लैटिनम में",
    "चंद्र": "नेचुरल मोती 5 रत्ती (चाँदी में)",
    "सूर्य": "माणिक 5 रत्ती सोना या ब्रॉन्ज़ में",
    "बृहस्पति": "पीत पुखराज / पीला बज्रमणि 5+ रत्ती सोना या ब्रॉन्ज़ में",
    "शनि": "बज्रमणि ब्लू / नीलम 5+ रत्ती पंचधातु में",
    "राहु": "गोमेद 5+ रत्ती चाँदी में",
    "केतु": "लहसुनिया 5+ रत्ती चाँदी में"
}

# Exalted signs for planets
exalted_signs = {
    "सूर्य": "मेष",
    "चंद्र": "वृष",
    "मंगल": "मकर",
    "बुध": "कन्या",
    "बृहस्पति": "कर्क",
    "शुक्र": "मीन",
    "शनि": "तुला",
    "राहु": "वृष",
    "केतु": "वृश्चिक"
}

# Benefic and malefic planets
benefics = ["बृहस्पति", "शुक्र", "बुध", "चंद्र"]
malefics = ["मंगल", "शनि", "राहु", "केतु"]

# Static gemstone dictionaries (for fallback)
bhagyavardhak_ratna = {
    "मेष": "पीत पुखराज / पीला बज्रमणि 5+ रत्ती सोना या ब्रॉन्ज़ में",
    "वृष": "बज्रमणि ब्लू / नीलम 5+ रत्ती पंचधातु में",
    "मिथुन": "बज्रमणि ब्लू / नीलम 5+ रत्ती पंचधातु में",
    "कर्क": "पीत पुखराज / पीला बज्रमणि 5+ रत्ती सोना या ब्रॉन्ज़ में",
    "सिंह": "मूँगा रक्त इटालियन 7 रत्ती सोना या चाँदी में",
    "कन्या": "बज्रमणि सफ़ेद / ब्राउन डायमंड 5 रत्ती / हीरा 50 सेंट",
    "तुला": "पन्ना ब्राज़ीली / पेरिडॉट / ग्रीन तुरमुली 5+ रत्ती चाँदी या प्लैटिनम में",
    "वृश्चिक": "नेचुरल मोती 5 रत्ती (चाँदी में)",
    "धनु": "माणिक 5 रत्ती सोना या ब्रॉन्ज़ में",
    "मकर": "पन्ना ब्राज़ीली / पेरिडॉट / ग्रीन तुरमुली 5+ रत्ती चाँदी या प्लैटिनम में",
    "कुंभ": "बज्रमणि सफ़ेद / ब्राउन डायमंड 5 रत्ती / हीरा 50 सेंट",
    "मीन": "मूँगा रक्त इटालियन 7 रत्ती सोना या चाँदी में"
}

jeevan_rakshak_ratna = {
    "मेष": "मूँगा रक्त इटालियन 7 रत्ती सोना या चाँदी में",
    "वृष": "बज्रमणि सफ़ेद / ब्राउन डायमंड 5 रत्ती / हीरा 50 सेंट",
    "मिथुन": "पन्ना ब्राज़ीली / पेरिडॉट / ग्रीन तुरमुली 5+ रत्ती चाँदी या प्लैटिनम में",
    "कर्क": "नेचुरल मोती 5 रत्ती (चाँदी में)",
    "सिंह": "माणिक 5 रत्ती सोना या ब्रॉन्ज़ में",
    "कन्या": "पन्ना ब्राज़ीली / पेरिडॉट / ग्रीन तुरमुली 5+ रत्ती चाँदी या प्लैटिनम में",
    "तुला": "बज्रमणि सफ़ेद / ब्राउन डायमंड 5 रत्ती / हीरा 50 सेंट",
    "वृश्चिक": "मूँगा रक्त इटालियन 7 रत्ती सोना या चाँदी में",
    "धनु": "पीत पुखराज / पीला बज्रमणि 5+ रत्ती सोना या ब्रॉन्ज़ में",
    "मकर": "बज्रमणि ब्लू / नीलम 5+ रत्ती पंचधातु में",
    "कुंभ": "बज्रमणि ब्लू / नीलम 5+ रत्ती पंचधातु में",
    "मीन": "पीत पुखराज / पीला बज्रमणि 5+ रत्ती सोना या ब्रॉन्ज़ में"
}

vidya_vardhak_ratna = {
    "मेष": "मूँगा रक्त इटालियन 7 रत्ती सोना या चाँदी में",
    "वृष": "बज्रमणि सफ़ेद / ब्राउन डायमंड 5 रत्ती / हीरा 50 सेंट",
    "मिथुन": "पन्ना ब्राज़ीली / पेरिडॉट / ग्रीन तुरमुली 5+ रत्ती चाँदी या प्लैटिनम में",
    "कर्क": "नेचुरल मोती 5 रत्ती (चाँदी में)",
    "सिंह": "माणिक 5 रत्ती सोना या ब्रॉन्ज़ में",
    "कन्या": "पन्ना ब्राज़ीली / पेरिडॉट / ग्रीन तुरमुली 5+ रत्ती चाँदी या प्लैटिनम में",
    "तुला": "बज्रमणि सफ़ेद / ब्राउन डायमंड 5 रत्ती / हीरा 50 सेंट",
    "वृश्चिक": "मूँगा रक्त इटालियन 7 रत्ती सोना या चाँदी में",
    "धनु": "पीत पुखराज / पीला बज्रमणि 5+ रत्ती सोना या ब्रॉन्ज़ में",
    "मकर": "बज्रमणि ब्लू / नीलम 5+ रत्ती पंचधातु में",
    "कुंभ": "बज्रमणि ब्लू / नीलम 5+ रत्ती पंचधातु में",
    "मीन": "पीत पुखराज / पीला बज्रमणि 5+ रत्ती सोना या ब्रॉन्ज़ में"
}

# Planet mantras for Mahadasha
planet_mantras = {
    "सूर्य": "ॐ घृणिः सूर्याय नमः",
    "चंद्र": "ॐ सों सोमाय नमः",
    "मंगल": "ॐ अं अंगारकाय नमः",
    "बुध": "ॐ बुं बुद्धाय नमः",
    "बृहस्पति": "ॐ बृं बृहस्पतये नमः",
    "शुक्र": "ॐ शुं शुक्राय नमः",
    "शनि": "ॐ शं शनैश्चराय नमः",
    "राहु": "ॐ रां राहवे नमः",
    "केतु": "ॐ कें केतवे नमः"
}

def get_gemstone(house_number, lagna_chart, planet_positions, lagna_sign_index):
    """
    Calculate gemstone for a given house based on Rashi lord, planetary strength, and aspects.
    Args:
        house_number (int): House number (1, 5, or 9).
        lagna_chart (dict): Lagna chart with house numbers as keys and {'sign': str, 'planets': list} as values.
        planet_positions (dict): Planet positions with planet names as keys and {'sign': str, 'rashi_lord': str} as values.
        lagna_sign_index (int): Index of Lagna Rashi (0-based).
    Returns:
        str: Recommended gemstone.
    """
    # Get Rashi and lord for the house
    house_index = (lagna_sign_index + (house_number - 1)) % 12 + 1
    rashi = lagna_chart[house_index]["sign"]
    lord = rashi_lord[rashi]
    
    # Check if the lord is strong (in own or exalted sign)
    lord_sign = planet_positions.get(lord, {}).get("sign", "")
    is_lord_strong = lord_sign == rashi or lord_sign == exalted_signs.get(lord, "")
    
    # Check if the lord is benefic
    is_lord_benefic = lord in benefics
    
    # If lord is strong and benefic, use its gemstone
    if is_lord_strong and is_lord_benefic:
        return planet_to_gemstone.get(lord, "Unknown")
    
    # Check benefic planets in the house
    house_planets = lagna_chart[house_index]["planets"]
    for planet in benefics:
        if planet in house_planets:
            planet_sign = planet_positions.get(planet, {}).get("sign", "")
            is_planet_strong = planet_sign == rashi or planet_sign == exalted_signs.get(planet, "")
            if is_planet_strong:
                return planet_to_gemstone.get(planet, "Unknown")
    
    # Check aspects by benefic planets (Jupiter: 5th/9th, Venus/Mercury: 7th)
    for planet in benefics:
        planet_house = None
        for h in range(1, 13):
            if planet in lagna_chart[h]["planets"]:
                planet_house = h
                break
        if planet_house:
            if planet == "बृहस्पति":
                aspects = [(planet_house + 4) % 12 or 12, (planet_house + 8) % 12 or 12]
            else:
                aspects = [(planet_house + 6) % 12 or 12]
            if house_index in aspects:
                planet_sign = planet_positions.get(planet, {}).get("sign", "")
                is_planet_strong = planet_sign == lagna_chart[planet_house]["sign"] or planet_sign == exalted_signs.get(planet, "")
                if is_planet_strong:
                    return planet_to_gemstone.get(planet, "Unknown")
    
    # Default: Jupiter for 5th/9th, Lagna lord for 1st, or fallback to static dictionary
    if house_number in [5, 9]:
        return planet_to_gemstone.get("बृहस्पति", "पीत पुखराज / पीला बज्रमणि 5+ रत्ती सोना या ब्रॉन्ज़ में")
    elif house_number == 1:
        return planet_to_gemstone.get(lord, jeevan_rakshak_ratna.get(rashi, "Unknown"))
    else:
        # Fallback to static dictionaries
        if house_number == 5:
            return vidya_vardhak_ratna.get(rashi, "Unknown")
        elif house_number == 9:
            return bhagyavardhak_ratna.get(rashi, "Unknown")
        return "Unknown"

def draw_north_indian_chart(chart_data, title, filename):
    try:
        plt.clf()
        plt.close()

        timestamp = int(time.time() * 1000)
        filename = f"{filename.split('.png')[0]}_{timestamp}.png"
        sanitized_filename = sanitize_filename(filename)
        filepath = os.path.join("static", sanitized_filename)
        logger.debug(f"Saving chart to: {filepath}")

        font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansDevanagari-Regular.ttf")
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"Font file not found at {font_path}")
        hindi_font = fm.FontProperties(fname=font_path)

        fig, ax = plt.subplots(figsize=(6, 5.4))
        ax.set_facecolor('white')
        ax.axis('off')

        line_color = '#D4A017'
        linewidth = 2
        ax.plot([0, 0, 1, 1, 0], [0, 1, 1, 0, 0], color=line_color, linewidth=linewidth)
        ax.plot([0, 1], [0, 1], color=line_color, linewidth=linewidth)
        ax.plot([1, 0], [0, 1], color=line_color, linewidth=linewidth)
        ax.plot([0.5, 0], [0, 0.5], color=line_color, linewidth=linewidth)
        ax.plot([0.5, 1], [0, 0.5], color=line_color, linewidth=linewidth)
        ax.plot([0, 0.5], [0.5, 1], color=line_color, linewidth=linewidth)
        ax.plot([0.5, 1], [1, 0.5], color=line_color, linewidth=linewidth)

        SYMBOL_SIZE = 0.048
        house_bounds = {
            1: (0.35, 0.65, 0.60, 0.90),
            2: (0.65, 0.90, 0.00, 0.20),
            3: (0.80, 1.00, 0.15, 0.35),
            4: (0.65, 0.90, 0.35, 0.65),
            5: (0.80, 1.00, 0.65, 0.85),
            6: (0.65, 0.90, 0.80, 1.00),
            7: (0.35, 0.65, 0.10, 0.40),
            8: (0.10, 0.35, 0.80, 1.00),
            9: (0.00, 0.20, 0.65, 0.85),
            10: (0.10, 0.35, 0.35, 0.65),
            11: (0.00, 0.20, 0.15, 0.35),
            12: (0.10, 0.35, 0.00, 0.20)
        }

        provided_coordinates = {
            1: {
                "rashi": (247/500, (500-119)/500),
                "planets": [
                    (210/500, (500-124)/500),
                    (247/500, (500-80)/500),
                    (306/500, (500-119)/500),
                    (252/500, (500-187)/500),
                    (218/500, (500-149)/500)
                ]
            },
            8: {
                "rashi": (123/500, (500-77)/500),
                "planets": [
                    (80/500, (500-26)/500),
                    (110/500, (500-27)/500),
                    (132/500, (500-26)/500),
                    (168/500, (500-26)/500)
                ]
            },
            9: {
                "rashi": (77/500, (500-122)/500),
                "planets": [
                    (23/500, (500-67)/500),
                    (27/500, (500-98)/500),
                    (30/500, (500-130)/500),
                    (29/500, (500-163)/500)
                ]
            },
            10: {
                "rashi": (123/500, (500-245)/500),
                "planets": [
                    (60/500, (500-246)/500),
                    (89/500, (500-214)/500),
                    (128/500, (500-182)/500),
                    (183/500, (500-246)/500),
                    (124/500, (500-304)/500)
                ]
            },
            11: {
                "rashi": (76/500, (500-378)/500),
                "planets": [
                    (26/500, (500-319)/500),
                    (28/500, (500-349)/500),
                    (30/500, (500-384)/500),
                    (29/500, (500-422)/500)
                ]
            },
            12: {
                "rashi": (125/500, (500-426)/500),
                "planets": [
                    (80/500, (500-445)/500),
                    (145/500, (500-455)/500),
                    (80/500, (500-465)/500),
                    (145/500, (500-470)/500)
                ]
            },
            7: {
                "rashi": (251/500, (500-360)/500),
                "planets": [
                    (249/500, (500-314)/500),
                    (207/500, (500-347)/500),
                    (190/500, (500-395)/500),
                    (246/500, (500-428)/500),
                    (309/500, (500-371)/500)
                ]
            },
            2: {
                "rashi": (375/500, (500-421)/500),
                "planets": [
                    (355/500, (500-449)/500),
                    (326/500, (500-469)/500),
                    (374/500, (500-473)/500),
                    (420/500, (500-466)/500)
                ]
            },
            3: {
                "rashi": (418/500, (500-374)/500),
                "planets": [
                    (471/500, (500-323)/500),
                    (464/500, (500-360)/500),
                    (465/500, (500-398)/500),
                    (467/500, (500-423)/500)
                ]
            },
            4: {
                "rashi": (375/500, (500-250)/500),
                "planets": [
                    (315/500, (500-248)/500),
                    (343/500, (500-213)/500),
                    (381/500, (500-190)/500),
                    (429/500, (500-246)/500),
                    (374/500, (500-305)/500)
                ]
            },
            5: {
                "rashi": (419/500, (500-123)/500),
                "planets": [
                    (447/500, (500-103)/500),
                    (469/500, (500-75)/500),
                    (461/500, (500-148)/500),
                    (471/500, (500-175)/500)
                ]
            },
            6: {
                "rashi": (373/500, (500-75)/500),
                "planets": [
                    (340/500, (500-45)/500),
                    (361/500, (500-30)/500),
                    (395/500, (500-29)/500),
                    (424/500, (500-37)/500)
                ]
            }
        }

        rashi_to_number = {
            "मेष": 1, "वृष": 2, "मिथुन": 3, "कर्क": 4, "सिंह": 5, "कन्या": 6,
            "तुला": 7, "वृश्चिक": 8, "धनु": 9, "मकर": 10, "कुंभ": 11, "मीन": 12
        }

        inverse_permutation = {
            1: 1, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12,
            7: 7, 8: 2, 9: 3, 10: 4, 11: 5, 12: 6
        }

        for json_house in range(1, 13):
            chart_house = inverse_permutation[json_house]
            if json_house not in chart_data:
                logger.error(f"House {json_house} not found in chart_data")
                continue
            data = chart_data[json_house]
            rashi = data.get('sign')
            if not rashi or rashi not in rashi_to_number:
                logger.error(f"Invalid Rashi data for house {json_house}: {data}")
                continue
            rashi_number = rashi_to_number[rashi]
            if chart_house not in provided_coordinates:
                logger.error(f"No coordinates provided for chart house {chart_house}")
                continue
            rashi_x, rashi_y = provided_coordinates[chart_house]["rashi"]
            ax.text(rashi_x, rashi_y, str(rashi_number), ha='center', va='center', color='black', fontsize=18, fontweight='bold')
            logger.debug(f"Placed Rashi {rashi} (number {rashi_number}) at ({rashi_x}, {rashi_y}) in chart house {chart_house}")

        for json_house in range(1, 13):
            chart_house = inverse_permutation[json_house]
            if json_house not in chart_data:
                continue
            data = chart_data[json_house]
            planets = data.get('planets', [])
            if not planets:
                continue
            if chart_house not in provided_coordinates:
                logger.error(f"No coordinates provided for chart house {chart_house}")
                continue

            planet_coords = provided_coordinates[chart_house]["planets"]
            num_planets = len(planets)
            num_coords = len(planet_coords)

            if num_planets > num_coords:
                logger.warning(f"House {chart_house}: More planets ({num_planets}) than coordinates ({num_coords}). Using first {num_coords} planets.")
                planets = planets[:num_coords]
            elif num_planets < num_coords:
                logger.debug(f"House {chart_house}: Fewer planets ({num_planets}) than coordinates ({num_coords}). Using first {num_planets} coordinates.")
                planet_coords = planet_coords[:num_planets]

            x_min, x_max, y_min, y_max = house_bounds[chart_house]
            padding = 0.04
            x_min += padding
            x_max -= padding
            y_min += padding
            y_max -= padding
            x_min, x_max = min(x_min, x_max), max(x_min, x_max)
            y_min, y_max = min(y_min, y_max), max(y_min, y_max)

            for idx, planet in enumerate(planets):
                if planet not in planet_symbols:
                    logger.error(f"Planet {planet} not found in planet_symbols")
                    continue
                pos_x, pos_y = planet_coords[idx]
                if not (x_min <= pos_x <= x_max and y_min <= pos_y <= y_max):
                    logger.warning(f"House {chart_house}: Planet {planet} at ({pos_x}, {pos_y}) is outside bounds ({x_min}, {x_max}, {y_min}, {y_max})")
                symbol, color = planet_symbols[planet]
                ax.text(pos_x, pos_y, symbol, ha='center', va='center', color=color, fontsize=12, fontproperties=hindi_font)
                logger.debug(f"Placed {planet} ({symbol}) at ({pos_x}, {pos_y}) in chart house {chart_house}")

        plt.savefig(filepath, bbox_inches='tight', facecolor='white', dpi=100)
        plt.clf()
        plt.close()
        logger.debug(f"Chart saved to {filepath}")
        return sanitized_filename

    except Exception as e:
        logger.exception(f"Error drawing chart: {str(e)}")
        raise

def cleanup_static_folder():
    now = time.time()
    for filename in os.listdir(STATIC_FOLDER):
        filepath = os.path.join(STATIC_FOLDER, filename)
        if os.path.isfile(filepath) and os.path.getmtime(filepath) < now - 86400:
            os.remove(filepath)
    logger.debug("Static folder cleaned")

@app.route('/ping', methods=['GET'])
def ping():
    logger.debug("Ping received")
    return jsonify({"status": "alive"}), 200

def get_lat_lon(birth_place):
    try:
        birth_place = birth_place.strip().lower()
        if birth_place in geolocation_cache:
            logger.debug(f"Using cached geolocation for {birth_place}")
            return geolocation_cache[birth_place]
        geolocator = Nominatim(user_agent="kundali_app")
        location = geolocator.geocode(birth_place)
        if location:
            geolocation_cache[birth_place] = (location.latitude, location.longitude)
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        logger.error(f"Error in get_lat_lon: {e}")
        return None, None

def convert_to_julian(birth_date, birth_time):
    year, month, day = map(int, birth_date.split('-'))
    hour, minute = map(int, birth_time.split(':'))
    jd = swe.julday(year, month, day, hour + (minute / 60.0) - 5.5)  # IST to UTC
    logger.debug(f"Calculated JD for {day}-{month}-{year} {hour}:{minute} IST = {jd}")
    return jd

def julian_to_time(jd, return_only_hour_minute=False):
    try:
        unix_time = (jd - 2440587.5) * 86400
        utc_time = datetime.fromtimestamp(unix_time, timezone.utc)
        ist_time = utc_time + timedelta(hours=5, minutes=30)
        if return_only_hour_minute:
            return ist_time.strftime("%H:%M")
        return ist_time.strftime("%I:%M:%S %p")
    except Exception as e:
        logger.error(f"Error in julian_to_time: {e}")
        return "Calculation Error"

def get_sunrise_time(julian_day, lat, lon):
    try:
        logger.debug(f"Input to get_sunrise_time -> JD: {julian_day}, Lat: {lat}, Lon: {lon}")
        jd_ut = float(julian_day)
        geopos = (lon, lat, 0)
        res, tret = swe.rise_trans(jd_ut, swe.SUN, swe.CALC_RISE, geopos)
        if res == 0 and isinstance(tret, tuple):
            sunrise_jd = tret[0]
            logger.debug(f"Calculated Sunrise JD = {sunrise_jd}")
            return sunrise_jd
        raise ValueError("Sunrise calculation failed")
    except Exception as e:
        logger.error(f"Error in get_sunrise_time: {e}")
        return None

def calculate_ist_kaal(birth_time, sunrise_time):
    try:
        fmt = "%H:%M"
        birth_dt = datetime.strptime(birth_time, fmt)
        sunrise_dt = datetime.strptime(sunrise_time, fmt)
        ist_kaal_minutes = (birth_dt.hour * 60 + birth_dt.minute) - (sunrise_dt.hour * 60 + sunrise_dt.minute)
        if ist_kaal_minutes < 0:
            raise ValueError(f"Birth time ({birth_time}) is before sunrise ({sunrise_time})!")
        total_pal = ist_kaal_minutes * 2.5
        ghati = int(total_pal // 60)
        remaining_pal = total_pal % 60
        pal = int(remaining_pal)
        vipal = int((remaining_pal - pal) * 60)
        if pal >= 60:
            extra_ghati = pal // 60
            ghati += extra_ghati
            pal = pal % 60
        ist_kaal = f"{ghati}-{pal}-{vipal}"
        logger.debug(f"Calculated Ist Kaal = {ist_kaal}")
        return ist_kaal
    except Exception as e:
        logger.error(f"Error in calculate_ist_kaal: {e}")
        return None

def calculate_mulyank(birth_date):
    try:
        day = int(birth_date.split('-')[2])
        mulyank = sum(int(digit) for digit in str(day))
        while mulyank > 9:
            mulyank = sum(int(digit) for digit in str(mulyank))
        logger.debug(f"Calculated Mulyank for day {day} = {mulyank}")
        return mulyank
    except Exception as e:
        logger.error(f"Error in calculate_mulyank: {e}")
        return None

def compute_lagna(birth_jd, lat, lon, ayanamsa):
    sidereal_time = (swe.sidtime(birth_jd) * 15 + lon) % 360
    logger.debug(f"Sidereal Time = {sidereal_time}°")
    houses, ascmc = swe.houses(birth_jd, lat, lon, b'A')
    ascendant_degree = float(ascmc[0])
    logger.debug(f"Swiss Ephemeris Ascendant Degree = {ascendant_degree}°")
    ascendant_degree_corrected = (ascendant_degree - ayanamsa) % 360
    logger.debug(f"Corrected Ascendant Degree After Ayanamsa = {ascendant_degree_corrected}°")
    rashi_names = ["मेष", "वृष", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक",
                   "धनु", "मकर", "कुंभ", "मीन"]
    lagna_sign_index = int(ascendant_degree_corrected // 30) % 12
    lagna_rashi = rashi_names[lagna_sign_index]
    logger.debug(f"Assigned Lagna Rashi = {lagna_rashi}")
    return ascendant_degree_corrected, lagna_rashi

nakshatra_letters = {
    "अश्विनी": ["च", "चि", "चु", "चे"],
    "भरणी": ["ल", "लि", "लू", "ले"],
    "कृत्तिका": ["अ", "इ", "उ", "ए"],
    "रोहिणी": ["क", "कि", "कू", "के"],
    "मृगशीर्ष": ["ग", "गि", "गू", "गे"],
    "आर्द्रा": ["अ", "इ", "उ", "ए"],
    "पुनर्वसु": ["अ", "इ", "उ", "ए"],
    "पुष्य": ["अ", "इ", "उ", "ए"],
    "आश्लेषा": ["अ", "इ", "उ", "ए"],
    "मघा": ["अ", "इ", "उ", "ए"],
    "पूर्वा फाल्गुनी": ["अ", "इ", "उ", "ए"],
    "उत्तरा फाल्गुनी": ["अ", "इ", "उ", "ए"],
    "हस्त": ["अ", "इ", "उ", "ए"],
    "चित्रा": ["अ", "इ", "उ", "ए"],
    "स्वाति": ["अ", "इ", "उ", "ए"],
    "विशाखा": ["अ", "इ", "उ", "ए"],
    "अनुराधा": ["अ", "इ", "उ", "ए"],
    "ज्येष्ठा": ["अ", "इ", "उ", "ए"],
    "मूल": ["अ", "इ", "उ", "ए"],
    "पूर्वाषाढ़ा": ["भ", "भि", "भू", "ध"],
    "उत्तराषाढ़ा": ["भ", "भि", "भू", "ध"],
    "श्रवण": ["थ", "थि", "थू", "थे"],
    "धनिष्ठा": ["ज", "जि", "जू", "जे"],
    "शतभिषा": ["ज", "जि", "जू", "जे"],
    "पूर्वाभाद्रपद": ["ख", "खि", "खू", "खे"],
    "उत्तराभाद्रपद": ["ख", "खि", "खू", "खे"],
    "रेवती": ["ल", "लि", "लू", "ले"]
}

nakshatras = [
    "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशीर्ष", "आर्द्रा", "पुनर्वसु", "पुष्य", "आश्लेषा",
    "मघा", "पूर्वा फाल्गुनी", "उत्तरा फाल्गुनी", "हस्त", "चित्रा", "स्वाति", "विशाखा", "अनुराधा", "ज्येष्ठा",
    "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा", "पूर्वाभाद्रपद", "उत्तराभाद्रपद", "रेवती"
]

nakshatra_gana = {
    "अश्विनी": "देव गण",
    "भरणी": "मनुष्य गण",
    "कृत्तिका": "राक्षस गण",
    "रोहिणी": "मनुष्य गण",
    "मृगशीर्ष": "देव गण",
    "आर्द्रा": "मनुष्य गण",
    "पुनर्वसु": "देव गण",
    "पुष्य": "देव गण",
    "आश्लेषा": "राक्षस गण",
    "मघा": "राक्षस गण",
    "पूर्वा फाल्गुनी": "मनुष्य गण",
    "उत्तरा फाल्गुनी": "मनुष्य गण",
    "हस्त": "देव गण",
    "चित्रा": "राक्षस गण",
    "स्वाति": "देव गण",
    "विशाखा": "राक्षस गण",
    "अनुराधा": "देव गण",
    "ज्येष्ठा": "राक्षस गण",
    "मूल": "राक्षस गण",
    "पूर्वाषाढ़ा": "मनुष्य गण",
    "उत्तराषाढ़ा": "मनुष्य गण",
    "श्रवण": "मनुष्य गण",
    "धनिष्ठा": "राक्षस गण",
    "शतभिषा": "मनुष्य गण",
    "पूर्वाभाद्रपद": "मनुष्य गण",
    "उत्तराभाद्रपद": "राक्षस गण",
    "रेवती": "देव गण"
}

ruling_planets = ["केतु", "शुक्र", "सूर्य", "चंद्र", "मंगल", "राहु", "बृहस्पति", "शनि", "बुध"]

mahadasha_periods = {
    "केतु": 7,
    "शुक्र": 20,
    "सूर्य": 6,
    "चंद्र": 10,
    "मंगल": 7,
    "राहु": 18,
    "बृहस्पति": 16,
    "शनि": 19,
    "बुध": 17
}

dusthana_houses = [6, 8, 12]

rashi_lucky_days = {
    "मेष": "मंगलवार",
    "वृष": "शुक्रवार",
    "मिथुन": "बुधवार",
    "कर्क": "सोमवार",
    "सिंह": "रविवार",
    "कन्या": "बुधवार",
    "तुला": "शुक्रवार",
    "वृश्चिक": "मंगलवार, सोमवार",
    "धनु": "गुरुवार",
    "मकर": "शनिवार",
    "कुंभ": "शनिवार",
    "मीन": "गुरुवार"
}

rashi_ishta_devta = {
    "मेष": "पंचमुखी हनुमान",
    "वृष": "भवानी शंकर",
    "मिथुन": "गणेश जी",
    "कर्क": "भवानी शंकर",
    "सिंह": "भगवान सूर्य",
    "कन्या": "गणेश जी",
    "तुला": "भवानी शंकर",
    "वृश्चिक": "भवानी शंकर",
    "धनु": "हनुमान जी",
    "मकर": "नरसिंह भगवान",
    "कुंभ": "लक्ष्मी नारायण",
    "मीन": "दुर्गा जी"
}

rashi_numbers = {
    "मेष": 1,
    "वृष": 2,
    "मिथुन": 3,
    "कर्क": 4,
    "सिंह": 5,
    "कन्या": 6,
    "तुला": 7,
    "वृश्चिक": 8,
    "धनु": 9,
    "मकर": 10,
    "कुंभ": 11,
    "मीन": 12
}

planet_lucky_colors = {
    "मंगल": "लाल",
    "शुक्र": "सफेद",
    "बुध": "हरा",
    "चंद्र": "सफेद",
    "सूर्य": "नारंगी",
    "बृहस्पति": "पीला",
    "शनि": "नीला"
}

def calculate_nakshatra_and_charan(sidereal_pos):
    nakshatra_degrees = 13.3333
    charan_degrees = 3.3333
    
    nakshatra_index = int(sidereal_pos // nakshatra_degrees)
    nakshatra = nakshatras[nakshatra_index % 27]
    
    remainder = sidereal_pos % nakshatra_degrees
    charan = int(remainder // charan_degrees) + 1
    
    return nakshatra, charan

def get_naming_letter(nakshatra_name, pada_number):
    if nakshatra_name in nakshatra_letters:
        letters = nakshatra_letters[nakshatra_name]
        if 1 <= pada_number <= 4:
            return letters[pada_number - 1]
    return None

def compute_planet_positions(birth_jd, ayanamsa):
    planets = {
        "सूर्य": swe.SUN,
        "चंद्र": swe.MOON,
        "बुध": swe.MERCURY,
        "शुक्र": swe.VENUS,
        "मंगल": swe.MARS,
        "बृहस्पति": swe.JUPITER,
        "शनि": swe.SATURN,
        "राहु": swe.MEAN_NODE,
        "केतु": swe.MEAN_NODE
    }
    positions = {}
    rashi_names = ["मेष", "वृष", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक",
                   "धनु", "मकर", "कुंभ", "मीन"]
    
    for planet, swe_id in planets.items():
        result = swe.calc_ut(birth_jd, swe_id)
        logger.debug(f"{planet} raw result = {result}")
        tropical_pos = float(result[0][0])
        logger.debug(f"{planet} tropical_pos = {tropical_pos}")
        sidereal_pos = (tropical_pos - ayanamsa) % 360
        sign_index = int(sidereal_pos // 30) % 12
        sign = rashi_names[sign_index]
        if planet == "केतु":
            sidereal_pos = (sidereal_pos + 180) % 360
            sign_index = int(sidereal_pos // 30) % 12
            sign = rashi_names[sign_index]
        
        nakshatra, charan = calculate_nakshatra_and_charan(sidereal_pos)
        
        naming_letter = None
        if planet == "चंद्र":
            naming_letter = get_naming_letter(nakshatra, charan)
        
        positions[planet] = {
            "degree": sidereal_pos,
            "sign": sign,
            "sign_number": sign_index + 1,
            "rashi": sign,
            "rashi_number": sign_index + 1,
            "rashi_lord": rashi_lord[sign],
            "nakshatra": nakshatra,
            "charan": charan,
            "naming_letter": naming_letter if naming_letter else None,
        }
        logger.debug(f"{planet} = {sidereal_pos}° in {sign}")
    return positions

def build_north_indian_chart(lagna_sign_index, moon_sign_index, planet_positions):
    rashi_names = ["मेष", "वृष", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक",
                   "धनु", "मकर", "कुंभ", "मीन"]
    
    lagna_sign_number = lagna_sign_index + 1
    moon_sign_number = moon_sign_index + 1
    
    lagna_chart = {i: {"sign": rashi_names[(lagna_sign_index + i - 1) % 12], "planets": []} for i in range(1, 13)}
    chandra_chart = {i: {"sign": rashi_names[(moon_sign_index + i - 1) % 12], "planets": []} for i in range(1, 13)}
    
    for planet, data in planet_positions.items():
        sign_number = data["sign_number"]
        lagna_house = (sign_number - lagna_sign_number) % 12 + 1
        chandra_house = (sign_number - moon_sign_number) % 12 + 1
        lagna_chart[lagna_house]["planets"].append(planet)
        chandra_chart[chandra_house]["planets"].append(planet)
    
    return lagna_chart, chandra_chart

def calculate_lucky_number(birth_date):
    digits = ''.join(filter(str.isdigit, birth_date))
    lucky_number = sum(int(digit) for digit in digits)
    while lucky_number > 9:
        lucky_number = sum(int(digit) for digit in str(lucky_number))
    return lucky_number

def calculate_lucky_dates(lucky_number):
    lucky_dates = []
    for date in range(1, 32):
        digit_sum = sum(int(digit) for digit in str(date))
        while digit_sum > 9:
            digit_sum = sum(int(digit) for digit in str(digit_sum))
        if digit_sum == lucky_number:
            lucky_dates.append(date)
        if len(lucky_dates) >= 3:
            break
    return lucky_dates

@app.route('/kundali', methods=['POST', 'OPTIONS'])
def calculate_kundali():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "ok"})
        response.status_code = 200
        response.headers['Access-Control-Allow-Origin'] = 'https://astrologerinranchi.com'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response
        
    cleanup_static_folder()    
    data = request.json
    name = data.get("name")
    birth_date = data.get("birth_date")
    birth_time = data.get("birth_time")
    birth_place = data.get("birth_place")

    if not birth_date or not birth_time or not birth_place:
        return jsonify({"error": "Missing required fields"}), 400

    lat, lon = get_lat_lon(birth_place)
    if lat is None or lon is None:
        return jsonify({"error": "Invalid birth place"}), 400

    birth_jd = convert_to_julian(birth_date, birth_time)
    ayanamsa = swe.get_ayanamsa_ut(birth_jd)
    logger.debug(f"Birth Date = {birth_date} {birth_time} IST")
    logger.debug(f"Birth JD = {birth_jd}")
    logger.debug(f"Ayanamsa = {ayanamsa}")

    lagna_degree, lagna_rashi = compute_lagna(birth_jd, lat, lon, ayanamsa)
    lagna_sign_index = ["मेष", "वृष", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक",
                        "धनु", "मकर", "कुंभ", "मीन"].index(lagna_rashi)

    planet_positions = compute_planet_positions(birth_jd, ayanamsa)
    moon_sign_index = planet_positions["चंद्र"]["sign_number"] - 1
    lagna_chart, chandra_chart = build_north_indian_chart(lagna_sign_index, moon_sign_index, planet_positions)
    
    sanitized_name = sanitize_filename(name)
    lagna_filename = f"lagna_{sanitized_name}_{birth_date}_{birth_time}.png".replace(" ", "_").replace(":", "-")
    chandra_filename = f"chandra_{sanitized_name}_{birth_date}_{birth_time}.png".replace(" ", "_").replace(":", "-")
    
    lagna_filename = draw_north_indian_chart(lagna_chart, "लग्न कुण्डली", lagna_filename)
    chandra_filename = draw_north_indian_chart(chandra_chart, "चंद्र कुण्डली", chandra_filename)

    lagna_image_url = url_for('static', filename=lagna_filename, _external=True)
    chandra_image_url = url_for('static', filename=chandra_filename, _external=True)
    logger.debug(f"Lagna Image URL: {lagna_image_url}, Chandra Image URL: {chandra_image_url}")

    sunrise_jd = get_sunrise_time(birth_jd, lat, lon)
    if sunrise_jd is None:
        return jsonify({"error": "Failed to calculate sunrise time"}), 500

    converted_sunrise_time = julian_to_time(sunrise_jd, return_only_hour_minute=True)
    ist_kaal = calculate_ist_kaal(birth_time, converted_sunrise_time)
    
    janam_nakshatra = planet_positions["चंद्र"]["nakshatra"]
    janam_charan = planet_positions["चंद्र"]["charan"]
    rashi = planet_positions["चंद्र"]["rashi"]
    
    janam_gana = nakshatra_gana.get(janam_nakshatra, "अज्ञात गण")
    logger.debug(f"Janam Nakshatra = {janam_nakshatra}, Gana = {janam_gana}")
    
    nakshatra_index = nakshatras.index(janam_nakshatra)
    ruling_planet = ruling_planets[nakshatra_index % 9]
    total_period = mahadasha_periods[ruling_planet]
    moon_sidereal_pos = planet_positions["चंद्र"]["degree"]
    nakshatra_degrees = 13.3333
    proportion_passed = (moon_sidereal_pos % nakshatra_degrees) / nakshatra_degrees
    balance_years = total_period * (1 - proportion_passed)

    total_days = balance_years * 365.25
    years = int(total_days // 365.25)
    remaining_days = total_days - years * 365.25
    months = int(remaining_days // 30)
    days = int(remaining_days - months * 30)
    mahadasha_balance = f"{ruling_planet} {years} Y {months} M {days} D"

    lucky_day = rashi_lucky_days.get(rashi, "Unknown")

    twelfth_house_number = (lagna_sign_index + 11) % 12 + 1
    twelfth_house_sign = lagna_chart[twelfth_house_number]["sign"]
    ishta_devta = rashi_ishta_devta.get(twelfth_house_sign, "Unknown")

    # Calculate Mulyank and Lucky Number
    mulyank = calculate_mulyank(birth_date)
    lucky_number = calculate_lucky_number(birth_date)
    lucky_dates = calculate_lucky_dates(lucky_number)
    lucky_dates_str = ", ".join(str(date) for date in lucky_dates) + " तारीख"
    logger.debug(f"Lucky Number = {lucky_number}, Lucky Dates = {lucky_dates_str}")

    rashi_lord_for_color = planet_positions["चंद्र"]["rashi_lord"]
    lucky_color = planet_lucky_colors.get(rashi_lord_for_color, "Unknown")

    # Gemstone calculations using dynamic logic
    jeevan_rakshak = get_gemstone(1, lagna_chart, planet_positions, lagna_sign_index)
    vidya_vardhak = get_gemstone(5, lagna_chart, planet_positions, lagna_sign_index)
    bhagyavardhak = get_gemstone(9, lagna_chart, planet_positions, lagna_sign_index)
    
    mangal_dosha_houses = [1, 4, 7, 8, 12]
    kendra_houses = [1, 4, 7, 10]

    mars_house = None
    for house in range(1, 13):
        if "मंगल" in lagna_chart[house]["planets"]:
            mars_house = house
            break

    mangal_dosha = mars_house in mangal_dosha_houses if mars_house else False

    mangal_dosha_details = {"exists": mangal_dosha, "nullified": False, "reasons": []}
    if mangal_dosha:
        jupiter_house = None
        for house in range(1, 13):
            if "बृहस्पति" in lagna_chart[house]["planets"]:
                jupiter_house = house
                break

        moon_house = None
        for house in range(1, 13):
            if "चंद्र" in lagna_chart[house]["planets"]:
                moon_house = house
                break

        rahu_house = None
        for house in range(1, 13):
            if "राहु" in lagna_chart[house]["planets"]:
                rahu_house = house
                break

        if jupiter_house:
            jupiter_aspects = [
                (jupiter_house + 4) % 12 or 12,
                (jupiter_house + 6) % 12 or 12,
                (jupiter_house + 8) % 12 or 12
            ]
            if mars_house in jupiter_aspects:
                mangal_dosha_details["nullified"] = True
                mangal_dosha_details["reasons"].append("गुरु मंगल को देख रहा है")

        if moon_house in kendra_houses:
            mangal_dosha_details["nullified"] = True
            mangal_dosha_details["reasons"].append("चंद्रमा केंद्र में है")

        if moon_house == mars_house:
            mangal_dosha_details["nullified"] = True
            mangal_dosha_details["reasons"].append("चंद्रमा मंगल के साथ है")

        if rahu_house == mars_house:
            mangal_dosha_details["nullified"] = True
            mangal_dosha_details["reasons"].append("राहु मंगल के साथ है")
            
    rahu_house = None
    ketu_house = None
    planet_houses = {}
    for house in range(1, 13):
        for planet in lagna_chart[house]["planets"]:
            if planet == "राहु":
                rahu_house = house
            elif planet == "केतु":
                ketu_house = house
            else:
                planet_houses[planet] = house

    kaalsarp_dosha = False
    kaalsarp_details = {"exists": False, "rahu_house": rahu_house, "ketu_house": ketu_house}
    if rahu_house and ketu_house:
        min_house = min(rahu_house, ketu_house)
        max_house = max(rahu_house, ketu_house)
        
        all_between = True
        for planet, house in planet_houses.items():
            if not ((min_house < house < max_house) or (house < min_house or house > max_house)):
                all_between = False
                break
        
        if all_between:
            kaalsarp_dosha = True
        else:
            all_between_reverse = all((house < min_house or house > max_house) for house in planet_houses.values())
            kaalsarp_dosha = all_between_reverse

        kaalsarp_details["exists"] = kaalsarp_dosha        

    def get_planet_house(planet, lagna_chart):
        for house in range(1, 13):
            if planet in lagna_chart[house]["planets"]:
                return house
        return None

    fifth_house_number = (lagna_sign_index + 4) % 12 + 1
    fifth_house_sign = lagna_chart[fifth_house_number]["sign"]
    fifth_house_lord = rashi_lord[fifth_house_sign]
    fifth_lord_house = get_planet_house(fifth_house_lord, lagna_chart)

    study_problem = False
    study_problem_reasons = []
    if fifth_lord_house is not None and fifth_lord_house in dusthana_houses:
        study_problem = True
        study_problem_reasons.append(f"पांचवे घर का स्वामी {fifth_house_lord} दुष्टान घर {fifth_lord_house} में है")
    if any(planet in lagna_chart[fifth_house_number]["planets"] for planet in malefics):
        study_problem = True
        malefic_planets = [planet for planet in lagna_chart[fifth_house_number]["planets"] if planet in malefics]
        study_problem_reasons.append(f"पांचवे घर में पाप ग्रह {', '.join(malefic_planets)} हैं")

    if study_problem:
        study_statement = f"पढ़ाई में बाधाएँ आ सकती हैं क्योंकि {', '.join(study_problem_reasons)}।"
        study_resolution = "माँ सरस्वती की कृपा हेतु प्रतिदिन \"ॐ ऐं सरस्वत्यै नमः\" मंत्र का 108 बार जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"
    else:
        study_statement = "पढ़ाई में सफलता के प्रबल योग बन रहे हैं।"
        study_resolution = "माँ सरस्वती का आशीर्वाद बनाए रखने हेतु \"ॐ ऐं सरस्वत्यै नमः\" मंत्र का नियमित जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"

    study_response = {
        "statement": study_statement,
        "resolution": study_resolution
    }

    second_house_number = (lagna_sign_index + 1) % 12 + 1
    second_house_sign = lagna_chart[second_house_number]["sign"]
    second_house_lord = rashi_lord[second_house_sign]
    second_lord_house = get_planet_house(second_house_lord, lagna_chart)

    eleventh_house_number = (lagna_sign_index + 10) % 12 + 1
    eleventh_house_sign = lagna_chart[eleventh_house_number]["sign"]
    eleventh_house_lord = rashi_lord[eleventh_house_sign]
    eleventh_lord_house = get_planet_house(eleventh_house_lord, lagna_chart)

    money_problem = False
    money_problem_reasons = []
    if second_lord_house is not None and second_lord_house in dusthana_houses:
        money_problem = True
        money_problem_reasons.append(f"दूसरे घर का स्वामी {second_house_lord} दुष्टान घर {second_lord_house} में है")
    if eleventh_lord_house is not None and eleventh_lord_house in dusthana_houses:
        money_problem = True
        money_problem_reasons.append(f"ग्यारहवें घर का स्वामी {eleventh_house_lord} दुष्टान घर {eleventh_lord_house} में है")
    if any(planet in lagna_chart[second_house_number]["planets"] for planet in malefics):
        money_problem = True
        malefic_planets = [planet for planet in lagna_chart[second_house_number]["planets"] if planet in malefics]
        money_problem_reasons.append(f"दूसरे घर में पाप ग्रह {', '.join(malefic_planets)} हैं")
    if any(planet in lagna_chart[eleventh_house_number]["planets"] for planet in malefics):
        money_problem = True
        malefic_planets = [planet for planet in lagna_chart[eleventh_house_number]["planets"] if planet in malefics]
        money_problem_reasons.append(f"ग्यारहवें घर में पाप ग्रह {', '.join(malefic_planets)} हैं")

    if money_problem:
        money_statement = f"धन संबंधी परेशानियाँ हो सकती हैं क्योंकि {', '.join(money_problem_reasons)}।"
        money_resolution = "महालक्ष्मी की कृपा हेतु शुक्रवार को \"ॐ श्रीं ह्रीं क्लीं महालक्ष्म्यै नमः\" मंत्र का 108 बार जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"
    else:
        money_statement = "धन प्राप्ति के लिए शुभ योग बन रहे हैं।"
        money_resolution = "लक्ष्मी माता का आशीर्वाद बनाए रखने हेतु \"ॐ श्रीं ह्रीं क्लीं महालक्ष्म्यै नमः\" मंत्र का नियमित जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"

    money_response = {
        "statement": money_statement,
        "resolution": money_resolution
    }

    tenth_house_number = (lagna_sign_index + 9) % 12 + 1
    tenth_house_sign = lagna_chart[tenth_house_number]["sign"]
    tenth_house_lord = rashi_lord[tenth_house_sign]
    tenth_lord_house = get_planet_house(tenth_house_lord, lagna_chart)

    work_problem = False
    work_problem_reasons = []
    if tenth_lord_house is not None and tenth_lord_house in dusthana_houses:
        work_problem = True
        work_problem_reasons.append(f"दसवें घर का स्वामी {tenth_house_lord} दुष्टान घर {tenth_lord_house} में है")
    if any(planet in lagna_chart[tenth_house_number]["planets"] for planet in malefics):
        work_problem = True
        malefic_planets = [planet for planet in lagna_chart[tenth_house_number]["planets"] if planet in malefics]
        work_problem_reasons.append(f"दसवें घर में पाप ग्रह {', '.join(malefic_planets)} हैं")

    if work_problem:
        work_statement = f"कार्यक्षेत्र में चुनौतियाँ संभव हैं क्योंकि {', '.join(work_problem_reasons)}।"
        work_resolution = "हनुमान जी की कृपा हेतु मंगलवार को \"ॐ हं हनुमते नमः\" मंत्र का 108 बार जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"
    else:
        work_statement = "कार्यक्षेत्र में उन्नति के शुभ योग हैं।"
        work_resolution = "हनुमान जी का आशीर्वाद बनाए रखने हेतु \"ॐ हं हनुमते नमः\" मंत्र का नियमित जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"

    work_response = {
        "statement": work_statement,
        "resolution": work_resolution
    }

    seventh_house_number = (lagna_sign_index + 6) % 12 + 1
    seventh_house_sign = lagna_chart[seventh_house_number]["sign"]
    seventh_house_lord = rashi_lord[seventh_house_sign]
    seventh_lord_house = get_planet_house(seventh_house_lord, lagna_chart)

    marriage_problem = False
    marriage_problem_reasons = []
    if seventh_lord_house is not None and seventh_lord_house in dusthana_houses:
        marriage_problem = True
        marriage_problem_reasons.append(f"सातवें घर का स्वामी {seventh_house_lord} दुष्टान घर {seventh_lord_house} में है")
    if any(planet in lagna_chart[seventh_house_number]["planets"] for planet in malefics):
        marriage_problem = True
        malefic_planets = [planet for planet in lagna_chart[seventh_house_number]["planets"] if planet in malefics]
        marriage_problem_reasons.append(f"सातवें घर में पाप ग्रह {', '.join(malefic_planets)} हैं")

    if marriage_problem:
        marriage_statement = f"विवाह में देरी या बाधाएँ हो सकती हैं क्योंकि {', '.join(marriage_problem_reasons)}।"
        marriage_resolution = "माँ पार्वती की कृपा हेतु \"ॐ उमायै नमः\" मंत्र का 108 बार जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"
    else:
        marriage_statement = "विवाह के लिए शुभ संयोग बन रहे हैं।"
        marriage_resolution = "शिव-पार्वती का आशीर्वाद बनाए रखने हेतु \"ॐ उमायै नमः\" मंत्र का नियमित जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"

    marriage_response = {
        "statement": marriage_statement,
        "resolution": marriage_resolution
    }

    mahadasha_problem = ruling_planet in malefics
    moon_house = get_planet_house("चंद्र", lagna_chart)
    saturn_house = get_planet_house("शनि", lagna_chart)
    sade_sati = False
    if moon_house and saturn_house:
        relative_position = (saturn_house - moon_house) % 12
        if relative_position in [0, 1, 11]:
            sade_sati = True

    if mahadasha_problem:
        mahadasha_statement = f"महादशा के कारण जीवन में उतार-चढ़ाव संभव हैं क्योंकि {ruling_planet} एक पाप ग्रह है।"
        mahadasha_resolution = f"{ruling_planet} की शांति हेतु \"{planet_mantras[ruling_planet]}\" मंत्र का 108 बार जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"
    else:
        mahadasha_statement = "महादशा अनुकूल है और जीवन में स्थिरता लाएगी।"
        mahadasha_resolution = f"{ruling_planet} का आशीर्वाद बनाए रखने हेतु \"{planet_mantras[ruling_planet]}\" मंत्र का नियमित जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"

    if sade_sati:
        sade_sati_statement = "साढ़ेसाती के प्रभाव से जीवन में कठिनाइयाँ आ सकती हैं क्योंकि शनि चंद्रमा के निकट है।"
        sade_sati_resolution = "शनि देव की कृपा हेतु शनिवार को \"ॐ शं शनैश्चराय नमः\" मंत्र का 108 बार जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"
    else:
        sade_sati_statement = "साढ़ेसाती का प्रभाव न्यूनतम है।"
        sade_sati_resolution = "शनि देव का आशीर्वाद बनाए रखने हेतु \"ॐ शं शनैश्चराय नमः\" मंत्र का नियमित जाप करें। (विस्तृत जानकारी के लिए आप हमारी वेबसाइट https://astrologerinranchi.com से व्यक्तिगत कुंडली ऑर्डर कर सकते हैं।)"

    mahadasha_sadesati_response = {
        "mahadasha_problem": {
            "statement": mahadasha_statement,
            "resolution": mahadasha_resolution
        },
        "sade_sati_problem": {
            "statement": sade_sati_statement,
            "resolution": sade_sati_resolution
        }
    }

    response = jsonify({
        "name": name,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_place": birth_place,
        "mulyank": mulyank,
        "latitude": lat,
        "longitude": lon,
        "birth_julian_day": birth_jd,
        "ayanamsa_lahiri": ayanamsa - 0.88,
        "sunrise_julian_day": sunrise_jd,
        "sunrise_time": converted_sunrise_time,
        "ist_kaal": ist_kaal,
        "lagna_degree": lagna_degree,
        "lagna_rashi": lagna_rashi,
        "janam_nakshatra": janam_nakshatra,
        "janam_charan": janam_charan,
        "rashi": rashi,
        "rashi_naam_start_from": planet_positions["चंद्र"]["naming_letter"],
        "gana": janam_gana,
        "lagna_chart": lagna_chart,
        "chandra_chart": chandra_chart,
        "planet_positions": planet_positions,
        "shubh_din": lucky_day,
        "ishta_devta": ishta_devta,
        "lucky_number": lucky_number,
        "lucky_date": lucky_dates_str,
        "lucky_color": lucky_color,
        "bhagyavardhak_ratna": bhagyavardhak,
        "jeevan_rakshak_ratna": jeevan_rakshak,
        "vidya_vardhak_ratna": vidya_vardhak,
        "mangal_dosha": mangal_dosha_details,
        "kaalsarp_dosha": kaalsarp_details,
        "mahadasha": {"starting_planet": ruling_planet, "balance": mahadasha_balance},
        "predictions": {
            "study": study_response,
            "money": money_response,
            "work": work_response,
            "marriage": marriage_response,
            "mahadasha_sadesati": mahadasha_sadesati_response
        },
        "lagna_image": lagna_image_url,
        "chandra_image": chandra_image_url
    })
    response.headers.add('Access-Control-Allow-Origin', 'https://astrologerinranchi.com')
    logger.debug("Response prepared successfully")
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)