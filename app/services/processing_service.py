# app/services/processing_service.py
from typing import Dict, Any, List
from app.models import Metric

def extract_key_metrics(data: Dict[str, Any]) -> List[Metric]:
    """
    Extracts key performance metrics for frontend display.

    Args:
        data: The parsed JSON response from the Lighthouse report.

    Returns:
        A list of Metric objects containing the title and value of each key metric.
    """

    audits = data.get("lighthouseResult", {}).get("audits", {})
    metrics_to_extract = [
        "first-contentful-paint", "speed-index", "largest-contentful-paint",
        "interactive", "total-blocking-time", "cumulative-layout-shift"
    ]

    extracted_metrics = []
    for metric_id in metrics_to_extract:
        metric_data = audits.get(metric_id, {})
        extracted_metrics.append(
            Metric(
                title=metric_data.get("title", metric_id.replace('-', ' ').title()),
                value=metric_data.get("displayValue", "N/A")
            )
        )
    return extracted_metrics

def extract_info_for_llm(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts key performance indicators from the PageSpeed Insights JSON data.

    Args:
        data: The full JSON response from the API.

    Returns:
        A structured dictionary containing summarized information for the LLM.
    """
    if not isinstance(data, dict):
        raise TypeError("Input data must be a dictionary.")

    lighthouse_result = data.get("lighthouseResult", {})
    if not lighthouse_result:
        return {}

    audits = lighthouse_result.get("audits", {})
    extracted_info = {
        "summary": {},
        "metrics": [],
        "opportunities": [],
        "diagnostics": {}
    }

    # 1. Overall Performance Score
    performance_category = lighthouse_result.get("categories", {}).get("performance", {})
    if performance_category.get("score") is not None:
        extracted_info["summary"]["performance_score"] = performance_category["score"] * 100

    # 2. Core Web Vitals and Key Metrics
    metric_ids = [
        "largest-contentful-paint",
        "total-blocking-time",
        "cumulative-layout-shift",
        "first-contentful-paint",
        "speed-index"
        "interactive"
    ]
    for metric_id in metric_ids:
        metric_audit = audits.get(metric_id)
        if metric_audit:
            extracted_info["metrics"].append({
                "title": metric_audit.get("title"),
                "value": metric_audit.get("displayValue")
            })

    # 3. Actionable Opportunities (with potential savings)
    for audit_id, audit in audits.items():
        details = audit.get("details", {})
        # Check if it's an opportunity with measurable savings or actionable items
        if details.get("type") == "opportunity" and (details.get("overallSavingsMs", 0) > 0 or details.get("items", [])):
            opportunity = {
                "title": audit.get("title"),
                "description": audit.get("description"),
                "savings": audit.get("displayValue", ""),
                "items": []
            }
            # Extract specific items for context
            for item in details.get("items", []):
                if audit_id == "bootup-time":
                    opportunity["items"].append(f"  - Script: {item.get('url')}, CPU Time: {item.get('total'):.0f}ms")
                elif audit_id == "image-delivery-insight" and item.get('subItems'):
                    reason = item['subItems']['items'][0].get('reason', 'Optimization needed')
                    opportunity["items"].append(f"  - Image: {item.get('url')}, Reason: {reason}")
            extracted_info["opportunities"].append(opportunity)

    # 4. Key Diagnostics
    # Critical Request Chains
    crc_audit = audits.get("critical-request-chains", {})
    if crc_audit and crc_audit.get("details"):
        longest_chain = crc_audit["details"].get("longestChain", {})
        if longest_chain:
            extracted_info["diagnostics"]["critical_request_chains"] = (
                f"Longest chain: {longest_chain.get('length')} requests, "
                f"taking {longest_chain.get('duration'):.0f}ms."
            )

    # Resource Summary
    rs_audit = audits.get("resource-summary", {})
    if rs_audit and rs_audit.get("details", {}).get("items"):
        summary_items = []
        for item in rs_audit["details"]["items"]:
            if item.get("resourceType") in ["total", "script", "image", "font", "third-party"]:
                size_kb = item.get('transferSize', 0) / 1024
                summary_items.append(
                    f"  - {item.get('label')}: {item.get('requestCount')} requests, {size_kb:.0f} KB"
                )
        extracted_info["diagnostics"]["resource_summary"] = "\n".join(summary_items)
    
    return extracted_info

def format_for_llm(extracted_data: Dict[str, Any], url: str) -> str:
    """
    Formats the extracted data into a clean, readable string for the LLM prompt.
    """
    if not extracted_data:
        return "No performance data could be extracted."

    prompt_lines = ["--- Performance Summary Report for URL: " + url + " ---"]
    
    # Summary
    score = extracted_data["summary"].get("performance_score")
    if score is not None:
        prompt_lines.append(f"Overall Score: {score:.0f}/100")
    
    # Core Metrics
    prompt_lines.append("\n--- Core Metrics ---")
    for metric in extracted_data.get("metrics", []):
        prompt_lines.append(f"- {metric.get('title')}: {metric.get('value')}")
        
    # Opportunities
    prompt_lines.append("\n--- Top Opportunities for Improvement ---")
    opportunities = extracted_data.get("opportunities", [])
    if not opportunities:
        prompt_lines.append("No significant opportunities were identified.")
    else:
        for opp in opportunities:
            prompt_lines.append(f"\n- {opp['title']} ({opp.get('savings', 'Action required')})")
            prompt_lines.extend(opp.get("items", []))

    # Diagnostics
    prompt_lines.append("\n--- Key Diagnostics ---")
    diagnostics = extracted_data.get("diagnostics", {})
    if not diagnostics:
        prompt_lines.append("No key diagnostics available.")
    else:
        if "critical_request_chains" in diagnostics:
            prompt_lines.append(f"- Critical Request Chains: {diagnostics['critical_request_chains']}")
        if "resource_summary" in diagnostics:
            prompt_lines.append("- Resource Breakdown:\n" + diagnostics['resource_summary'])
            
    return "\n".join(prompt_lines)

