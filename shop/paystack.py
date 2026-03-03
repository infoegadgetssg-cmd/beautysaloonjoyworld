# shop/paystack.py
import requests
from django.conf import settings

class Paystack:
    """Paystack API integration"""
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"
    
    def initialize_transaction(self, email, amount, reference, callback_url=None, metadata=None):
        """Initialize a Paystack transaction [citation:9]"""
        amount_in_kobo = int(amount * 100)  # Convert to kobo [citation:9]
        
        payload = {
            "email": email,
            "amount": amount_in_kobo,
            "reference": reference,
            "callback_url": callback_url,
            "metadata": metadata or {}
        }
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.base_url}/transaction/initialize",
            json=payload,
            headers=headers
        )
        
        return response.json()
    
    def verify_transaction(self, reference):
        """Verify a Paystack transaction [citation:1]"""
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{self.base_url}/transaction/verify/{reference}",
            headers=headers
        )
        
        return response.json()
    
    def verify_webhook_signature(self, payload, signature):
        """Verify webhook signature for security [citation:4]"""
        import hmac
        import hashlib
        
        computed_signature = hmac.new(
            settings.PAYSTACK_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(computed_signature, signature)
    
    