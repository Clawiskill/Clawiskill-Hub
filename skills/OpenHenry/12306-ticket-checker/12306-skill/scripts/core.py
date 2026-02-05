
import asyncio
import json
import logging
import httpx
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import pytz
import re

from services.station_service import StationService
from utils.config import get_settings
from utils.date_utils import validate_date

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize StationService
station_service = StationService()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

async def ensure_telecode(val):
    if val.isalpha() and val.isupper() and len(val) == 3:
        return val
    code = await station_service.get_station_code(val)
    return code

def parse_ticket_string(ticket_str, query):
    parts = ticket_str.split('|')
    if len(parts) < 35:
        return None
    return {
        "train_no": parts[3],
        "start_time": parts[8],
        "arrive_time": parts[9],
        "duration": parts[10],
        "business_seat_num": parts[32] or "",
        "first_class_num": parts[31] or "",
        "second_class_num": parts[30] or "",
        "advanced_soft_sleeper_num": parts[21] or "",
        "soft_sleeper_num": parts[23] or "",
        "dongwo_num": parts[33] or "",
        "hard_sleeper_num": parts[28] or "",
        "soft_seat_num": parts[24] or "",
        "hard_seat_num": parts[29] or "",
        "no_seat_num": parts[26] or "",
        "from_station": query["from_station"],
        "to_station": query["to_station"],
        "train_date": query["train_date"]
    }

async def search_stations(args: dict) -> dict:
    query = args.get("query", "").strip()
    limit = args.get("limit", 10)
    if not query:
        return {"success": False, "error": "请输入搜索关键词"}
    if not isinstance(limit, int) or limit < 1 or limit > 50:
        limit = 10
    result = await station_service.search_stations(query, limit)
    if result.stations:
        stations_data = []
        for station in result.stations:
            station_dict = {
                "name": station.name,
                "code": station.code,
                "pinyin": station.pinyin,
                "py_short": station.py_short if station.py_short else "",
            }
            if hasattr(station, 'num') and station.num:
                station_dict["num"] = station.num
            stations_data.append(station_dict)
        
        return {
            "success": True,
            "query": query,
            "count": len(stations_data),
            "stations": stations_data
        }
    else:
        return {
            "success": False,
            "query": query,
            "count": 0,
            "stations": [],
            "message": "未找到匹配的车站",
            "suggestions": [
                "尝试完整城市名称 (如: 北京)",
                "尝试拼音 (如: beijing)",
                "尝试简拼 (如: bj)",
                "检查拼写是否正确"
            ]
        }

async def query_tickets(args: dict) -> dict:
    try:
        from_station = args.get("from_station", "").strip()
        to_station = args.get("to_station", "").strip()
        train_date = args.get("train_date", "").strip()
        logger.info(f"查询参数: {from_station} -> {to_station} ({train_date})")
        errors = []
        if not from_station:
            errors.append("出发站不能为空")
        if not to_station:
            errors.append("到达站不能为空")
        if not train_date:
            errors.append("出发日期不能为空")
        elif not validate_date(train_date):
            errors.append("日期格式错误，请使用 YYYY-MM-DD 格式")
        if errors:
            return {"success": False, "errors": errors}
            
        from_code = await ensure_telecode(from_station)
        to_code = await ensure_telecode(to_station)
        
        if not from_code or not to_code:
            suggestions = []
            if not from_code:
                result = await station_service.search_stations(from_station, 3)
                if result.stations:
                    suggestions.append({"station_type": "from", "input": from_station, "matches": [{"name": s.name, "code": s.code, "pinyin": s.pinyin, "py_short": s.py_short} for s in result.stations]})
            if not to_code:
                result = await station_service.search_stations(to_station, 3)
                if result.stations:
                    suggestions.append({"station_type": "to", "input": to_station, "matches": [{"name": s.name, "code": s.code, "pinyin": s.pinyin, "py_short": s.py_short} for s in result.stations]})
            return {"success": False, "error": "车站名称无效", "suggestions": suggestions, "hint": "可尝试拼音、简拼、三字码或用 search_stations 工具辅助查询"}
            
        url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
        url_u = "https://kyfw.12306.cn/otn/leftTicket/queryG"
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
            "Host": "kyfw.12306.cn",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
        max_retries = 3
        last_exception = None
        tickets_data = []

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
                    await client.get(url_init, headers=headers)
                    params = {
                        "leftTicketDTO.train_date": train_date,
                        "leftTicketDTO.from_station": from_code,
                        "leftTicketDTO.to_station": to_code,
                        "purpose_codes": "ADULT"
                    }
                    resp = await client.get(url_u, headers=headers, params=params)
                    if resp.status_code != 200:
                        return {"success": False, "error": "12306接口返回异常", "status_code": resp.status_code, "detail": resp.text[:200]}
                    try:
                        data = resp.json().get("data", {})
                        tickets_data = data.get("result", [])
                        break  # Success
                    except Exception as e:
                        return {"success": False, "error": "12306响应解析失败", "detail": f"{type(e).__name__}: {str(e)}"}
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        else:
            return {"success": False, "error": f"网络请求失败 (已重试{max_retries}次): {str(last_exception)}"}
            
        tickets = []
        for ticket_str in tickets_data:
            ticket = parse_ticket_string(ticket_str, {
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date
            })
            if ticket:
                tickets.append(ticket)
                
        if tickets:
            trains_list = []
            for i, ticket in enumerate(tickets, 1):
                ticket_str = tickets_data[i-1] if i-1 < len(tickets_data) else None
                from_station_name = to_station_name = from_code_actual = to_code_actual = None
                if ticket_str:
                    parts = ticket_str.split('|')
                    from_code_actual = parts[6] if len(parts) > 6 else None
                    to_code_actual = parts[7] if len(parts) > 7 else None
                    # Try to resolve station names from codes
                    from_station_obj = await station_service.get_station_by_code(from_code_actual) if from_code_actual else None
                    to_station_obj = await station_service.get_station_by_code(to_code_actual) if to_code_actual else None
                    from_station_name = from_station_obj.name if from_station_obj else (from_code_actual or "未知")
                    to_station_name = to_station_obj.name if to_station_obj else (to_code_actual or "未知")
                
                seats = {}
                if ticket['business_seat_num']: seats["business"] = ticket['business_seat_num']
                if ticket['first_class_num']: seats["first_class"] = ticket['first_class_num']
                if ticket['second_class_num']: seats["second_class"] = ticket['second_class_num']
                if ticket['advanced_soft_sleeper_num']: seats["advanced_soft_sleeper"] = ticket['advanced_soft_sleeper_num']
                if ticket['soft_sleeper_num']: seats["soft_sleeper"] = ticket['soft_sleeper_num']
                if ticket['hard_sleeper_num']: seats["hard_sleeper"] = ticket['hard_sleeper_num']
                if ticket['soft_seat_num']: seats["soft_seat"] = ticket['soft_seat_num']
                if ticket['hard_seat_num']: seats["hard_seat"] = ticket['hard_seat_num']
                if ticket['no_seat_num']: seats["no_seat"] = ticket['no_seat_num']
                if ticket['dongwo_num']: seats["dongwo"] = ticket['dongwo_num']
                
                train_data = {
                    "train_no": ticket['train_no'],
                    "from_station": from_station_name,
                    "from_station_code": from_code_actual,
                    "to_station": to_station_name,
                    "to_station_code": to_code_actual,
                    "start_time": ticket['start_time'],
                    "arrive_time": ticket['arrive_time'],
                    "duration": ticket['duration'],
                    "seats": seats
                }
                trains_list.append(train_data)
            
            return {
                "success": True,
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date,
                "count": len(trains_list),
                "trains": trains_list
            }
        else:
            return {
                "success": False,
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date,
                "count": 0,
                "trains": [],
                "message": "未找到该线路的余票"
            }
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"查询车票失败: {error_detail}\n{traceback.format_exc()}")
        return {"success": False, "error": "查询失败", "detail": error_detail}

async def get_train_no_by_train_code(args: dict) -> dict:
    train_code = args.get("train_code", "").strip().upper()
    from_station = args.get("from_station", "").strip().upper()
    to_station = args.get("to_station", "").strip().upper()
    train_date = args.get("train_date", "").strip()
    try:
        dt = datetime.strptime(train_date, "%Y-%m-%d")
        if dt.date() < date.today():
            return {"success": False, "error": "出发日期不能早于今天"}
    except Exception:
        return {"success": False, "error": "出发日期格式错误，应为YYYY-MM-DD"}
        
    def is_telecode(val):
        return val.isalpha() and val.isupper() and len(val) == 3
        
    if not is_telecode(from_station):
        code = await station_service.get_station_code(from_station)
        if not code:
            return {"success": False, "error": f"出发站无效或无法识别：{from_station}"}
        from_station = code
    if not is_telecode(to_station):
        code = await station_service.get_station_code(to_station)
        if not code:
            return {"success": False, "error": f"到达站无效或无法识别：{to_station}"}
        to_station = code
        
    url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
    url_u = "https://kyfw.12306.cn/otn/leftTicket/queryG"
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        "Host": "kyfw.12306.cn",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
        await client.get(url_init, headers=headers)
        params = {
            "leftTicketDTO.train_date": train_date,
            "leftTicketDTO.from_station": from_station,
            "leftTicketDTO.to_station": to_station,
            "purpose_codes": "ADULT"
        }
        resp = await client.get(url_u, headers=headers, params=params)
        try:
            data = resp.json().get("data", {})
            tickets_data = data.get("result", [])
        except Exception:
            return {"success": False, "error": "12306反爬拦截或数据异常，请稍后重试"}
            
    if not tickets_data:
        return {"success": False, "error": f"未找到该线路的余票数据（{from_station}->{to_station} {train_date}）"}
        
    found = None
    for ticket_str in tickets_data:
        parts = ticket_str.split('|')
        try:
            idx = parts.index('预订')
            train_no = parts[idx+1].strip()
            train_code_str = parts[idx+2].strip().upper()
            if train_code_str == train_code:
                found = train_no
                break
        except Exception:
            continue
            
    if not found:
        debug_codes = []
        for p in tickets_data:
            try:
                parts = p.split('|')
                idx = parts.index('预订')
                debug_codes.append(parts[idx+2])
            except Exception:
                continue
        return {"success": False, "train_code": train_code, "from_station": from_station, "to_station": to_station, "train_date": train_date, "error": "未找到该车次号的列车编号", "available_trains": debug_codes}
        
    return {"success": True, "train_code": train_code, "train_no": found, "from_station": from_station, "to_station": to_station, "train_date": train_date}

async def get_train_route_stations(args: dict) -> dict:
    try:
        train_no = args.get("train_no", "").strip()
        from_station = args.get("from_station", "").strip().upper()
        to_station = args.get("to_station", "").strip().upper()
        train_date = args.get("train_date", "").strip()
        
        if not train_no:
            return {"success": False, "error": "车次编号(train_no)不能为空"}
        if not from_station:
            return {"success": False, "error": "出发站不能为空"}
        if not to_station:
            return {"success": False, "error": "到达站不能为空"}
        if not train_date:
            return {"success": False, "error": "出发日期不能为空"}
        
        try:
            dt = datetime.strptime(train_date, "%Y-%m-%d")
            if dt.date() < date.today():
                return {"success": False, "error": "出发日期不能早于今天"}
        except Exception:
            return {"success": False, "error": "出发日期格式错误，应为YYYY-MM-DD"}
        
        def is_telecode(val):
            return val.isalpha() and val.isupper() and len(val) == 3
        
        if not is_telecode(from_station):
            code = await station_service.get_station_code(from_station)
            if not code:
                return {"success": False, "error": f"出发站无效或无法识别：{from_station}"}
            from_station = code
        
        if not is_telecode(to_station):
            code = await station_service.get_station_code(to_station)
            if not code:
                return {"success": False, "error": f"到达站无效或无法识别：{to_station}"}
            to_station = code
        
        is_train_code = bool(re.match(r'^[A-Z]+\d+$', train_no))
        
        if is_train_code:
            convert_args = {
                "train_code": train_no,
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date
            }
            convert_result = await get_train_no_by_train_code(convert_args)
            
            if not convert_result.get("success"):
                return convert_result
            
            actual_train_no = convert_result.get("train_no")
            if not actual_train_no:
                return {"success": False, "error": f"无法解析车次 {train_no} 的列车编号"}
        else:
            actual_train_no = train_no
        
        url = "https://kyfw.12306.cn/otn/czxx/queryByTrainNo"
        params = {
            "train_no": actual_train_no,
            "from_station_telecode": from_station,
            "to_station_telecode": to_station,
            "depart_date": train_date
        }
        
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "kyfw.12306.cn",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://kyfw.12306.cn"
        }
        
        max_retries = 3
        last_exception = None
        json_data = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
                    await client.get("https://kyfw.12306.cn/otn/leftTicket/init", headers=headers)
                    resp = await client.get(url, headers=headers, params=params)
                    if resp.status_code != 200:
                        return {"success": False, "error": f"12306接口返回异常: {resp.status_code}"}
                    if "error.html" in str(resp.url) or "ntce" in str(resp.url):
                        return {"success": False, "error": "12306反爬虫拦截，请稍后重试或更换网络环境"}
                    try:
                        json_data = resp.json()
                        break
                    except Exception as e:
                        return {"success": False, "error": f"12306响应解析失败: {str(e)}"}
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        else:
            return {"success": False, "error": f"网络请求失败 (已重试{max_retries}次): {str(last_exception)}"}
        
        if not json_data:
            return {"success": False, "error": "12306接口返回空数据"}
        
        data = json_data.get("data", {})
        stations = data.get("data", [])
        
        if not stations and "middleList" in data:
            stations = []
            for m in data["middleList"]:
                if "fullList" in m:
                    stations.extend(m["fullList"])
        if not stations and "fullList" in data:
            stations = data["fullList"]
        if not stations and "route" in data:
            stations = data["route"]
        
        if not stations:
            return {"success": False, "train_no": train_no, "error": "未找到经停站信息"}
        
        stations_list = []
        for station in stations:
            station_data = {
                "station_no": station.get("station_no", station.get("from_station_no", "")),
                "station_name": station.get("station_name", station.get("from_station_name", "")),
                "arrive_time": station.get("arrive_time", "----"),
                "start_time": station.get("start_time", "----"),
                "stopover_time": station.get("stopover_time", "----")
            }
            stations_list.append(station_data)
        
        return {
            "success": True,
            "train_no": train_no,
            "train_date": train_date,
            "count": len(stations_list),
            "stations": stations_list
        }
    except Exception as e:
        return {"success": False, "error": "查询经停站失败", "detail": str(e)}

async def query_transfer(args: dict) -> dict:
    try:
        from_station = args.get("from_station", "").strip()
        to_station = args.get("to_station", "").strip()
        train_date = args.get("train_date", "").strip()
        middle_station = args.get("middle_station", "").strip() if "middle_station" in args else ""
        isShowWZ = args.get("isShowWZ", "N").strip().upper() or "N"
        purpose_codes = args.get("purpose_codes", "00").strip().upper() or "00"
        
        if not from_station or not to_station or not train_date:
            return {"success": False, "error": "请输入出发站、到达站和出发日期"}
        
        try:
            dt = datetime.strptime(train_date, "%Y-%m-%d")
            if dt.date() < date.today():
                return {"success": False, "error": "出发日期不能早于今天"}
        except Exception:
            return {"success": False, "error": "出发日期格式错误，应为YYYY-MM-DD"}
        
        async def ensure_telecode(val):
            if val.isalpha() and val.isupper() and len(val) == 3:
                return val
            code = await station_service.get_station_code(val)
            return code
        
        from_code = await ensure_telecode(from_station)
        to_code = await ensure_telecode(to_station)
        if not from_code:
            return {"success": False, "error": f"出发站无效或无法识别：{from_station}"}
        if not to_code:
            return {"success": False, "error": f"到达站无效或无法识别：{to_station}"}

        middle_station_code = ""
        if middle_station:
            middle_station_code = await ensure_telecode(middle_station)
            if not middle_station_code:
                middle_station_code = middle_station 
        
        url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
        url = "https://kyfw.12306.cn/lcquery/queryG"
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "kyfw.12306.cn",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://kyfw.12306.cn"
        }
        
        all_transfer_list = []
        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
                    await client.get(url_init, headers=headers)
                    page_size = 10
                    result_index = 0
                    page_num = 1
                    
                    while True:
                        params = {
                            "train_date": train_date,
                            "from_station_telecode": from_code,
                            "to_station_telecode": to_code,
                            "middle_station": middle_station_code,
                            "result_index": str(result_index),
                            "can_query": "Y",
                            "isShowWZ": isShowWZ,
                            "purpose_codes": purpose_codes,
                            "channel": "E"
                        }
                        
                        resp = await client.get(url, headers=headers, params=params)
                        
                        if resp.status_code == 302 or "error.html" in str(resp.headers.get("location", "")):
                            if page_num == 1:
                                return {"success": False, "error": "12306反爬虫拦截（302跳转），请稍后重试或更换网络环境"}
                            else:
                                break
                        
                        try:
                            data = resp.json().get("data", {})
                            transfer_list = data.get("middleList", [])
                        except Exception:
                            if page_num == 1:
                                return {"success": False, "error": "12306反爬拦截或数据异常，请稍后重试"}
                            else:
                                break
                        
                        if not transfer_list:
                            break
                        
                        all_transfer_list.extend(transfer_list)
                        
                        if len(transfer_list) < page_size:
                            break
                        
                        result_index += page_size
                        page_num += 1
                    
                    break
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                last_exception = e
                all_transfer_list = []
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        else:
            return {"success": False, "error": f"网络请求失败 (已重试{max_retries}次): {str(last_exception)}"}
        
        if not all_transfer_list:
            return {
                "success": False,
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date,
                "count": 0,
                "transfers": [],
                "message": "未查到中转方案"
            }
        
        transfers_list = []
        for item in all_transfer_list:
            try:
                full_list = item.get("fullList") or item.get("trainList") or []
                if len(full_list) < 2:
                    continue
                
                segments = []
                for seg in full_list:
                    seats = {}
                    seat_num = seg.get("swz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["商务座"] = seat_num
                    seat_num = seg.get("tz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["特等座"] = seat_num
                    seat_num = seg.get("zy_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["一等座"] = seat_num
                    seat_num = seg.get("ze_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["二等座"] = seat_num
                    seat_num = seg.get("gr_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["高级软卧"] = seat_num
                    seat_num = seg.get("rw_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["软卧"] = seat_num
                    seat_num = seg.get("rz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["一等卧"] = seat_num
                    seat_num = seg.get("yw_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["硬卧"] = seat_num
                    seat_num = seg.get("yz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["硬座"] = seat_num
                    seat_num = seg.get("wz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "": seats["无座"] = seat_num
                    
                    segment_data = {
                        "train_code": seg.get("station_train_code", ""),
                        "from_station": seg.get("from_station_name", ""),
                        "to_station": seg.get("to_station_name", ""),
                        "start_time": seg.get("start_time", ""),
                        "arrive_time": seg.get("arrive_time", ""),
                        "duration": seg.get("lishi", ""),
                        "seats": seats
                    }
                    segments.append(segment_data)
                
                transfer_data = {
                    "middle_station": item.get("middle_station_name") or (full_list[0].get("to_station_name", "") if full_list else ""),
                    "wait_time": item.get("wait_time", ""),
                    "total_duration": item.get("all_lishi", ""),
                    "segments": segments
                }
                transfers_list.append(transfer_data)
                
            except Exception as e:
                continue
        
        return {
            "success": True,
            "from_station": from_station,
            "to_station": to_station,
            "train_date": train_date,
            "count": len(transfers_list),
            "transfers": transfers_list
        }
        
    except Exception as e:
        return {"success": False, "error": "查询中转失败", "detail": str(e)}

async def query_ticket_price(args: dict) -> dict:
    try:
        from_station = args.get("from_station", "").strip()
        to_station = args.get("to_station", "").strip()
        train_date = args.get("train_date", "").strip()
        purpose_codes = args.get("purpose_codes", "ADULT").strip()
        train_code = args.get("train_code", "").strip().upper()
        
        if not from_station or not to_station or not train_date:
            return {"success": False, "error": "请输入出发站、到达站和出发日期"}
            
        if not validate_date(train_date):
             return {"success": False, "error": "日期格式错误，请使用 YYYY-MM-DD 格式"}

        async def ensure_telecode(val):
            if val.isalpha() and val.isupper() and len(val) == 3:
                return val
            code = await station_service.get_station_code(val)
            return code

        from_code = await ensure_telecode(from_station)
        to_code = await ensure_telecode(to_station)
        
        if not from_code:
             return {"success": False, "error": f"出发站无效: {from_station}"}
        if not to_code:
             return {"success": False, "error": f"到达站无效: {to_station}"}

        import httpx
        url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
        url_price = "https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice"
        
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
            "Host": "kyfw.12306.cn",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
        
        params = {
            "leftTicketDTO.train_date": train_date,
            "leftTicketDTO.from_station": from_code,
            "leftTicketDTO.to_station": to_code,
            "purpose_codes": purpose_codes
        }

        max_retries = 3
        last_exception = None
        json_data = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
                    await client.get(url_init, headers=headers)
                    resp = await client.get(url_price, headers=headers, params=params)
                    
                    if resp.status_code != 200:
                         return {"success": False, "error": f"12306接口返回异常: {resp.status_code}"}
                    
                    try:
                        json_data = resp.json()
                        break
                    except Exception as e:
                        return {"success": False, "error": "12306响应解析失败", "detail": str(e)}
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        else:
            return {"success": False, "error": f"网络请求失败 (已重试{max_retries}次): {str(last_exception)}"}

        if json_data and "data" in json_data:
            result_data = []
            price_map = {
                "wz_price": "无座",
                "yz_price": "硬座",
                "yw_price": "硬卧",
                "rw_price": "软卧",
                "gr_price": "高级软卧",
                "ze_price": "二等座",
                "zy_price": "一等座",
                "swz_price": "商务座",
                "tdz_price": "特等座",
                "dw_price": "动卧"
            }
            
            for item in json_data.get("data", []):
                query_left_new_dto = item.get("queryLeftNewDTO", {})
                current_train_code = query_left_new_dto.get("station_train_code", "")
                if train_code and current_train_code != train_code:
                    continue
                
                train_info = {
                    "train_no": query_left_new_dto.get("train_no"),
                    "train_code": current_train_code,
                    "from_station": query_left_new_dto.get("from_station_name"),
                    "to_station": query_left_new_dto.get("to_station_name"),
                    "start_time": query_left_new_dto.get("start_time"),
                    "arrive_time": query_left_new_dto.get("arrive_time"),
                    "duration": query_left_new_dto.get("lishi"),
                    "train_class_name": query_left_new_dto.get("train_class_name"),
                    "prices": {}
                }
                
                for key, name in price_map.items():
                    price_val = query_left_new_dto.get(key)
                    if price_val and price_val != "--":
                        try:
                            if price_val.isdigit():
                                price_int = int(price_val)
                                price_str = str(price_int)
                                if len(price_str) == 1:
                                    formatted_price = "0." + price_str
                                else:
                                    formatted_price = price_str[:-1] + "." + price_str[-1]
                                train_info["prices"][name] = formatted_price
                            else:
                                train_info["prices"][name] = price_val
                        except:
                            train_info["prices"][name] = price_val
                            
                result_data.append(train_info)
            
            return {
                "success": True,
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date,
                "count": len(result_data),
                "data": result_data
            }

        return json_data
        
    except Exception as e:
        return {"success": False, "error": "查询票价失败", "detail": str(e)}

async def get_current_time(args: dict) -> dict:
    try:
        timezone_str = args.get("timezone", "Asia/Shanghai")
        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
        except pytz.exceptions.UnknownTimeZoneError:
            tz = pytz.timezone("Asia/Shanghai")
            now = datetime.now(tz)
        
        return {
            "success": True,
            "timezone": tz.zone,
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timestamp": int(now.timestamp())
        }
    except Exception as e:
        return {"success": False, "error": "获取时间信息失败", "detail": str(e)}
