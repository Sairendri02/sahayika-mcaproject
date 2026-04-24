import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

def send_otp_sms(phone, otp):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_phone = os.environ.get("TWILIO_PHONE")

    client = Client(account_sid, auth_token)
    try:
        client.messages.create(
            body=f"Your Sahayika OTP is {otp}. Valid for 5 minutes.",
            from_=twilio_phone,
            to="+91" + phone
        )
        print("OTP SENT SUCCESS")
    except Exception as e:
        print("TWILIO ERROR:", e)