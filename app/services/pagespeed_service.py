# app/services/pagespeed_service.py
import httpx
from typing import Dict, Any, Literal
from fastapi import HTTPException

from app.core.config import settings

API_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

async def get_pagespeed_insights(url: str, strategy: Literal["mobile", "desktop"]) -> Dict[str, Any]:
    """
    Asynchronously calls the Google PageSpeed Insights API.

    Args:
        url: The target website URL.
        strategy: The analysis strategy ('mobile' or 'desktop').

    Returns:
        The parsed JSON response as a dictionary.
        
    Raises:
        HTTPException: If the API call fails or returns an error.
    """
    params = {"url": url, "key": settings.PAGESPEED_API_KEY, "strategy": strategy}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(API_ENDPOINT, params=params, timeout=60.0)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()
            
            if "error" in data:
                error_message = data["error"].get("message", "Unknown API error")
                raise HTTPException(status_code=400, detail=f"PageSpeed API Error: {error_message}")

            if "lighthouseResult" not in data:
                 raise HTTPException(status_code=500, detail="Invalid response from PageSpeed API: 'lighthouseResult' not found.")

            return data

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error calling PageSpeed API: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=500, detail=f"Network error while calling PageSpeed API: {e}"
            )
