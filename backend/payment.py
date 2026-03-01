import time
import hashlib

BASE_PAYMENT_URL = "https://pay.voyagehack.com/quote"

def generate_payment_link(amount, trip_data=None):

    timestamp = str(time.time())

    unique = hashlib.md5(
        (timestamp + str(amount)).encode()
    ).hexdigest()[:10]

    payment_id = f"VH{unique}"

    payment_link = f"{BASE_PAYMENT_URL}/{payment_id}"

    return payment_link