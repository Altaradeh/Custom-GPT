"""
Chart generation utilities for GPT artifact rendering
"""
from typing import Dict, List, Any
import json

def generate_time_series_chart(data: List[Dict[str, Any]], title: str = "Time Series Analysis") -> Dict[str, Any]:
    """
    Generate time series chart data for GPT artifact rendering
    
    Args:
        data: List of dicts with 'date' and 'value' keys
        title: Chart title
    
    Returns:
        Chart specification for GPT artifacts
    """
    return {
        "type": "line_chart",
        "title": title,
        "data": data,
        "x_axis": "Date",
        "y_axis": "Value",
        "chart_config": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": True},
                "tooltip": {"enabled": True}
            }
        }
    }

def generate_scatter_plot(x_data: List[float], y_data: List[float], labels: List[str] = None, 
                         title: str = "XMetric vs YMetric Analysis") -> Dict[str, Any]:
    """
    Generate scatter plot data for GPT artifact rendering
    
    Args:
        x_data: X-axis values (XMetric scores)
        y_data: Y-axis values (YMetric scores)  
        labels: Point labels (ticker symbols, names, etc.)
        title: Chart title
    
    Returns:
        Chart specification for GPT artifacts
    """
    if labels is None:
        labels = [f"Point {i+1}" for i in range(len(x_data))]
    
    data = [
        {"x": x, "y": y, "label": label} 
        for x, y, label in zip(x_data, y_data, labels)
    ]
    
    return {
        "type": "scatter_plot", 
        "title": title,
        "data": data,
        "x_axis": "XMetric Score",
        "y_axis": "YMetric Score",
        "chart_config": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": True},
                "tooltip": {"enabled": True}
            }
        }
    }

def generate_combined_analysis_chart(xmetric_result: Dict, ymetric_result: Dict) -> Dict[str, Any]:
    """
    Generate a combined analysis using both XMetric and YMetric results
    
    Args:
        xmetric_result: Output from handle_xmetric
        ymetric_result: Output from handle_ymetric
    
    Returns:
        Combined chart specification
    """
    # Extract summary values for scatter plot
    x_value = xmetric_result.get("summary", {}).get("mean", 0)
    y_value = ymetric_result.get("summary", {}).get("mean", 0)
    
    return generate_scatter_plot(
        x_data=[x_value],
        y_data=[y_value], 
        labels=["Analysis Point"],
        title="Combined XMetric vs YMetric Analysis"
    )