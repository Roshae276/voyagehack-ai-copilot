from pymongo import MongoClient
from datetime import datetime
from datetime import timedelta


# ===============================
# CONNECTION
# ===============================

MONGO_URL = "mongodb+srv://roshae276_db_user:Roshni123@voyagehack-cluster.csdbros.mongodb.net/voyagehack?retryWrites=true&w=majority&appName=voyagehack-cluster"
DB_NAME = "voyagehack"

client = MongoClient(MONGO_URL)

db = client[DB_NAME]
CACHE_EXPIRY_HOURS = 24

# Collections
search_collection = db["searches"]
hotel_collection = db["hotel_results"]
booking_collection = db["bookings"]
analytics_collection = db["analytics"]


# ===============================
# SAVE SEARCH
# ===============================

def save_search(data):

    record = {

        "destination": data.get("destination"),
        "checkin": data.get("checkin"),
        "checkout": data.get("checkout"),
        "budget": data.get("budget"),
        "travelers": data.get("travelers"),
        "rooms": data.get("rooms"),
        "confidence_score": data.get("confidence_score"),
        "created_at": datetime.utcnow()

    }

    return search_collection.insert_one(record)


# ===============================
# SAVE HOTEL RESULTS
# ===============================

def save_hotels(destination, checkin, checkout, travelers, hotels):

    try:

        hotel_collection.update_one(

            {

                "destination": destination,

                "checkin": checkin,

                "checkout": checkout,

                "travelers": travelers

            },

            {

                "$set": {

                    "destination": destination,

                    "checkin": checkin,

                    "checkout": checkout,

                    "travelers": travelers,

                    "hotels": hotels,

                    "created_at": datetime.utcnow()

                }

            },

            upsert=True

        )

    except Exception as e:

        print("Cache save error:", e)


# ===============================
# SAVE BOOKING
# ===============================

def save_booking(data):

    record = {

        "data": data,
        "created_at": datetime.utcnow()

    }

    return booking_collection.insert_one(record)


# ===============================
# ANALYTICS UPDATE
# ===============================

def update_analytics(commission):

    analytics_collection.update_one(

        {"type": "commission"},

        {
            "$inc": {
                "total_commission": commission,
                "total_searches": 1
            }
        },

        upsert=True
    )
def get_previous_search(destination):

    return search_collection.find_one(
        {"destination": destination},
        sort=[("created_at", -1)]
    )  
    
# ===============================
# GET CACHED HOTELS
# ===============================

def get_cached_hotels(destination, checkin, checkout, travelers):

    try:

        return hotel_collection.find_one({

            "destination": destination,

            "checkin": checkin,

            "checkout": checkout,

            "travelers": travelers

        })

    except Exception as e:

        print("Cache read error:", e)

        return None  
    
from datetime import timedelta


CACHE_EXPIRY_HOURS = 24


# ===============================
# CACHE VALIDATION
# ===============================

def is_cache_valid(record):

    if not record:
        return False

    created = record.get("created_at")

    if not created:
        return False

    expiry = created + timedelta(hours=CACHE_EXPIRY_HOURS)

    return datetime.utcnow() < expiry


# ===============================
# GET VALID CACHED HOTELS
# ===============================

def get_valid_cached_hotels(destination, checkin, checkout, travelers):

    record = get_cached_hotels(destination, checkin, checkout, travelers)

    if record and is_cache_valid(record):
        return record

    return None


# ===============================
# FLIGHT CACHE COLLECTION
# ===============================

flight_collection = db["flight_results"]


def save_flights(origin, destination, date, flights):

    try:

        flight_collection.update_one(

            {
                "origin": origin,
                "destination": destination,
                "date": date
            },

            {
                "$set": {
                    "origin": origin,
                    "destination": destination,
                    "date": date,
                    "flights": flights,
                    "created_at": datetime.utcnow()
                }
            },

            upsert=True
        )

    except Exception as e:

        print("Flight cache save error:", e)


def get_cached_flights(origin, destination, date):

    try:

        record = flight_collection.find_one({

            "origin": origin,
            "destination": destination,
            "date": date

        })

        if record and is_cache_valid(record):
            return record

    except Exception as e:

        print("Flight cache read error:", e)

    return None 

# ===============================
# GET VALID CACHED HOTELS (WITH EXPIRY)
# ===============================

def get_valid_cached_hotels(destination, checkin, checkout, travelers):

    try:

        record = hotel_collection.find_one({

            "destination": destination,
            "checkin": checkin,
            "checkout": checkout,
            "travelers": travelers

        })

        if not record:
            return None

        created = record.get("created_at")

        if not created:
            return None

        if datetime.utcnow() - created > timedelta(hours=CACHE_EXPIRY_HOURS):

            print("Hotel cache expired")

            return None

        print("Hotel cache valid")

        return record

    except Exception as e:

        print("Hotel cache error:", e)

        return None
    
# ===============================
# GET VALID CACHED FLIGHTS
# ===============================

def get_valid_cached_flights(origin, destination, date):

    try:

        record = db["flight_results"].find_one({

            "origin": origin,
            "destination": destination,
            "date": date

        })

        if not record:
            return None

        created = record.get("created_at")

        if not created:
            return None

        if datetime.utcnow() - created > timedelta(hours=CACHE_EXPIRY_HOURS):

            print("Flight cache expired")

            return None

        print("Flight cache valid")

        return record

    except Exception as e:

        print("Flight cache error:", e)

        return None           