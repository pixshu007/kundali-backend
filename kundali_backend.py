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
import json  # Ensure json is imported
import re
import math

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

swe.set_sid_mode(swe.SIDM_LAHIRI)
app = Flask(__name__)
# Allow CORS for all routes, specifically from your frontend domain
CORS(app, resources={r"/*": {"origins": "https://astrologerinranchi.com"}}, supports_credentials=True)

# Add a custom handler for OPTIONS requests (if needed)
@app.route('/kundali', methods=['OPTIONS'])
def handle_options():
    response = jsonify({"status": "ok"})
    response.headers['Access-Control-Allow-Origin'] = 'https://astrologerinranchi.com'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Define STATIC_FOLDER (adjust path as needed)
STATIC_FOLDER = "static"

# Placeholder sanitize_filename function
def sanitize_filename(filename):
    invalid_chars = r'[<>:"/\\|?*]+'
    sanitized = re.sub(invalid_chars, '-', filename)
    sanitized = sanitized.strip().strip('.')
    return sanitized

# Set up logging so we can track what’s happening
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define planet symbols and their colors
planet_symbols = {
    "सूर्य": ("सु", "darkred"),
    "चंद्र": ("च", "navy"),
    "मंगल": ("मं", "darkorange"),
    "बुध": ("बु", "forestgreen"),
    "बृहस्पति": ("गु", "darkgoldenrod"),
    "शुक्र": ("शु", "magenta"),
    "शनि": ("श", "darkslategray"),
    "राहु": ("र", "purple"),
    "केतु": ("के", "teal")
}

# Helper function to clean filenames
def sanitize_filename(filename):
    return "".join(c for c in filename if c.isalnum() or c in ['_', '-', '.'])

# Main function to draw the chart
def draw_north_indian_chart(chart_data, title, filename):
    try:
        # Clear any previous plot
        plt.clf()
        plt.close()

        # Add a timestamp to the filename
        timestamp = int(time.time() * 1000)
        filename = f"{filename.split('.png')[0]}_{timestamp}.png"
        sanitized_filename = sanitize_filename(filename)
        filepath = os.path.join("static", sanitized_filename)  # Adjust path as needed
        logger.debug(f"Saving chart to: {filepath}")

        # Load Hindi font (you’ll need this file in a 'fonts' folder)
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansDevanagari-Regular.ttf")
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"Font file not found at {font_path}")
        hindi_font = fm.FontProperties(fname=font_path)

        # Create the figure
        fig, ax = plt.subplots(figsize=(6, 5.4))
        ax.set_facecolor('white')
        ax.axis('off')

        # Draw the chart lines (North Indian style)
        line_color = '#D4A017'
        linewidth = 2
        ax.plot([0, 0, 1, 1, 0], [0, 1, 1, 0, 0], color=line_color, linewidth=linewidth)
        ax.plot([0, 1], [0, 1], color=line_color, linewidth=linewidth)
        ax.plot([1, 0], [0, 1], color=line_color, linewidth=linewidth)
        ax.plot([0.5, 0], [0, 0.5], color=line_color, linewidth=linewidth)
        ax.plot([0.5, 1], [0, 0.5], color=line_color, linewidth=linewidth)
        ax.plot([0, 0.5], [0.5, 1], color=line_color, linewidth=linewidth)
        ax.plot([0.5, 1], [1, 0.5], color=line_color, linewidth=linewidth)

        # Define house bounds for validation
        SYMBOL_SIZE = 0.072  # Updated for fontsize=18
        house_bounds = {
            1: (0.35, 0.65, 0.60, 0.90),   # Center-top (House 1)
            2: (0.65, 0.90, 0.00, 0.20),   # Top-right (House 2)
            3: (0.80, 1.00, 0.15, 0.35),   # Right-top (House 3)
            4: (0.65, 0.90, 0.35, 0.65),   # Right-middle (House 4)
            5: (0.80, 1.00, 0.65, 0.85),   # Right-bottom (House 5)
            6: (0.65, 0.90, 0.80, 1.00),   # Bottom-right (House 6)
            7: (0.35, 0.65, 0.10, 0.40),   # Bottom-center (House 7)
            8: (0.10, 0.35, 0.80, 1.00),   # Bottom-left (House 8)
            9: (0.00, 0.20, 0.65, 0.85),   # Left-top (House 9)
            10: (0.10, 0.35, 0.35, 0.65),  # Left-middle (House 10)
            11: (0.00, 0.20, 0.15, 0.35),  # Top-left (House 11)
            12: (0.10, 0.35, 0.00, 0.20)   # Top-middle (House 12)
        }

        # Provided coordinates for rashi numbers and planet symbols (with adjustments)
        provided_coordinates = {
            1: {
                "rashi": (0.4940, 0.7620),
                "planets": [
                    (0.3540, 0.7520), (0.4940, 0.8760), (0.6120, 0.7620),
                    (0.5040, 0.6260), (0.4360, 0.7020)
                ]
            },
            8: {
                "rashi": (0.2460, 0.8660),  # Adjusted from (0.246, 0.846)
                "planets": [
                    (0.1320, 0.9180), (0.1920, 0.9160), (0.2640, 0.9180),  # Adjusted from (0.948, 0.946, 0.948)
                    (0.3360, 0.9180)
                ]
            },
            9: {
                "rashi": (0.1540, 0.7560),
                "planets": [
                    (0.0460, 0.8660), (0.0540, 0.8040), (0.0600, 0.7400),
                    (0.0580, 0.6740)
                ]
            },
            10: {
                "rashi": (0.2460, 0.5100),
                "planets": [
                    (0.1200, 0.5080), (0.1780, 0.5720), (0.2560, 0.6360),
                    (0.3660, 0.5080), (0.2480, 0.3920)
                ]
            },
            11: {
                "rashi": (0.1520, 0.2440),
                "planets": [
                    (0.0520, 0.3620), (0.0560, 0.3020), (0.0600, 0.2320),
                    (0.0580, 0.1560)
                ]
            },
            12: {
                "rashi": (0.2500, 0.1480),
                "planets": [
                    (0.1880, 0.0960), (0.1800, 0.0760), (0.2460, 0.0600),  # Adjusted from (0.14, 0.056)
                    (0.3380, 0.0600)
                ]
            },
            7: {
                "rashi": (0.5020, 0.2800),
                "planets": [
                    (0.4980, 0.3720), (0.4140, 0.3060), (0.3800, 0.2100),
                    (0.4920, 0.1440), (0.6180, 0.2580)
                ]
            },
            2: {
                "rashi": (0.7500, 0.1580),
                "planets": [
                    (0.6980, 0.1020), (0.6520, 0.0620), (0.7480, 0.0540),
                    (0.8400, 0.0680)
                ]
            },
            3: {
                "rashi": (0.8360, 0.2520),
                "planets": [
                    (0.9420, 0.3540), (0.9280, 0.2800), (0.9300, 0.2040),
                    (0.9340, 0.1540)
                ]
            },
            4: {
                "rashi": (0.7500, 0.5000),
                "planets": [
                    (0.6300, 0.5040), (0.6860, 0.5740), (0.7620, 0.6200),
                    (0.8580, 0.5080), (0.7560, 0.3900)
                ]
            },
            5: {
                "rashi": (0.8380, 0.7540),
                "planets": [
                    (0.8940, 0.7940), (0.9380, 0.8500), (0.9220, 0.7040),
                    (0.9420, 0.6500)
                ]
            },
            6: {
                "rashi": (0.7460, 0.8500),
                "planets": [
                    (0.6800, 0.9100), (0.7220, 0.9400), (0.7900, 0.9420),
                    (0.8480, 0.9260)
                ]
            }
        }

        # Rashi to number mapping
        rashi_to_number = {
            "मेष": 1, "वृष": 2, "मिथुन": 3, "कर्क": 4, "सिंह": 5, "कन्या": 6,
            "तुला": 7, "वृश्चिक": 8, "धनु": 9, "मकर": 10, "कुंभ": 11, "मीन": 12
        }

        # House mapping (JSON house to chart house)
        inverse_permutation = {
            1: 1, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12,
            7: 7, 8: 2, 9: 3, 10: 4, 11: 5, 12: 6
        }

        # Place Rashi numbers at provided coordinates
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
            ax.text(rashi_x, rashi_y, str(rashi_number), ha='center', va='center', color='black', fontsize=18, fontweight='bold')  # Updated to 18
            logger.debug(f"Placed Rashi {rashi} (number {rashi_number}) at ({rashi_x}, {rashi_y}) in chart house {chart_house}")

        # Place planets at provided coordinates
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

            # Get the provided planet coordinates
            planet_coords = provided_coordinates[chart_house]["planets"]
            num_planets = len(planets)
            num_coords = len(planet_coords)

            if num_planets > num_coords:
                logger.warning(f"House {chart_house}: More planets ({num_planets}) than coordinates ({num_coords}). Using first {num_coords} planets.")
                planets = planets[:num_coords]
            elif num_planets < num_coords:
                logger.debug(f"House {chart_house}: Fewer planets ({num_planets}) than coordinates ({num_coords}). Using first {num_planets} coordinates.")
                planet_coords = planet_coords[:num_planets]

            # Get house bounds for validation
            x_min, x_max, y_min, y_max = house_bounds[chart_house]
            padding = 0.06  # Increased padding
            x_min += padding
            x_max -= padding
            y_min += padding
            y_max -= padding
            x_min, x_max = min(x_min, x_max), max(x_min, x_max)
            y_min, y_max = min(y_min, y_max), max(y_min, y_max)

            # Place the planets
            for idx, planet in enumerate(planets):
                if planet not in planet_symbols:
                    logger.error(f"Planet {planet} not found in planet_symbols")
                    continue
                pos_x, pos_y = planet_coords[idx]
                # Validate position
                if not (x_min <= pos_x <= x_max and y_min <= pos_y <= y_max):
                    logger.warning(f"House {chart_house}: Planet {planet} at ({pos_x}, {pos_y}) is outside bounds ({x_min}, {x_max}, {y_min}, {y_max})")
                symbol, color = planet_symbols[planet]
                ax.text(pos_x, pos_y, symbol, ha='center', va='center', color=color, fontsize=18, fontproperties=hindi_font)  # Updated to 18
                logger.debug(f"Placed {planet} ({symbol}) at ({pos_x}, {pos_y}) in chart house {chart_house}")

        # Save the chart
        plt.savefig(filepath, bbox_inches='tight', facecolor='white', dpi=130)
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
        geolocator = Nominatim(user_agent="kundali_app")
        location = geolocator.geocode(birth_place)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Error in get_lat_lon: {e}")
        return None, None

def convert_to_julian(birth_date, birth_time):
    year, month, day = map(int, birth_date.split('-'))
    hour, minute = map(int, birth_time.split(':'))
    jd = swe.julday(year, month, day, hour + (minute / 60.0) - 5.5)  # IST to UTC
    print(f"Debug: Calculated JD for {day}-{month}-{year} {hour}:{minute} IST = {jd}")
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
        print(f"Error in julian_to_time: {e}")
        return "Calculation Error"

def get_sunrise_time(julian_day, lat, lon):
    try:
        print(f"Debug: Input to get_sunrise_time -> JD: {julian_day}, Lat: {lat}, Lon: {lon}")
        jd_ut = float(julian_day)
        geopos = (lon, lat, 0)
        res, tret = swe.rise_trans(jd_ut, swe.SUN, swe.CALC_RISE, geopos)
        if res == 0 and isinstance(tret, tuple):
            sunrise_jd = tret[0]
            print(f"Debug: Calculated Sunrise JD = {sunrise_jd}")
            return sunrise_jd
        raise ValueError("Sunrise calculation failed")
    except Exception as e:
        print(f"Error in get_sunrise_time: {e}")
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
        print(f"✅ Debug: Calculated Ist Kaal = {ist_kaal}")
        return ist_kaal
    except Exception as e:
        print(f"Error in calculate_ist_kaal: {e}")
        return None

def compute_lagna(birth_jd, lat, lon, ayanamsa):
    sidereal_time = (swe.sidtime(birth_jd) * 15 + lon) % 360
    print(f"Debug: Sidereal Time = {sidereal_time}°")
    houses, ascmc = swe.houses(birth_jd, lat, lon, b'A')
    ascendant_degree = float(ascmc[0])
    print(f"Debug: Swiss Ephemeris Ascendant Degree = {ascendant_degree}°")
    ascendant_degree_corrected = (ascendant_degree - ayanamsa) % 360
    print(f"Debug: Corrected Ascendant Degree After Ayanamsa = {ascendant_degree_corrected}°")
    rashi_names = ["मेष", "वृष", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक",
                   "धनु", "मकर", "कुंभ", "मीन"]
    lagna_sign_index = int(ascendant_degree_corrected // 30) % 12
    lagna_rashi = rashi_names[lagna_sign_index]
    print(f"Debug: Assigned Lagna Rashi = {lagna_rashi}")
    print(f"Debug: Lagna Degree = {ascendant_degree_corrected}°")
    print(f"Debug: Lagna Rashi = {lagna_rashi}")
    return ascendant_degree_corrected, lagna_rashi
    
    # Define nakshatra_letters globally
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
# ... (other functions like get_lat_lon, convert_to_julian, etc., remain unchanged)

nakshatras = [
    "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशीर्ष", "आर्द्रा", "पुनर्वसु", "पुष्य", "आश्लेषा",
    "मघा", "पूर्वा फाल्गुनी", "उत्तरा फाल्गुनी", "हस्त", "चित्रा", "स्वाति", "विशाखा", "अनुराधा", "ज्येष्ठा",
    "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा", "पूर्वाभाद्रपद", "उत्तराभाद्रपद", "रेवती"
]

# Mapping of Nakshatras to Gana
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

ruling_planets = ["केतु", "शुक्र", "सूर्य", "चंद्र", "मंगल", "राहु", "गुरु", "शनि", "बुध"]

mahadasha_periods = {
    "केतु": 7,
    "शुक्र": 20,
    "सूर्य": 6,
    "चंद्र": 10,
    "मंगल": 7,
    "राहु": 18,
    "गुरु": 16,
    "शनि": 19,
    "बुध": 17
}

# Rashi to Lord mapping (moved from compute_planet_positions)
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

# Define Dusthana houses (6, 8, 12) for checking planetary strength
dusthana_houses = [6, 8, 12]

# Define malefic and benefic planets
malefics = ["मंगल", "शनि", "राहु", "केतु"]
benefics = ["बृहस्पति", "शुक्र"]

# Rashi to Lucky Day mapping
rashi_lucky_days = {
    "मेष": "मंगलवार",
    "वृषभ": "शुक्रवार",
    "मिथुन": "बुधवार",
    "कर्क": "सोमवार",
    "सिंह": "रविवार",
    "कन्या": "बुधवार",
    "तुला": "शुक्रवार",
    "वृश्चिक": "मंगलवार, सोमवार",  # Special case with two days
    "धनु": "गुरुवार",
    "मकर": "शनिवार",
    "कुंभ": "शनिवार",
    "मीन": "गुरुवार"
}

# Rashi to Ishta Devta mapping (used for 12th house ruler)
rashi_ishta_devta = {
    "मेष": "पंचमुखी हनुमान",
    "वृषभ": "भवानी शंकर",
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

# Rashi to Rashi Number (for Lucky Date)
rashi_numbers = {
    "मेष": 1,
    "वृषभ": 2,
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

# Planet (Rashi Lord) to Lucky Color
planet_lucky_colors = {
    "मंगल": "लाल",          # Mars - Red
    "शुक्र": "सफेद",        # Venus - White
    "बुध": "हरा",           # Mercury - Green
    "चंद्र": "सफेद",        # Moon - White
    "सूर्य": "नारंगी",      # Sun - Orange
    "बृहस्पति": "पीला",     # Jupiter - Yellow
    "शनि": "नीला"           # Saturn - Blue
}

# भाग्यवर्धक रत्न (Lucky Gemstone) based on 1st house (Lagna)
bhagyavardhak_ratna = {
    "मेष": "पीत पुखराज 4.5 रत्ती",
    "वृषभ": "ब्रजमनी ब्लू 5 रत्ती",
    "मिथुन": "ब्रजमनी ब्लू 5 रत्ती",
    "कर्क": "पीत पुखराज 4.5 रत्ती",
    "सिंह": "मूँगा रक्त इटालियन 7 रत्ती",
    "कन्या": "ब्रजमनी सफ़ेद 5 रत्ती",
    "तुला": "पन्ना ब्राज़ीली 4.5 रत्ती",
    "वृश्चिक": "नेचुरल मोती 5 रत्ती (चांदी में)",
    "धनु": "माणिक 5 रत्ती",
    "मकर": "पन्ना ब्राज़ीली 4.5 रत्ती",
    "कुंभ": "ब्रजमनी सफ़ेद 5 रत्ती",
    "मीन": "मूँगा रक्त इटालियन 7 रत्ती"
}

# जीवन रक्षक रत्न (Life-Saving Gemstone) based on 9th house
jeevan_rakshak_ratna = {
    "मेष": "मूँगा रक्त इटालियन 7 रत्ती",
    "वृषभ": "ब्रजमनी सफ़ेद 5 रत्ती",
    "मिथुन": "पन्ना ब्राज़ीली 4.5 रत्ती",
    "कर्क": "नेचुरल मोती 5 रत्ती (चांदी में)",
    "सिंह": "माणिक 5 रत्ती",
    "कन्या": "पन्ना ब्राज़ीली 4.5 रत्ती",
    "तुला": "डायमंड 50 सेंट अभाव में सफ़ेद बज्रमणि 5 रत्ती",
    "वृश्चिक": "मूँगा रक्त इटालियन 7 रत्ती गोल्ड या ब्रॉन्ज़ में",
    "धनु": "पीत पुखराज 4.5 रत्ती",
    "मकर": "ब्रजमनी ब्लू 5 रत्ती",
    "कुंभ": "ब्रजमनी ब्लू 5 रत्ती",
    "मीन": "पीत पुखराज 4.5 रत्ती"
}

# विद्या वर्धक रत्न (Education-Enhancing Gemstone) based on 5th house
vidya_vardhak_ratna = {
    "मेष": "मूँगा रक्त इटालियन 7 रत्ती",
    "वृषभ": "ब्रजमनी सफ़ेद 5 रत्ती",
    "मिथुन": "पन्ना ब्राज़ीली 4.5 रत्ती",
    "कर्क": "नेचुरल मोती 5 रत्ती (चांदी में)",
    "सिंह": "माणिक 5 रत्ती",
    "कन्या": "पन्ना ब्राज़ीली 4.5 रत्ती",
    "तुला": "डायमंड 50 सेंट अभाव में सफ़ेद बज्रमणि 5 रत्ती",
    "वृश्चिक": "मूँगा रक्त इटालियन 7 रत्ती गोल्ड या ब्रॉन्ज़ में",
    "धनु": "पीत पुखराज 4.5 रत्ती",
    "मकर": "ब्रजमनी ब्लू 5 रत्ती",
    "कुंभ": "ब्रजमनी ब्लू 5 रत्ती",
    "मीन": "पीत पुखराज 4.5 रत्ती"
}

def calculate_nakshatra_and_charan(sidereal_pos):
    nakshatra_degrees = 13.3333  # 13°20'
    charan_degrees = 3.3333      # 3°20'
    
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
        print(f"Debug: {planet} raw result = {result}")
        tropical_pos = float(result[0][0])
        print(f"Debug: {planet} tropical_pos = {tropical_pos}")
        sidereal_pos = (tropical_pos - ayanamsa) % 360
        sign_index = int(sidereal_pos // 30) % 12
        sign = rashi_names[sign_index]
        if planet == "केतु":
            sidereal_pos = (sidereal_pos + 180) % 360
            sign_index = int(sidereal_pos // 30) % 12
            sign = rashi_names[sign_index]
        
        nakshatra, charan = calculate_nakshatra_and_charan(sidereal_pos)
        
        naming_letter = None
        if planet == "चंद्र":  # Only calculate naming letter for Moon
            naming_letter = get_naming_letter(nakshatra, charan)
        
        positions[planet] = {
            "degree": sidereal_pos,
            "sign": sign,
            "sign_number": sign_index + 1,
            "rashi": sign,
            "rashi_number": sign_index + 1,
            "rashi_lord": rashi_lord[sign],  # Corrected to fetch the lord for the specific rashi
            "nakshatra": nakshatra,
            "charan": charan,
            "naming_letter": naming_letter if naming_letter else None,
        }
        print(f"Debug: {planet} = {sidereal_pos}° in {sign}")
    return positions

def build_north_indian_chart(lagna_sign_index, moon_sign_index, planet_positions):
    """Build Lagna and Chandra Charts in North Indian style with Hindi names"""
    rashi_names = ["मेष", "वृष", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक",
                   "धनु", "मकर", "कुंभ", "मीन"]
    
    # Convert 0-based indices to 1-based sign numbers
    lagna_sign_number = lagna_sign_index + 1
    moon_sign_number = moon_sign_index + 1
    
    # Initialize charts with sign names
    lagna_chart = {i: {"sign": rashi_names[(lagna_sign_index + i - 1) % 12], "planets": []} for i in range(1, 13)}
    chandra_chart = {i: {"sign": rashi_names[(moon_sign_index + i - 1) % 12], "planets": []} for i in range(1, 13)}
    
    # Fill planets into houses
    for planet, data in planet_positions.items():
        sign_number = data["sign_number"]
        # Calculate house relative to Lagna
        lagna_house = (sign_number - lagna_sign_number) % 12 + 1
        # Calculate house relative to Moon
        chandra_house = (sign_number - moon_sign_number) % 12 + 1
        lagna_chart[lagna_house]["planets"].append(planet)
        chandra_chart[chandra_house]["planets"].append(planet)
    
    return lagna_chart, chandra_chart
    
@app.route('/kundali', methods=['POST', 'OPTIONS'])
def calculate_kundali():
    if request.method == 'OPTIONS':
    response = jsonify({"status": "ok"})
    response.status_code = 200  # Use 200 instead of 204 for debugging
    response.headers['Access-Control-Allow-Origin'] = 'https://astrologerinranchi.com'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
    response.headers['Access-Control-Max-Age'] = '86400'
    return response
        
    cleanup_static_folder()    
    data = request.json
    name = data.get("name")
    birth_date = data.get("birth_date")  # Format: YYYY-MM-DD
    birth_time = data.get("birth_time")
    birth_place = data.get("birth_place")

    if not birth_date or not birth_time or not birth_place:
        return jsonify({"error": "Missing required fields"}), 400

    lat, lon = get_lat_lon(birth_place)
    if lat is None or lon is None:
        return jsonify({"error": "Invalid birth place"}), 400

    birth_jd = convert_to_julian(birth_date, birth_time)
    ayanamsa = swe.get_ayanamsa_ut(birth_jd)
    print(f"Debug: Birth Date = {birth_date} {birth_time} IST")
    print(f"Debug: Birth JD = {birth_jd}")
    print(f"Debug: Ayanamsa = {ayanamsa}")

    lagna_degree, lagna_rashi = compute_lagna(birth_jd, lat, lon, ayanamsa)
    lagna_sign_index = ["मेष", "वृष", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक",
                        "धनु", "मकर", "कुंभ", "मीन"].index(lagna_rashi)

    planet_positions = compute_planet_positions(birth_jd, ayanamsa)
    moon_sign_index = planet_positions["चंद्र"]["sign_number"] - 1
    lagna_chart, chandra_chart = build_north_indian_chart(lagna_sign_index, moon_sign_index, planet_positions)
    
    # Generate dynamic charts
    sanitized_name = sanitize_filename(name)
    lagna_filename = f"lagna_{sanitized_name}_{birth_date}_{birth_time}.png".replace(" ", "_").replace(":", "-")
    chandra_filename = f"chandra_{sanitized_name}_{birth_date}_{birth_time}.png".replace(" ", "_").replace(":", "-")
    
    # Use the timestamped filenames returned by draw_north_indian_chart
    lagna_filename = draw_north_indian_chart(lagna_chart, "लग्न कुण्डली", lagna_filename)
    chandra_filename = draw_north_indian_chart(chandra_chart, "चंद्र कुण्डली", chandra_filename)

    lagna_image_url = url_for('static', filename=lagna_filename, _external=True)
    chandra_image_url = url_for('static', filename=chandra_filename, _external=True)
    logger.debug(f"Lagna Image URL: {lagna_image_url}, Chandra Image URL: {chandra_image_url}")

    # ... rest of the calculate_kundali function remains unchanged ...

    sunrise_jd = get_sunrise_time(birth_jd, lat, lon)
    if sunrise_jd is None:
        return jsonify({"error": "Failed to calculate sunrise time"}), 500

    converted_sunrise_time = julian_to_time(sunrise_jd, return_only_hour_minute=True)
    ist_kaal = calculate_ist_kaal(birth_time, converted_sunrise_time)
    
    janam_nakshatra = planet_positions["चंद्र"]["nakshatra"]
    janam_charan = planet_positions["चंद्र"]["charan"]
    rashi = planet_positions["चंद्र"]["rashi"]
    
    # Calculate Gana based on Nakshatra
    janam_gana = nakshatra_gana.get(janam_nakshatra, "अज्ञात गण")
    print(f"Debug: Janam Nakshatra = {janam_nakshatra}, Gana = {janam_gana}")
    
    # Calculate Mahadasha
    nakshatra_index = nakshatras.index(janam_nakshatra)
    ruling_planet = ruling_planets[nakshatra_index % 9]
    total_period = mahadasha_periods[ruling_planet]
    moon_sidereal_pos = planet_positions["चंद्र"]["degree"]
    nakshatra_degrees = 13.3333
    proportion_passed = (moon_sidereal_pos % nakshatra_degrees) / nakshatra_degrees
    balance_years = total_period * (1 - proportion_passed)

    # Convert balance to years, months, days
    total_days = balance_years * 365.25
    years = int(total_days // 365.25)
    remaining_days = total_days - years * 365.25
    months = int(remaining_days // 30)
    days = int(remaining_days - months * 30)
    mahadasha_balance = f"{ruling_planet} {years} Y {months} M {days} D"

    # 1. Calculate Lucky Day
    lucky_day = rashi_lucky_days.get(rashi, "Unknown")

    # 2. Calculate Ishta Devta (Ruler of 12th house from Lagna)
    twelfth_house_number = (lagna_sign_index + 11) % 12 + 1  # 12th house from Lagna (1-based)
    twelfth_house_sign = lagna_chart[twelfth_house_number]["sign"]
    # Use the global rashi_lord dictionary defined in compute_planet_positions
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
    twelfth_house_rashi_lord = rashi_lord.get(twelfth_house_sign, "Unknown")
    ishta_devta = rashi_ishta_devta.get(twelfth_house_sign, "Unknown")

    # 3. Calculate Lucky Number
    birth_date_digits = ''.join(filter(str.isdigit, birth_date))
    lucky_number = sum(int(digit) for digit in birth_date_digits)
    while lucky_number > 9:
        lucky_number = sum(int(digit) for digit in str(lucky_number))

    # 4. Calculate Lucky Color
    rashi_lord_for_color = planet_positions["चंद्र"]["rashi_lord"]  # Already a string
    lucky_color = planet_lucky_colors.get(rashi_lord_for_color, "Unknown")

    # 5. Calculate Lucky Date
    birth_day = int(birth_date.split('-')[2])  # Extract day from YYYY-MM-DD
    rashi_number = rashi_numbers.get(rashi, 0)
    lucky_date = birth_day + rashi_number
    if lucky_date > 31:  # Adjust if exceeds month length (simplified)
        lucky_date = lucky_date % 31 or 31

    # 6. Calculate Gemstones based on Lagna Chart
    # भाग्यवर्धक रत्न (1st house - Lagna)
    first_house_sign = lagna_chart[1]["sign"]
    bhagyavardhak = bhagyavardhak_ratna.get(first_house_sign, "Unknown")

    # विद्या वर्धक रत्न (5th house)
    fifth_house_number = (lagna_sign_index + 4) % 12 + 1  # 5th house from Lagna (1-based)
    fifth_house_sign = lagna_chart[fifth_house_number]["sign"]
    vidya_vardhak = vidya_vardhak_ratna.get(fifth_house_sign, "Unknown")

    # जीवन रक्षक रत्न (9th house)
    ninth_house_number = (lagna_sign_index + 8) % 12 + 1  # 9th house from Lagna (1-based)
    ninth_house_sign = lagna_chart[ninth_house_number]["sign"]
    jeevan_rakshak = jeevan_rakshak_ratna.get(ninth_house_sign, "Unknown")
    
    # Mangal Dosha Calculation
    mangal_dosha_houses = [1, 4, 7, 8, 12]  # Houses where Mars causes Mangal Dosha
    kendra_houses = [1, 4, 7, 10]           # Kendra houses for Moon check

    # Find Mars' house
    mars_house = None
    for house in range(1, 13):
        if "मंगल" in lagna_chart[house]["planets"]:
            mars_house = house
            break

    # Check if Mangal Dosha exists
    mangal_dosha = mars_house in mangal_dosha_houses if mars_house else False

    # If Mangal Dosha exists, check conditions to nullify it
    mangal_dosha_details = {"exists": mangal_dosha, "nullified": False, "reasons": []}
    if mangal_dosha:
        # Find Jupiter's house
        jupiter_house = None
        for house in range(1, 13):
            if "बृहस्पति" in lagna_chart[house]["planets"]:
                jupiter_house = house
                break

        # Find Moon's house
        moon_house = None
        for house in range(1, 13):
            if "चंद्र" in lagna_chart[house]["planets"]:
                moon_house = house
                break

        # Find Rahu's house
        rahu_house = None
        for house in range(1, 13):
            if "राहु" in lagna_chart[house]["planets"]:
                rahu_house = house
                break

        # Condition 1: Jupiter aspects Mars
        if jupiter_house:
            jupiter_aspects = [
                (jupiter_house + 4) % 12 or 12,  # 5th house aspect
                (jupiter_house + 6) % 12 or 12,  # 7th house aspect
                (jupiter_house + 8) % 12 or 12   # 9th house aspect
            ]
            if mars_house in jupiter_aspects:
                mangal_dosha_details["nullified"] = True
                mangal_dosha_details["reasons"].append("गुरु मंगल को देख रहा है")

        # Condition 2: Moon in Kendra
        if moon_house in kendra_houses:
            mangal_dosha_details["nullified"] = True
            mangal_dosha_details["reasons"].append("चंद्रमा केंद्र में है")

        # Condition 3: Moon conjunct with Mars
        if moon_house == mars_house:
            mangal_dosha_details["nullified"] = True
            mangal_dosha_details["reasons"].append("चंद्रमा मंगल के साथ है")

        # Condition 4: Rahu conjunct with Mars
        if rahu_house == mars_house:
            mangal_dosha_details["nullified"] = True
            mangal_dosha_details["reasons"].append("राहु मंगल के साथ है")
            
    # Kaalsarp Dosha Calculation
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
        # Normalize houses for circular check (Rahu < Ketu or Ketu < Rahu)
        min_house = min(rahu_house, ketu_house)
        max_house = max(rahu_house, ketu_house)
        
        # Check if all planets are between Rahu and Ketu (one side of the axis)
        all_between = True
        for planet, house in planet_houses.items():
            # Planets should either be between min_house and max_house (clockwise)
            # or outside max_house to min_house (counterclockwise)
            if not ((min_house < house < max_house) or (house < min_house or house > max_house)):
                all_between = False
                break
        
        # If all planets are on one side, check which side
        if all_between:
            kaalsarp_dosha = True
        else:
            # Check the other side (counterclockwise)
            all_between_reverse = all((house < min_house or house > max_house) for house in planet_houses.values())
            kaalsarp_dosha = all_between_reverse

        kaalsarp_details["exists"] = kaalsarp_dosha        

        # Prediction Analysis
        def get_planet_house(planet, lagna_chart):
            for house in range(1, 13):
                if planet in lagna_chart[house]["planets"]:
                    return house
            return None

        # 1. Study (5th House Analysis)
        fifth_house_number = (lagna_sign_index + 4) % 12 + 1  # 5th house
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
            study_statement = f"पढ़ाई में समस्याएं आ सकती हैं क्योंकि {', '.join(study_problem_reasons)}।"
            study_resolution = "समस्या का समाधान 1-3 साल में हो सकता है।"
        else:
            study_statement = "पढ़ाई में कोई बड़ी समस्या नहीं है।"
            study_resolution = "कोई विशेष उपाय की आवश्यकता नहीं है।"

        study_response = {
            "statement": study_statement,
            "resolution": study_resolution
}

        # 2. Money (2nd and 11th Houses Analysis)
        second_house_number = (lagna_sign_index + 1) % 12 + 1  # 2nd house
        second_house_sign = lagna_chart[second_house_number]["sign"]
        second_house_lord = rashi_lord[second_house_sign]
        second_lord_house = get_planet_house(second_house_lord, lagna_chart)

        eleventh_house_number = (lagna_sign_index + 10) % 12 + 1  # 11th house
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
            money_statement = f"धन संबंधी समस्याएं आ सकती हैं क्योंकि {', '.join(money_problem_reasons)}।"
            money_resolution = "समस्या का समाधान 1-2 साल में हो सकता है।"
        else:
            money_statement = "धन संबंधी कोई बड़ी समस्या नहीं है।"
            money_resolution = "कोई विशेष उपाय की आवश्यकता नहीं है।"

        money_response = {
            "statement": money_statement,
            "resolution": money_resolution
}

        # 3. Work/Business (10th House Analysis)
        tenth_house_number = (lagna_sign_index + 9) % 12 + 1  # 10th house
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
            work_statement = f"कार्यक्षेत्र में चुनौतियाँ आ सकती हैं क्योंकि {', '.join(work_problem_reasons)}।"
            work_resolution = "समस्या का समाधान 1-3 साल में हो सकता है।"
        else:
            work_statement = "कार्यक्षेत्र में कोई बड़ी समस्या नहीं है।"
            work_resolution = "कोई विशेष उपाय की आवश्यकता नहीं है।"

        work_response = {
            "statement": work_statement,
            "resolution": work_resolution
}

        # 4. Marriage (7th House Analysis)
        seventh_house_number = (lagna_sign_index + 6) % 12 + 1  # 7th house
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
            marriage_statement = f"विवाह में समस्याएं आ सकती हैं क्योंकि {', '.join(marriage_problem_reasons)}।"
            marriage_resolution = "समस्या का समाधान 1-2 साल में हो सकता है।"
        else:
            marriage_statement = "विवाह में कोई बड़ी समस्या नहीं है।"
            marriage_resolution = "कोई विशेष उपाय की आवश्यकता नहीं है।"

        marriage_response = {
            "statement": marriage_statement,
            "resolution": marriage_resolution
}

        # 5. Mahadasha/Sade Sati Analysis
        mahadasha_problem = ruling_planet in malefics  # If current Mahadasha planet is malefic
        moon_house = get_planet_house("चंद्र", lagna_chart)
        saturn_house = get_planet_house("शनि", lagna_chart)
        sade_sati = False
        if moon_house and saturn_house:
            relative_position = (saturn_house - moon_house) % 12
        if relative_position in [0, 1, 11]:  # Saturn in 12th, 1st, or 2nd from Moon
            sade_sati = True

        if mahadasha_problem:
            mahadasha_statement = f"महादशा के कारण समस्याएं आ सकती हैं क्योंकि वर्तमान महादशा ग्रह {ruling_planet} एक पाप ग्रह है।"
            mahadasha_resolution = "समस्या का समाधान अगली महादशा तक हो सकता है।"
        else:
            mahadasha_statement = "महादशा के कारण कोई बड़ी समस्या नहीं है।"
            mahadasha_resolution = "कोई विशेष उपाय की आवश्यकता नहीं है।"

        if sade_sati:
            sade_sati_statement = "साढ़ेसाती के कारण जीवन में कठिनाइयाँ आ सकती हैं क्योंकि शनि चंद्र से निकट स्थिति में है।"
            sade_sati_resolution = "समस्या का समाधान 7.5 साल तक हो सकता है।"
        else:
            sade_sati_statement = "साढ़ेसाती के कारण कोई बड़ी समस्या नहीं है।"
            sade_sati_resolution = "कोई विशेष उपाय की आवश्यकता नहीं है।"

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
        "lucky_color": lucky_color,
        "lucky_date": f"{lucky_date} तारीख",
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