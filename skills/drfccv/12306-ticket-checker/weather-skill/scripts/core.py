import httpx
import asyncio
from typing import Optional, Dict, Any

API_BASE_URL = "https://uapis.cn/api/v1/misc/weather"

async def query_weather(
    city: Optional[str] = None,
    adcode: Optional[str] = None,
    extended: bool = False,
    forecast: bool = False,
    indices: bool = False
) -> Dict[str, Any]:
    """
    Query weather data from UAPI.
    
    Args:
        city: City name (e.g., "北京")
        adcode: 6-digit city code (e.g., "110000")
        extended: Return extended fields (feels_like, visibility, etc.)
        forecast: Return 3-day forecast
        indices: Return life indices
        
    Returns:
        Dictionary containing weather data or error message
    """
    if not city and not adcode:
        return {"error": "Either 'city' or 'adcode' parameter is required."}

    params = {}
    if adcode:
        params["adcode"] = adcode
    elif city:
        params["city"] = city
        
    if extended:
        params["extended"] = "true"
    if forecast:
        params["forecast"] = "true"
    if indices:
        params["indices"] = "true"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(API_BASE_URL, params=params, timeout=10.0)
            
            # Try to parse JSON response regardless of status code
            try:
                data = response.json()
            except Exception:
                return {
                    "error": f"Failed to parse response. Status: {response.status_code}",
                    "content": response.text
                }

            if response.status_code == 200:
                return data
            else:
                # Return API error message if available
                return {
                    "error": data.get("message", "Unknown API error"),
                    "code": data.get("code", str(response.status_code)),
                    "details": data
                }
                
    except httpx.RequestError as e:
        return {"error": f"Network request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def format_weather_output(data: Dict[str, Any]) -> str:
    """Format weather data into a readable string."""
    if "error" in data:
        return f"Error: {data['error']} (Code: {data.get('code', 'N/A')})"

    output = []
    
    # Basic Info
    city_name = data.get('city', 'Unknown City')
    province = data.get('province', '')
    weather = data.get('weather', 'N/A')
    temp = data.get('temperature', 'N/A')
    wind_dir = data.get('wind_direction', '')
    wind_power = data.get('wind_power', '')
    report_time = data.get('report_time', '')
    
    output.append(f"=== {province} {city_name} 天气实况 ===")
    output.append(f"时间: {report_time}")
    output.append(f"天气: {weather}")
    output.append(f"温度: {temp}°C")
    if wind_dir or wind_power:
        output.append(f"风向风力: {wind_dir} {wind_power}级")
    output.append(f"湿度: {data.get('humidity', 'N/A')}%")
    
    # Extended Info
    if 'feels_like' in data:
        output.append("\n--- 详细数据 ---")
        output.append(f"体感温度: {data.get('feels_like')}°C")
        output.append(f"能见度: {data.get('visibility')}km")
        output.append(f"气压: {data.get('pressure')}hPa")
        output.append(f"紫外线指数: {data.get('uv')}")
        output.append(f"空气质量(AQI): {data.get('aqi')}")
        output.append(f"降水量: {data.get('precipitation')}mm")
    
    # Life Indices
    if 'life_indices' in data:
        output.append("\n--- 生活指数 ---")
        indices = data['life_indices']
        mapping = {
            'clothing': '穿衣',
            'uv': '紫外线',
            'car_wash': '洗车',
            'drying': '晾晒',
            'cold_risk': '感冒',
            'comfort': '舒适度'
        }
        for key, name in mapping.items():
            if key in indices:
                item = indices[key]
                output.append(f"{name}: {item.get('level')} ({item.get('advice')})")

    # Forecast
    if 'forecast' in data:
        output.append("\n--- 未来天气预报 ---")
        for day in data['forecast']:
            date = day.get('date', '')
            week = day.get('week', '')
            w_day = day.get('weather_day', '')
            w_night = day.get('weather_night', '')
            t_max = day.get('temp_max', '')
            t_min = day.get('temp_min', '')
            output.append(f"{date} ({week}): {w_day}转{w_night}, {t_min}-{t_max}°C")

    return "\n".join(output)
