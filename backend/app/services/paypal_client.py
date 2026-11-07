"""
PayPal Developer Platform REST API Client.
Handles OAuth2 token caching, Invoicing v2, verified capture retrieval,
safe batch payouts with duplicate error recovery, and unclaimed item cancellation.
"""
import time
import logging
import httpx
from typing import Optional, Any
from app.config import settings

logger = logging.getLogger("splitflow.paypal")

class PayPalAPIError(Exception):
    def __init__(self, message: str, status_code: int = 500, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class PayPalClient:
    def __init__(self):
        self.base_url = settings.PAYPAL_API_BASE.rstrip("/")
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0

    def get_access_token(self) -> str:
        """
        Fetches or returns a cached OAuth2 Bearer token from PayPal.
        Refreshes token 60 seconds before expiration.
        """
        now = time.time()
        if self._cached_token and now < self._token_expires_at - 60:
            return self._cached_token

        if not self.client_id or not self.client_secret:
            raise PayPalAPIError("PayPal Client ID or Secret is not configured in settings.", 500)

        url = f"{self.base_url}/v1/oauth2/token"
        headers = {"Accept": "application/json", "Accept-Language": "en_US"}
        data = {"grant_type": "client_credentials"}

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, data=data, auth=(self.client_id, self.client_secret))

            if resp.status_code != 200:
                raise PayPalAPIError(
                    f"PayPal OAuth2 token exchange failed: {resp.text}",
                    status_code=resp.status_code,
                    response_data=resp.json() if resp.headers.get("content-type") == "application/json" else resp.text
                )

            token_data = resp.json()
            self._cached_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 32400)  # Default 9 hours
            self._token_expires_at = now + expires_in
            return self._cached_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    # =========================================================================
    # INVOICING API (v2)
    # =========================================================================
    def create_invoice(self, invoice_payload: dict) -> dict:
        """Creates a draft invoice in PayPal Invoicing v2."""
        url = f"{self.base_url}/v2/invoicing/invoices"
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=self._headers(), json=invoice_payload)
            if resp.status_code not in [200, 201]:
                raise PayPalAPIError(f"Create invoice failed: {resp.text}", resp.status_code, resp.text)
            return resp.json()

    def send_invoice(self, invoice_id: str) -> dict:
        """Dispatches an invoice to the client."""
        url = f"{self.base_url}/v2/invoicing/invoices/{invoice_id}/send"
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=self._headers(), json={"send_to_recipient": True})
            if resp.status_code not in [200, 202]:
                raise PayPalAPIError(f"Send invoice failed: {resp.text}", resp.status_code, resp.text)
            return resp.json() if resp.content else {"status": "SENT"}

    def get_invoice(self, invoice_id: str) -> dict:
        """Retrieves invoice details including payments.transactions[]."""
        url = f"{self.base_url}/v2/invoicing/invoices/{invoice_id}"
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=self._headers())
            if resp.status_code != 200:
                raise PayPalAPIError(f"Get invoice failed: {resp.text}", resp.status_code, resp.text)
            return resp.json()

    # =========================================================================
    # PAYMENTS & CAPTURES (v2)
    # =========================================================================
    def get_capture(self, capture_id: str) -> dict:
        """
        Retrieves PayPal capture resource to extract seller_receivable_breakdown (gross, fee, net).
        """
        url = f"{self.base_url}/v2/payments/captures/{capture_id}"
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=self._headers())
            if resp.status_code != 200:
                raise PayPalAPIError(f"Get capture failed for {capture_id}: {resp.text}", resp.status_code, resp.text)
            return resp.json()

    # =========================================================================
    # WEBHOOK SIGNATURE VERIFICATION
    # =========================================================================
    def verify_webhook_signature(
        self,
        transmission_id: str,
        transmission_time: str,
        cert_url: str,
        auth_algo: str,
        transmission_sig: str,
        raw_body: str
    ) -> bool:
        """
        Validates webhook payload authenticity with PayPal's verification endpoint.
        """
        if not settings.PAYPAL_WEBHOOK_ID:
            logger.warning("PAYPAL_WEBHOOK_ID not set; skipping signature verification in dev mode.")
            return True

        url = f"{self.base_url}/v1/notifications/verify-webhook-signature"
        payload = {
            "transmission_id": transmission_id,
            "transmission_time": transmission_time,
            "cert_url": cert_url,
            "auth_algo": auth_algo,
            "transmission_sig": transmission_sig,
            "webhook_id": settings.PAYPAL_WEBHOOK_ID,
            "webhook_event": raw_body
        }

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=self._headers(), json=payload)
            if resp.status_code != 200:
                logger.error(f"Webhook verification API error: {resp.text}")
                return False
            data = resp.json()
            return data.get("verification_status") == "SUCCESS"

    # =========================================================================
    # PAYOUTS API (v1) & RESILIENT BATCH DISPATCH
    # =========================================================================
    def create_batch_payout(self, payout_payload: dict) -> dict:
        """
        Submits a batch payout.
        If PayPal returns HTTP 400 with BATCH_ALREADY_EXISTS / DUPLICATE_REQUEST,
        catches the error and retrieves the existing batch resource.
        """
        url = f"{self.base_url}/v1/payments/payouts"
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, headers=self._headers(), json=payout_payload)

            if resp.status_code in [200, 201]:
                return resp.json()

            # Catch duplicate batch submission
            if resp.status_code == 400:
                data = resp.json()
                err_name = data.get("name")
                if err_name in ["DUPLICATE_REQUEST", "BATCH_ALREADY_EXISTS"]:
                    logger.info("Batch already submitted to PayPal. Locating existing batch details...")
                    # Search links for the existing batch ID
                    for link in data.get("links", []):
                        if link.get("rel") == "batch":
                            batch_href = link.get("href")
                            batch_resp = client.get(batch_href, headers=self._headers())
                            if batch_resp.status_code == 200:
                                return batch_resp.json()
                    
                    # Alternatively, if sender_batch_id was used, query directly
                    sender_batch_id = payout_payload.get("sender_batch_header", {}).get("sender_batch_id")
                    if sender_batch_id:
                        return self.get_payout_batch(sender_batch_id)

            raise PayPalAPIError(f"Create payout batch failed: {resp.text}", resp.status_code, resp.text)

    def get_payout_batch(self, payout_batch_id: str) -> dict:
        """Retrieves status and fees for a payout batch."""
        url = f"{self.base_url}/v1/payments/payouts/{payout_batch_id}"
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=self._headers())
            if resp.status_code != 200:
                raise PayPalAPIError(f"Get payout batch failed: {resp.text}", resp.status_code, resp.text)
            return resp.json()

    def get_payout_item(self, payout_item_id: str) -> dict:
        """Retrieves individual item status (SUCCESS, FAILED, UNCLAIMED, RETURNED)."""
        url = f"{self.base_url}/v1/payments/payouts-item/{payout_item_id}"
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=self._headers())
            if resp.status_code != 200:
                raise PayPalAPIError(f"Get payout item failed: {resp.text}", resp.status_code, resp.text)
            return resp.json()

    def cancel_unclaimed_payout_item(self, payout_item_id: str) -> dict:
        """
        Cancels an unclaimed payout item.
        PayPal transitions the status to RETURNED and refunds the sender's balance.
        """
        url = f"{self.base_url}/v1/payments/payouts-item/{payout_item_id}/cancel"
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=self._headers())
            if resp.status_code not in [200, 202]:
                raise PayPalAPIError(f"Cancel unclaimed payout item failed: {resp.text}", resp.status_code, resp.text)
            return resp.json()

paypal_client = PayPalClient()

