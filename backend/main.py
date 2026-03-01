import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from payment import generate_payment_link
from pdf_generator import generate_quote_pdf
from fastapi.staticfiles import StaticFiles
from pdf_generator import generate_user_pdf, generate_agent_pdf
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os

load_dotenv()

# MongoDB
from mongo import (
    save_search,
    save_hotels,
    update_analytics,
    get_previous_search,
    get_cached_hotels,
    get_valid_cached_hotels,
    save_flights,
    get_valid_cached_flights
)

# ===============================
# CONFIG
# ===============================

TBO_BASE_URL = "https://api.tbotechnology.in/TBOHolidays_HotelAPI"
auth = HTTPBasicAuth("hackathontest", "Hac@98147521")

TBO_AIR_AUTH_URL = "http://Sharedapi.tektravels.com/SharedData.svc/rest/Authenticate"

TBO_AIR_SEARCH_URL = "http://api.tektravels.com/BookingEngineService_Air/AirService.svc/rest/Search"



TBO_AIR_USERNAME = "Hackathon"

TBO_AIR_PASSWORD = "Hackathon@1234"

TBO_ENDUSER_IP = "127.0.0.1"

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

REQUEST_TIMEOUT = 15

app = FastAPI()
app.mount("/quotes", StaticFiles(directory="quotes"), name="quotes")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================
# AIRPORT CODE CACHE
# ===============================

airport_code_map = {

    "delhi": "DEL",
    "mumbai": "BOM",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "hyderabad": "HYD",
    "chennai": "MAA",
    "kolkata": "CCU",
    "goa": "GOI",
    "pune": "PNQ",
    "dubai": "DXB",
    "singapore": "SIN",
    "maldives": "MLE",
    "london": "LON"

}

def get_airport_code(city):

    if not city:
        return None

    return airport_code_map.get(city.lower())
# ===============================
# GLOBAL CACHES
# ===============================

city_cache = None
hotel_code_cache = {}
hotel_name_cache = {}

# ===============================
# MODEL
# ===============================

class BookingRequest(BaseModel):
    text: str

# ===============================
# AI EXTRACTION (FIXED)
# ===============================

def extract_booking_data(text: str):

    data = {}

    try:

        today = datetime.today().strftime("%Y-%m-%d")

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""
Return STRICT JSON with keys:

destination
checkin
checkout
budget
travelers
rooms
confidence_score
alert
ai_summary

Today: {today}

Rules:
- budget must be number
- travelers must be number
- rooms must be number
- confidence_score must be 0-100 number
- Never return strings like "Not specified"
- Never return null
"""
                },
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )

        content = res.choices[0].message.content

        if content:
            data = json.loads(content)

    except Exception as e:
        print("AI error:", e)

    # ===============================
    # SAFE TYPE NORMALIZATION
    # ===============================

    def to_int(value, default):

        try:

            if value is None:
                return default

            if isinstance(value, str):

                v = value.strip().lower()

                if v in ["not specified", "none", "null", "", "unknown"]:
                    return default

                return int(float(v))

            if isinstance(value, float) or isinstance(value, int):
                return int(value)

        except:
            pass

        return default

    # ===============================
    # FIELD NORMALIZATION
    # ===============================

    data["destination"] = str(
        data.get("destination") or ""
    ).strip()

    data["checkin"] = str(
        data.get("checkin")
        or data.get("check_in")
        or ""
    ).strip()

    data["checkout"] = str(
        data.get("checkout")
        or data.get("check_out")
        or ""
    ).strip()

    data["travelers"] = to_int(
        data.get("travelers") or data.get("guests"),
        1
    )

    data["rooms"] = to_int(
        data.get("rooms"),
        1
    )

    data["budget"] = to_int(
        data.get("budget"),
        0
    )

    confidence = data.get("confidence_score")

    if isinstance(confidence, float) and confidence <= 1:
        confidence = confidence * 100

    data["confidence_score"] = to_int(confidence, 85)

    data["alert"] = str(
        data.get("alert") or ""
    )

    data["ai_summary"] = str(
        data.get("ai_summary") or ""
    )

    # ===============================
    # SAVE SEARCH (SAFE)
    # ===============================

    try:
        save_search(data)
    except Exception as e:
        print("Save search error:", e)

    # ===============================
    # MEMORY INSIGHT (SAFE)
    # ===============================

    try:

        previous = get_previous_search(data["destination"])

        if previous and previous.get("destination"):

            data["memory_insight"] = (
                f"User previously searched "
                f"{previous['destination']} "
                f"with budget {previous.get('budget', 0)}."
            )

        else:

            data["memory_insight"] = "No previous booking history."

    except Exception as e:

        print("Memory error:", e)

        data["memory_insight"] = ""

    return data
# ===============================
# CITY CODE (CACHED)
# ===============================

def find_city_code(city_name):

    global city_cache

    if not city_name:
        return None

    city_name = city_name.lower()

    if city_cache is None:

        city_cache = []

        for country in ["IN","SG","AE","MV","TH","ID"]:

            try:
                res = requests.post(
                    f"{TBO_BASE_URL}/CityList",
                    auth=auth,
                    json={"CountryCode": country},
                    timeout=REQUEST_TIMEOUT
                )

                city_cache.extend(res.json().get("CityList", []))

            except:
                pass

    for city in city_cache:
        if city_name in city["Name"].lower():
            return city["Code"]

    return None

# ===============================
# HOTEL CODES (CACHED)
# ===============================

def fetch_hotel_codes(city_code):

    if city_code in hotel_code_cache:
        return hotel_code_cache[city_code]

    try:

        res = requests.post(
            f"{TBO_BASE_URL}/TBOHotelCodeList",
            auth=auth,
            json={"CityCode": city_code},
            timeout=REQUEST_TIMEOUT
        )

        hotels = res.json().get("Hotels", [])

        codes = [
            str(h["HotelCode"])
            for h in hotels
            if h.get("HotelCode")
        ][:80]

        hotel_code_cache[city_code] = codes

        return codes

    except:
        return []

# ===============================
# HOTEL NAME CACHE (CRITICAL FIX)
# ===============================

def fetch_hotel_details(code):

    if code in hotel_name_cache:
        return hotel_name_cache[code]

    try:

        res = requests.post(
            f"{TBO_BASE_URL}/HotelDetails",
            auth=auth,
            json={
                "Hotelcodes": str(code),
                "Language": "EN"
            },
            timeout=REQUEST_TIMEOUT
        )

        data = res.json()

        if data.get("HotelDetails"):
            name = data["HotelDetails"][0]["HotelName"]
            hotel_name_cache[code] = name
            return name

    except:
        pass

    return f"Hotel-{code}"

# ===============================
# HOTEL SEARCH
# ===============================

def search_tbo_hotels(codes, checkin, checkout, adults):

    results = []

    for i in range(0, len(codes), 80):

        batch = codes[i:i+80]

        try:

            res = requests.post(
                f"{TBO_BASE_URL}/Search",
                auth=auth,
                json={
                    "CheckIn": checkin,
                    "CheckOut": checkout,
                    "HotelCodes": ",".join(batch),
                    "GuestNationality": "IN",
                    "PaxRooms":[{"Adults": adults,"Children":0}],
                    "ResponseTime": 8,
                    "IsDetailedResponse": False
                },
                timeout=REQUEST_TIMEOUT
            )

            results.extend(
                res.json().get("HotelResult", [])
            )

        except:
            continue

    return {"HotelResult": results}

# ===============================
# COMMISSION ENGINE
# ===============================

def calculate_commission(hotel_response):

    hotels = []

    for hotel in hotel_response.get("HotelResult", []):

        code = hotel.get("HotelCode")

        name = (
            hotel.get("HotelName")
            or hotel.get("HotelInfo",{}).get("HotelName")
        )

        if not name:
            name = fetch_hotel_details(code)

        for room in hotel.get("Rooms", []):

            selling = float(
                room.get("RecommendedSellingRate")
                or room.get("TotalFare")
                or 0
            )

            if selling <= 0:
                continue

            base = float(
                room.get("BasePrice")
                or selling*0.85
            )

            commission = selling-base

            hotels.append({

                "HotelName": name,
                "HotelCode": code,

                "RoomName":
                    room.get("Name")[0]
                    if room.get("Name")
                    else "Room",

                "SellingPrice": round(selling,2),
                "Commission": round(commission,2),

                "CommissionPercent":
                    round(commission/selling*100,2)
            })

    hotels.sort(
        key=lambda x:x["Commission"],
        reverse=True
    )

    return hotels[:10]

# ===============================
# TBO AIR AUTH
# ===============================

def tbo_air_authenticate():

    try:

        url = "http://Sharedapi.tektravels.com/SharedData.svc/rest/Authenticate"

        payload = {
            "ClientId": "ApiIntegrationNew",
            "UserName": "Hackathon",
            "Password": "Hackathon@1234",
            "EndUserIp": "127.0.0.1"
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        print("AUTH STATUS:", response.status_code)
        print("AUTH RAW:", repr(response.text))

        if not response.text.strip():
            print("Empty auth response")
            return None

        data = json.loads(response.content.decode("utf-8-sig"))

        if data.get("Status") == 1:
            print("AUTH SUCCESS")
            return data.get("TokenId")

        print("AUTH FAILED:", data)
        return None

    except Exception as e:

        print("Auth exception:", e)
        return None

# ===============================
# FLIGHT SEARCH (FINAL WORKING)
# ===============================

# ===============================
# FINAL WORKING TBO AIR SEARCH
# ===============================

def search_tbo_flights(origin, destination, date, passengers):

    try:

        token = tbo_air_authenticate()

        if not token:
            print("Auth failed")
            return []

        print("Calling TBO Search...")

        payload = {

            "EndUserIp": TBO_ENDUSER_IP,

            "TokenId": token,

            "AdultCount": int(passengers),

            "ChildCount": 0,

            "InfantCount": 0,

            "DirectFlight": False,

            "OneStopFlight": False,

            "JourneyType": 1,  # one-way

            "PreferredAirlines": None,

            "Segments": [
                {
                    "Origin": origin,
                    "Destination": destination,
                    "FlightCabinClass": 1,
                    "PreferredDepartureTime": f"{date}T00:00:00.0000000",
                    "PreferredArrivalTime": f"{date}T00:00:00.0000000"
                }
            ],

            "Sources": ["GDS"],

            "PreferredCurrency": "INR"
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(
            TBO_AIR_SEARCH_URL,
            json=payload,
            headers=headers,
            timeout=30
        )

        print("SEARCH STATUS:", response.status_code)
        print("SEARCH RAW:", response.text[:500])

        data = json.loads(response.content.decode("utf-8-sig"))

        if data.get("Response") and data["Response"].get("ResponseStatus") == 1:

            flights = []

            for group in data["Response"]["Results"]:
                flights.extend(group)

            print("FLIGHTS FOUND:", len(flights))

            return flights

        print("NO FLIGHTS FOUND")

        return []

    except Exception as e:

        print("SEARCH ERROR:", e)

        return []
# ===============================
# COMMISSION ENGINE (FINAL)
# ===============================

def calculate_flight_commission(results):

    flights = []

    for flight in results:

        try:

            fare = flight["Fare"]

            selling = fare["PublishedFare"]

            base = selling * 0.90

            commission = selling - base

            airline = flight["Segments"][0][0]["Airline"]["AirlineName"]

            flights.append({

                "Airline": airline,

                "SellingPrice": round(selling, 2),

                "Commission": round(commission, 2),

                "CommissionPercent": round(commission/selling*100, 2)

            })

        except:
            continue

    flights.sort(key=lambda x: x["Commission"], reverse=True)

    print("Commission flights:", len(flights))

    return flights[:10]


# ===============================
# MAIN FLIGHT ENDPO
# ===============================
# PROCESS ENDPOINT (RESTORED)
# ===============================

@app.post("/process")
async def process_booking(request: BookingRequest):

    try:

        data = extract_booking_data(request.text)

        return {
            "AI_Extracted": data,
            "status": "success"
        }

    except Exception as e:

        print("Process endpoint error:", e)

        return {
            "AI_Extracted": {},
            "status": "error",
            "error": str(e)
        }

# ===============================
# MAIN ENDPOINT (WITH CACHE)
# ===============================

@app.post("/tbo/ai-search-hotels")
async def ai_search_hotels(request: BookingRequest):

    try:

        ai_data = extract_booking_data(request.text)

        destination = ai_data["destination"]

        city_code = find_city_code(destination)

        if not city_code:

            return {
                "AI_Extracted": ai_data,
                "TopProfitHotels":[]
            }

        cached = get_valid_cached_hotels(
            destination,
            ai_data["checkin"],
            ai_data["checkout"],
            ai_data["travelers"]
        )

        if cached and cached.get("hotels"):

            best = cached["hotels"]

            print("Loaded from Mongo cache")

        else:

            codes = fetch_hotel_codes(city_code)

            results = search_tbo_hotels(
                codes,
                ai_data["checkin"],
                ai_data["checkout"],
                ai_data["travelers"]
            )

            best = calculate_commission(results)

            save_hotels(
                destination,
                ai_data["checkin"],
                ai_data["checkout"],
                ai_data["travelers"],
                best
            )

        if best:
            update_analytics(best[0]["Commission"])

        return {

            "AI_Extracted": ai_data,

            "NormalizedDestination": destination,

            "CityCode": city_code,

            "TotalHotelsFound": len(best),

            "TopProfitHotels": best
        }

    except Exception as e:

        print("Search error:", e)

        return {
            "AI_Extracted": {},
            "TopProfitHotels":[],
            "error": str(e)
        }
        
# ===============================
# AI FLIGHT SEARCH ENDPOINT
# ===============================

# ===============================
# AI FLIGHT SEARCH ENDPOINT (FIXED)
# ===============================


@app.post("/tbo/ai-search-flights")
async def ai_search_flights(request: BookingRequest):

    try:

        ai_data = extract_booking_data(request.text)

        origin = "DEL"

        destination = get_airport_code(
            ai_data["destination"]
        )

        if not destination:

            return {

                "AI_Extracted": ai_data,

                "TopFlights": []
            }

        cached = get_valid_cached_flights(
            origin,
            destination,
            ai_data["checkin"]
        )

        if cached and cached.get("flights"):

            print("Loaded flights from cache")

            best = cached["flights"]

        else:

            results = search_tbo_flights(
                origin,
                destination,
                ai_data["checkin"],
                ai_data["travelers"]
            )

            best = calculate_flight_commission(
                results
            )

            save_flights(
                origin,
                destination,
                ai_data["checkin"],
                best
            )

        return {

            "AI_Extracted": ai_data,

            "Origin": origin,

            "Destination": destination,

            "TotalFlightsFound": len(best),

            "TopFlights": best
        }

    except Exception as e:

        print("Flight endpoint error:", e)

        return {

            "AI_Extracted": {},

            "TopFlights": [],

            "error": str(e)
        }
        
# ===============================
# UNIFIED AI TRIP SEARCH (HOTEL + FLIGHT)
# ===============================

@app.post("/tbo/ai-search-trip")
async def ai_search_trip(request: BookingRequest):

    try:

        ai_data = extract_booking_data(request.text)

        destination = ai_data["destination"]
        origin = "DEL"

        airport_code = get_airport_code(destination)

        # ===============================
        # HOTEL SEARCH
        # ===============================

        hotels = []

        city_code = find_city_code(destination)

        if city_code:

            cached_hotels = get_valid_cached_hotels(
                destination,
                ai_data["checkin"],
                ai_data["checkout"],
                ai_data["travelers"]
            )

            if cached_hotels and cached_hotels.get("hotels"):

                hotels = cached_hotels["hotels"]

                print("Hotels from cache")

            else:

                codes = fetch_hotel_codes(city_code)

                hotel_results = search_tbo_hotels(
                    codes,
                    ai_data["checkin"],
                    ai_data["checkout"],
                    ai_data["travelers"]
                )

                hotels = calculate_commission(hotel_results)

                save_hotels(
                    destination,
                    ai_data["checkin"],
                    ai_data["checkout"],
                    ai_data["travelers"],
                    hotels
                )

        # ===============================
        # FLIGHT SEARCH
        # ===============================

        flights = []

        if airport_code:

            cached_flights = get_valid_cached_flights(
                origin,
                airport_code,
                ai_data["checkin"]
            )

            if cached_flights and cached_flights.get("flights"):

                flights = cached_flights["flights"]

                print("Flights from cache")

            else:

                flight_results = search_tbo_flights(
                    origin,
                    airport_code,
                    ai_data["checkin"],
                    ai_data["travelers"]
                )

                flights = calculate_flight_commission(
                    flight_results
                )

                save_flights(
                    origin,
                    airport_code,
                    ai_data["checkin"],
                    flights
                )

        # ===============================
        # TOTAL CALCULATIONS
        # ===============================

        hotel_price = hotels[0]["SellingPrice"] if hotels else 0
        flight_price = flights[0]["SellingPrice"] if flights else 0

        total_price = hotel_price + flight_price

        hotel_commission = hotels[0]["Commission"] if hotels else 0
        flight_commission = flights[0]["Commission"] if flights else 0

        total_commission = hotel_commission + flight_commission
        payment_link = generate_payment_link(total_price, ai_data)

        # ===============================
        # RECOMMENDED OPTION
        # ===============================

        recommendation = "hotel+flight"

        if total_commission > 0:
            recommendation = "high-profit-trip"

        # ===============================
        # RESPONSE
        # ===============================

        return {

            "AI_Extracted": ai_data,

            "FlightsFound": len(flights),
            "HotelsFound": len(hotels),

            "TopFlights": flights,
            "TopHotels": hotels,

            "TotalTripPrice": round(total_price, 2),

            "TotalCommission": round(total_commission, 2),
            
            "PaymentLink": payment_link,

            "Recommendation": recommendation
            

        }

    except Exception as e:

        print("Trip search error:", e)

        return {
            "error": str(e)
        }        


# ===============================
# DEBUG AUTH ENDPOINT
# ===============================


@app.post("/generate-quote-pdf")
async def generate_pdf(request: BookingRequest):

    trip = await ai_search_trip(request)

    payment_link = trip.get("PaymentLink")

    file = generate_quote_pdf(trip, payment_link)

    return {

        "pdf_file": file,

        "payment_link": payment_link,

        "status": "success"
    }
    
@app.post("/send-whatsapp-quote")
async def whatsapp_quote(request: BookingRequest):

    trip = await ai_search_trip(request)

    payment_link = trip.get("PaymentLink")

    # USER SAFE MESSAGE (NO COMMISSION)
    message = (
    f"VoyageHack Travel Quote\n\n"
    f"Destination: {trip.get('AI_Extracted', {}).get('destination')}\n"
    f"Total Price: ₹{trip.get('TotalTripPrice')}\n\n"
    f"Payment Link:\n{payment_link}\n\n"
    f"Powered by VoyageHack AI"
    )

    whatsapp_link = (
        f"https://wa.me/?text={message}"
    )

    return {

        "WhatsAppLink": whatsapp_link,

        "PaymentLink": payment_link,

        "status": "success"
    } 
    
    
@app.post("/generate-user-pdf")
async def generate_user_pdf_endpoint(request: BookingRequest):

    trip = await ai_search_trip(request)

    payment_link = trip.get("PaymentLink")

    file = generate_user_pdf(trip, payment_link)

    return {
        "pdf_file": file
    }  
    
@app.post("/generate-agent-pdf")
async def generate_agent_pdf_endpoint(request: BookingRequest):

    trip = await ai_search_trip(request)

    file = generate_agent_pdf(trip)

    return {
        "pdf_file": file
    }     
    
# ===============================
# ANALYTICS DASHBOARD ENDPOINT
# ===============================

@app.get("/analytics-dashboard")
def analytics_dashboard():

    try:

        from mongo import analytics_collection

        data = analytics_collection.find_one(
            {"type": "commission"}
        )

        total_revenue = 0
        total_searches = 0

        if data:

            total_revenue = data.get(
                "total_commission", 0
            )

            total_searches = data.get(
                "total_searches", 0
            )

        return {

            "status": "success",

            "total_revenue": round(total_revenue, 2),

            "total_searches": total_searches,

            "avg_revenue_per_search":
                round(
                    total_revenue / total_searches, 2
                ) if total_searches > 0 else 0

        }

    except Exception as e:

        return {

            "status": "error",

            "message": str(e)
        }    
       
# ===============================
# DASHBOARD PAGE ENDPOINT
# ===============================

@app.get("/dashboard")
def dashboard_page():

    return FileResponse("dashboard.html")       
    

@app.get("/")
def root():

    return {"status": "VoyageHack Running"}