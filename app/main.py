# app/main.py
import json
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from app.models import AnalysisRequest, AnalysisResponse, ChatRequest
from app.services import pagespeed_service, processing_service, llm_service

# --- Application State ---
class AppState:
    full_report: Optional[Dict[str, Any]] = None
    llm_summary: Optional[str] = None

app_state = AppState()

# --- FastAPI App Initialization ---
app = FastAPI(
    title="FrontendX Performance-Pal",
    description="An API to benchmark website performance and provide AI-driven optimization tips.",
    version="1.0.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---
@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_website(request: AnalysisRequest):
    """
    Receives a URL, runs PageSpeed Insights, and returns key metrics.
    The full report is stored in-memory for subsequent chat and download requests.
    """
    # Get the performance data from Google PageSpeed Insights
    report = await pagespeed_service.get_pagespeed_insights(request.url, request.strategy)
    
    # Store the full report and the LLM summary in our simple state
    app_state.full_report = report
    llm_summary = processing_service.extract_info_for_llm(report)
    app_state.llm_summary = processing_service.format_for_llm(llm_summary, request.url) 

    initial_suggestion = await llm_service.get_initial_suggestion(app_state.llm_summary)

    # Extract key metrics for the frontend to display immediately
    lighthouse_result = report.get("lighthouseResult", {})
    performance_score = lighthouse_result.get("categories", {}).get("performance", {}).get("score", 0) * 100
    key_metrics = processing_service.extract_key_metrics(report)

    return AnalysisResponse(
        performance_score=int(performance_score),
        metrics=key_metrics,
        initial_suggestion=initial_suggestion
    )

@app.post("/api/chat")
async def chat_with_llm(request: ChatRequest = Body(...)):
    """
    Handles the chat interface. Streams responses from the LLM.
    """
    if not app_state.llm_summary:
        raise HTTPException(status_code=400, detail="Please analyze a website first before starting a chat.")
    
    # The user's most recent message is the last one in the history list
    user_query = request.history[-1].content if request.history else ""
    chat_history = request.history[:-1] # The history is all messages except the last one

    stream = llm_service.get_llm_stream(chat_history, user_query, app_state.llm_summary)
    return StreamingResponse(stream, media_type="text/event-stream")


@app.get("/api/download-report")
async def download_full_report():
    """
    Allows the user to download the full, raw JSON report from PageSpeed Insights.
    """
    if not app_state.full_report:
        raise HTTPException(status_code=400, detail="No report available to download. Please analyze a website first.")
    
    report_json_str = json.dumps(app_state.full_report, indent=2)
    
    return Response(
        content=report_json_str,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=lighthouse_report.json"}
    )

# A simple root endpoint to confirm the API is running
@app.get("/")
def read_root():
    return {"message": "Welcome to the FrontendX Performance-Pal API"}

