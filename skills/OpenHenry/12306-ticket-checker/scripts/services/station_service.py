import httpx
import logging
import asyncio
import json
import os
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class Station:
    name: str
    code: str
    pinyin: str
    py_short: str
    num: str = ""

@dataclass
class SearchResult:
    stations: List[Station]

class StationService:
    def __init__(self):
        self.stations: List[Station] = []
        self.station_map: Dict[str, str] = {}  # name -> code
        self.code_map: Dict[str, Station] = {}  # code -> Station
        self._loaded = False
        self.cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stations.json")
        
    async def load_stations(self):
        if self._loaded:
            return

        # Try to load from cache first
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        station = Station(**item)
                        self.stations.append(station)
                        self.station_map[station.name] = station.code
                        self.code_map[station.code] = station
                if self.stations:
                    self._loaded = True
                    logger.info(f"Loaded {len(self.stations)} stations from cache: {self.cache_file}")
                    return
            except Exception as e:
                logger.error(f"Error loading stations from cache: {e}")

        # If cache missing or empty, fetch from network
        url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    content = response.text
                    # content is like: var station_names ='@bjb|北京北|VAP|beijingbei|bjb|0@...'
                    start_index = content.find("'") + 1
                    end_index = content.rfind("'")
                    if start_index > 0 and end_index > start_index:
                        data = content[start_index:end_index]
                        parts = data.split('@')
                        for part in parts:
                            if not part:
                                continue
                            fields = part.split('|')
                            if len(fields) >= 5:
                                # format: py_short|name|code|pinyin|py_short|num
                                station = Station(
                                    name=fields[1],
                                    code=fields[2],
                                    pinyin=fields[3],
                                    py_short=fields[4],
                                    num=fields[5] if len(fields) > 5 else ""
                                )
                                self.stations.append(station)
                                self.station_map[station.name] = station.code
                                self.code_map[station.code] = station
                        
                        if self.stations:
                            self._loaded = True
                            logger.info(f"Loaded {len(self.stations)} stations from 12306")
                            # Save to cache
                            try:
                                with open(self.cache_file, 'w', encoding='utf-8') as f:
                                    json.dump([asdict(s) for s in self.stations], f, ensure_ascii=False)
                                logger.info(f"Saved stations to cache: {self.cache_file}")
                            except Exception as e:
                                logger.error(f"Error saving stations to cache: {e}")
                    else:
                        logger.error("Failed to parse station data format")
                else:
                    logger.error(f"Failed to fetch stations: {response.status_code}")
        except Exception as e:
            logger.error(f"Error loading stations from network: {repr(e)}")

    async def get_station_code(self, name: str) -> Optional[str]:
        if not self._loaded:
            await self.load_stations()
        return self.station_map.get(name)

    async def get_station_by_code(self, code: str) -> Optional[Station]:
        if not self._loaded:
            await self.load_stations()
        return self.code_map.get(code)

    async def search_stations(self, query: str, limit: int = 10) -> SearchResult:
        if not self._loaded:
            await self.load_stations()
        
        query = query.lower()
        matches = []
        for station in self.stations:
            if (query in station.name or 
                query in station.pinyin.lower() or 
                query in station.py_short.lower() or
                query.upper() == station.code):
                matches.append(station)
                if len(matches) >= limit:
                    break
        
        return SearchResult(stations=matches)
