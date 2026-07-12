"""
doctor_finder.py
-----------------
Finds nearby doctors/health centers relevant to a user's screening result
using the Google Places API (New) Text Search endpoint.

Maps the screened disease to a relevant medical specialty, then searches
"<specialty> near <location>" and returns a clean list of results.

NOTE: This never influences or overrides the ML prediction — it's a
purely informational lookup based on the disease name from an already
completed screening.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Disease name (from prediction_result["disease"]) -> specialty search term
DISEASE_TO_SPECIALTY = {
    "Heart Disease": "cardiologist heart specialist",
    "Diabetes": "endocrinologist diabetes specialist",
}

FIELD_MASK = ",".join([
    "places.displayName",
    "places.formattedAddress",
    "places.rating",
    "places.userRatingCount",
    "places.internationalPhoneNumber",
    "places.googleMapsUri",
    "places.location",
])


def find_nearby_doctors(disease: str, location: str, max_results: int = 8):
    """
    disease: e.g. "Heart Disease" or "Diabetes" (from the screening result)
    location: free-text place name typed by the user, e.g. "Vijayawada" or
              "Koramangala, Bangalore"
    Returns: dict with "specialty" and "results" (list of place dicts),
             or raises RuntimeError with a user-facing message on failure.
    """
    if not PLACES_API_KEY:
        raise RuntimeError(
            "Doctor search isn't configured yet — GOOGLE_PLACES_API_KEY is missing."
        )

    if not location:
        raise RuntimeError("Please enter a location to search near.")

    specialty = DISEASE_TO_SPECIALTY.get(disease, "general physician doctor")
    text_query = f"{specialty} near {location}"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": PLACES_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    payload = {
        "textQuery": text_query,
        "maxResultCount": max_results,
    }

    try:
        response = requests.post(PLACES_SEARCH_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Could not reach the location search service: {e}")

    places = data.get("places", [])
    if not places:
        return {"specialty": specialty, "results": []}

    results = []
    for p in places:
        results.append({
            "name": p.get("displayName", {}).get("text", "Unknown"),
            "address": p.get("formattedAddress", ""),
            "rating": p.get("rating"),
            "review_count": p.get("userRatingCount"),
            "phone": p.get("internationalPhoneNumber"),
            "maps_url": p.get("googleMapsUri"),
        })

    return {"specialty": specialty, "results": results}