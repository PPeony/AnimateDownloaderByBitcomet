import logging
import os
import random
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List
import httpx
import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('server.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


@mcp.tool()
async def get_web_page(url: str, headers: dict) -> str:
    """get the web page html from the url which contains magnet.
        Notice: When the number of characters on a webpage exceeds 2000, it will be truncated
        Args:
        url: the web page's url
        headers: custom headers, these will be added into the request header
    """
    # 调用工具，获取网页中的磁力链接链接，https://www.comicat.org/search.php?keyword=NUKITASHI，磁力后缀拼在href属性里面，在show后面的字段就是磁力后缀，你只需要返回第一个单元格的完整磁力链接。这个是调用函数所需要的请求头：headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36','Cookie': 'visitor_test=human', } 你最后的回答只需要回答磁力链接即可
    payload = {}
    # 防止请求太频繁
    time.sleep(1)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Cookie': 'visitor_test=human',
    }
    try:
        response = requests.request("GET", url, headers=headers, data=payload)
        logger.debug(f"successfully request url: {url} headers:{headers}")
        html = response.text
        logger.debug(f"response: {response}")

        soup = BeautifulSoup(html, 'html.parser')

        target_tag = 'tbody'
        target_id = 'data_list'
        target_element = soup.find(target_tag, id=target_id)
        logger.debug(f"successfully request web content is:{str(target_element)[:2000]}")
        return str(target_element)[:2000]
    except Exception as e:
        logger.error(f"Mcp tool call failed, error is {e}")
        return f"Mcp tool call failed, error is {e}"


@mcp.tool()
async def call_bitcomet(magnet: str) -> bool:
    """
    call bitcomet to start download
    :param magnet: the magnet to download    :return:  is successful
    """
    command = f"\"C:\\Program Files\\BitComet\\bitcomet\" --url {magnet} -s --tray"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stderr != "":
        logging.debug('call bitcomet error: ' + command)
        return False
    logging.debug(f'Successfully call bitcomet url:{magnet}')
    return True


@mcp.tool()
async def get_all_files(folder_path: str) -> dict[str, list[dict[str, str | bool]]]:
    """
    get all files in folder_path
    :param folder_path: the path which bitcomet will download to
    :return: a list of dict in the folder_path, each dict has 4 keys, name: the file or folder name, is_dir, is_file,
    path: the full path
    """
    dir_path = Path(folder_path)
    if not dir_path.exists():
        return {}
    if not dir_path.is_dir():
        return {}

    # iterdir() 遍历当前目录，不递归
    items = []
    for item in dir_path.iterdir():
        items.append({
            'name': item.name,
            'is_dir': item.is_dir(),
            'is_file': item.is_file(),
            'path': str(item)  # 完整路径
        })
    logger.debug(items)
    res = {'result': items}
    return res


@mcp.tool()
async def get_file_content(path: str) -> str:

    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    logger.debug(f"get_file_content:{content}")
    return content


@mcp.tool()
async def get_name_hash_res(name: str) -> int:
    """
    get the hash result from name
    :param name: this will be used to hash
    :return: the hash result
    """
    return hash(name)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
