"""Spend report parsing utilities for Kion MCP Server."""

from typing import Dict, Any, Tuple, Optional


def calculate_final_spend(spend_info: Dict[str, Any], spend_type: str, deduct_credits: bool, deduct_refunds: bool) -> Tuple[float, float, float]:
    """Calculate final spend amount with credits and refunds.
    
    Returns:
        Tuple of (final_spend, credits, refunds) as floats.
    """
    if spend_type == "attributed":
        base_spend = spend_info.get("attributed", 0)
    elif spend_type == "billed":
        base_spend = spend_info.get("billed", 0)
    elif spend_type == "unattributed":
        base_spend = spend_info.get("unattributed", 0)
    elif spend_type == "list":
        base_spend = spend_info.get("list", 0)
    else:
        base_spend = spend_info.get("attributed", 0)
    
    credits = spend_info.get("credit", 0)
    refunds = spend_info.get("refund", 0)
    
    final_spend = base_spend
    if deduct_credits:
        final_spend -= abs(credits)
    if deduct_refunds:
        final_spend -= abs(refunds)

    return final_spend, credits, refunds


def get_time_key(item: Dict[str, Any]) -> Optional[str]:
    """Extract time key from spend data item.
    
    Returns:
        Time key as string (date or month) or None if no time data found.
    """
    if "date" in item:
        return item["date"]
    elif "month" in item:
        return str(item["month"])
    return None


def calculate_report_totals(deduct_credits: bool, deduct_refunds: bool) -> Dict[str, float]:
    """Initialize report totals structure.
    
    Returns:
        Dictionary with 'spend' key and optionally 'credits'/'refunds' keys, all set to 0.
    """
    report_totals = {"spend": 0}
    if not deduct_credits:
        report_totals["credits"] = 0
    if not deduct_refunds:
        report_totals["refunds"] = 0
    return report_totals


def handle_empty_spend_data(deduct_credits: bool, deduct_refunds: bool, dimension: str, include_timeslice_breakdown: bool) -> Dict[str, Any]:
    """Handle case where spend data is null or empty.
    
    Returns:
        Dictionary with 'report_totals' and optionally 'dimensions' keys containing zero values.
    """
    empty_totals = {"spend": 0}
    if not deduct_credits:
        empty_totals["credits"] = 0
    if not deduct_refunds:
        empty_totals["refunds"] = 0
    
    if dimension == "none" and not include_timeslice_breakdown:
        return {"report_totals": empty_totals}
    elif dimension == "none" and include_timeslice_breakdown:
        return {
            "report_totals": empty_totals,
            "dimensions": {
                "spend": {
                    "total_spend": 0,
                    "total_credits": 0 if not deduct_credits else None,
                    "total_refunds": 0 if not deduct_refunds else None,
                    "time_intervals": {}
                }
            }
        }
    else:
        return {"report_totals": empty_totals, "dimensions": {}}


def process_none_dimension(spend_data: list, spend_type: str, deduct_credits: bool, deduct_refunds: bool, include_timeslice_breakdown: bool) -> Dict[str, Any]:
    """Process spend data for 'none' dimension with time-based aggregation.
    
    Returns:
        Dictionary with 'report_totals' containing overall spend totals. When include_timeslice_breakdown
        is True, also includes 'dimensions' key with a single 'spend' entry containing time interval breakdowns.
    """
    report_totals = calculate_report_totals(deduct_credits, deduct_refunds)
    time_aggregated = {}
    
    if spend_data is None:
        spend_data = []
    
    for item in spend_data:
        spend_info = item.get("spend_data", {})
        time_key = get_time_key(item)
        
        final_spend, credits, refunds = calculate_final_spend(spend_info, spend_type, deduct_credits, deduct_refunds)
        
        # Add to report totals
        report_totals["spend"] += final_spend
        if not deduct_credits:
            report_totals["credits"] += credits
        if not deduct_refunds:
            report_totals["refunds"] += refunds
        
        # Aggregate by time period if timeslice breakdown requested
        if include_timeslice_breakdown and time_key:
            if time_key not in time_aggregated:
                time_aggregated[time_key] = {"spend": 0}
                if not deduct_credits:
                    time_aggregated[time_key]["credits"] = 0
                if not deduct_refunds:
                    time_aggregated[time_key]["refunds"] = 0
            
            time_aggregated[time_key]["spend"] += final_spend
            if not deduct_credits:
                time_aggregated[time_key]["credits"] += credits
            if not deduct_refunds:
                time_aggregated[time_key]["refunds"] += refunds
    
    # Build response for "none" dimension
    if include_timeslice_breakdown:
        # Sort time intervals chronologically
        sorted_intervals = dict(sorted(time_aggregated.items()))
        dimensions = {
            "spend": {
                "total_spend": report_totals["spend"],
                "time_intervals": sorted_intervals
            }
        }
        if not deduct_credits:
            dimensions["spend"]["total_credits"] = report_totals["credits"]
        if not deduct_refunds:
            dimensions["spend"]["total_refunds"] = report_totals["refunds"]
        
        return {
            "report_totals": report_totals,
            "dimensions": dimensions
        }
    else:
        # No timeslice breakdown - return only report totals
        return {"report_totals": report_totals}


def process_regular_dimensions(spend_data: list, spend_type: str, deduct_credits: bool, deduct_refunds: bool, include_timeslice_breakdown: bool, dimension: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Process spend data for regular dimensions (not 'none').
    
    Returns:
        Tuple of (report_totals, grouped_data) where report_totals contains overall totals
        and grouped_data contains spend data grouped by dimension values.
    """
    report_totals = calculate_report_totals(deduct_credits, deduct_refunds)
    grouped_data = {}
    
    if spend_data is None:
        spend_data = []
    
    for item in spend_data:
        group_name = item.get("group_name", "Unknown")
        group_id = item.get("group_id", 0)
        spend_info = item.get("spend_data", {})
        time_key = get_time_key(item)
        
        final_spend, credits, refunds = calculate_final_spend(spend_info, spend_type, deduct_credits, deduct_refunds)
        
        # Initialize group if not exists
        if group_name not in grouped_data:
            grouped_data[group_name] = {
                "total_spend": 0,
                "time_intervals": {}
            }
            # Include group_id if it's not 0 and not dimensioning on tags
            if group_id != 0 and dimension != "cloudProviderTag":
                grouped_data[group_name]["id"] = group_id
            if not deduct_credits:
                grouped_data[group_name]["total_credits"] = 0
            if not deduct_refunds:
                grouped_data[group_name]["total_refunds"] = 0
        
        # Add to group totals
        grouped_data[group_name]["total_spend"] += final_spend
        if not deduct_credits:
            grouped_data[group_name]["total_credits"] += credits
        if not deduct_refunds:
            grouped_data[group_name]["total_refunds"] += refunds
        
        # Add to report totals
        report_totals["spend"] += final_spend
        if not deduct_credits:
            report_totals["credits"] += credits
        if not deduct_refunds:
            report_totals["refunds"] += refunds
        
        # Add time interval data if requested
        if include_timeslice_breakdown and time_key:
            time_entry = {"spend": final_spend}
            if not deduct_credits:
                time_entry["credits"] = credits
            if not deduct_refunds:
                time_entry["refunds"] = refunds
            grouped_data[group_name]["time_intervals"][time_key] = time_entry
    
    # Clean up time_intervals if not requested, or sort them if requested
    if not include_timeslice_breakdown:
        for group_data in grouped_data.values():
            del group_data["time_intervals"]
    else:
        # Sort time intervals by chronological order
        for group_data in grouped_data.values():
            if "time_intervals" in group_data and group_data["time_intervals"] is not None:
                sorted_intervals = dict(sorted(group_data["time_intervals"].items()))
                group_data["time_intervals"] = sorted_intervals
    
    return report_totals, grouped_data


def limit_dimensions_to_max_20(grouped_data: Dict[str, Any], deduct_credits: bool, deduct_refunds: bool, include_timeslice_breakdown: bool, dimension: str) -> Dict[str, Any]:
    """Limit dimensions to a maximum of 20 total dimensions.
    
    Concatenates dimensions by taking the top 19 by spend and aggregating the rest 
    into an 'other' category as the 20th dimension. Always returns a maximum of 20 
    dimensions regardless of input size.
    
    Returns:
        Dictionary with up to 20 dimensions. If input has >20 dimensions, returns 
        top 19 by spend plus aggregated 'other' category. If ≤20 dimensions, 
        returns original data unchanged.
    """
    if len(grouped_data) <= 20:
        return grouped_data
    
    # Sort dimensions by total spend (descending)
    sorted_dimensions = sorted(grouped_data.items(), key=lambda x: x[1]["total_spend"], reverse=True)
    
    # Take top 19 dimensions (leaving room for 'other' as the 20th)
    top_19_dimensions = dict(sorted_dimensions[:19])
    
    # Calculate "other" totals from remaining dimensions
    other_dimensions = sorted_dimensions[19:]
    other_totals = {
        "total_spend": sum(dim[1]["total_spend"] for dim in other_dimensions)
    }
    
    if not deduct_credits:
        other_totals["total_credits"] = sum(dim[1].get("total_credits", 0) for dim in other_dimensions)
    if not deduct_refunds:
        other_totals["total_refunds"] = sum(dim[1].get("total_refunds", 0) for dim in other_dimensions)
    
    # Handle time intervals for "other" if needed
    if include_timeslice_breakdown:
        other_time_intervals = {}
        for _, dim_data in other_dimensions:
            if "time_intervals" in dim_data and dim_data["time_intervals"] is not None:
                for time_key, time_data in dim_data["time_intervals"].items():
                    if time_key not in other_time_intervals:
                        other_time_intervals[time_key] = {"spend": 0}
                        if not deduct_credits:
                            other_time_intervals[time_key]["credits"] = 0
                        if not deduct_refunds:
                            other_time_intervals[time_key]["refunds"] = 0
                    
                    other_time_intervals[time_key]["spend"] += time_data["spend"]
                    if not deduct_credits:
                        other_time_intervals[time_key]["credits"] += time_data.get("credits", 0)
                    if not deduct_refunds:
                        other_time_intervals[time_key]["refunds"] += time_data.get("refunds", 0)
        
        # Sort time intervals for "other"
        other_totals["time_intervals"] = dict(sorted(other_time_intervals.items()))
    
    # Determine the "other" label based on dimension type
    dimension_names = {
        "ou": "other ous",
        "project": "other projects", 
        "account": "other accounts",
        "cloudProvider": "other cloud providers",
        "billingSource": "other billing sources",
        "cloudProviderTag": "other cloud provider tags",
        "fundingSource": "other funding sources",
        "label": "other labels",
        "region": "other regions",
        "service": "other services",
        "resource": "other resources"
    }
    other_label = dimension_names.get(dimension, "other items")
    
    # Add "other" to the top 19 dimensions (making 20 total)
    top_19_dimensions[other_label] = other_totals
    return top_19_dimensions


def parse_spend_report(raw_data: Dict[str, Any], spend_type: str, deduct_credits: bool, 
                      deduct_refunds: bool, include_timeslice_breakdown: bool = False, 
                      dimension: str = "none") -> Dict[str, Any]:
    """
    Parse the spend report response into a more LLM-friendly format.
    
    Returns:
        Dictionary with 'report_totals' containing overall spend totals. For dimension="none"
        with timeslice breakdown, includes 'dimensions' with time intervals. For other dimensions,
        includes 'dimensions' with spend data grouped by dimension values (projects, accounts, etc.).
    """
    if "data" not in raw_data or "spend" not in raw_data["data"]:
        return {"report_totals": {}, "dimensions": {}}
    
    spend_data = raw_data["data"]["spend"]
    
    # Handle case where spend data is null (no spend found)
    if spend_data is None:
        return handle_empty_spend_data(deduct_credits, deduct_refunds, dimension, include_timeslice_breakdown)
    
    # Handle "none" dimension case - aggregate all groups into single view
    if dimension == "none":
        return process_none_dimension(spend_data, spend_type, deduct_credits, deduct_refunds, include_timeslice_breakdown)
    
    # Handle regular dimensions (not "none")
    report_totals, grouped_data = process_regular_dimensions(spend_data, spend_type, deduct_credits, deduct_refunds, include_timeslice_breakdown, dimension)
    
    # Limit dimensions to top 20 total if more than 20 dimensions
    grouped_data = limit_dimensions_to_max_20(grouped_data, deduct_credits, deduct_refunds, include_timeslice_breakdown, dimension)
    
    return {
        "report_totals": report_totals,
        "dimensions": grouped_data
    }