import os
from dotenv import load_dotenv
from twilio.rest import Client
load_dotenv()
def send_otp_sms(phone, otp):
    account_sid = "AC57db65901e98a7a5fc6f2c49a9dc15cf"
    auth_token = "538a357e17a9cef101811732027802bc"
    twilio_phone = "+12295754614"

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