import argparse
import asyncio
import sys
import os

# Add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import (
    query_tickets, 
    query_transfer,
    search_stations
)
from utils.date_utils import get_current_date_str

def format_tickets(result):
    if not result.get("success"):
        return f"Error: {result.get('error')}\n{result.get('detail', '')}"
    
    output = []
    output.append(f"=== {result['from_station']} -> {result['to_station']} ({result['train_date']}) ===")
    for train in result.get("trains", []):
        seats = []
        for type_, num in train.get("seats", {}).items():
            seats.append(f"{type_}: {num}")
        
        output.append(f"[{train['train_no']}] {train['start_time']} -> {train['arrive_time']} ({train['duration']})")
        output.append(f"  Seats: {', '.join(seats)}")
        output.append("-" * 30)
    
    if not result.get("trains"):
        output.append("No tickets found.")
        
    return "\n".join(output)

def format_transfer_route(result):
    if not result.get("success"):
        return f"Error: {result.get('error')}\n{result.get('detail', '')}"
    
    output = []
    output.append(f"=== Transfer: {result['from_station']} -> {result['to_station']} ({result['train_date']}) ===")
    
    for route in result.get("transfers", []):
        output.append(f"Route: {route['from_station']} -> {route['to_station']} (Total: {route['total_duration']})")
        for segment in route.get("segments", []):
             output.append(f"  {segment['train_code']} {segment['from_station']}->{segment['to_station']} {segment['start_time']}->{segment['arrive_time']}")
        output.append("-" * 30)
        
    return "\n".join(output)

async def main():
    parser = argparse.ArgumentParser(description="12306 Skill CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # query-tickets
    p_tickets = subparsers.add_parser("query-tickets", help="Query train tickets")
    p_tickets.add_argument("--from", dest="from_station", required=True, help="Departure station")
    p_tickets.add_argument("--to", dest="to_station", required=True, help="Arrival station")
    p_tickets.add_argument("--date", dest="train_date", required=True, help="Date (YYYY-MM-DD)")

    # query-ticket-price (Reusing query-tickets for now as simplified version)
    p_price = subparsers.add_parser("query-ticket-price", help="Query ticket prices")
    p_price.add_argument("--from", dest="from_station", required=True, help="Departure station")
    p_price.add_argument("--to", dest="to_station", required=True, help="Arrival station")
    p_price.add_argument("--date", dest="train_date", required=True, help="Date (YYYY-MM-DD)")
    p_price.add_argument("--code", dest="train_code", help="Specific train code (e.g. G1)")

    # query-transfer
    p_transfer = subparsers.add_parser("query-transfer", help="Query transfer routes")
    p_transfer.add_argument("--from", dest="from_station", required=True, help="Departure station")
    p_transfer.add_argument("--to", dest="to_station", required=True, help="Arrival station")
    p_transfer.add_argument("--date", dest="train_date", required=True, help="Date (YYYY-MM-DD)")
    p_transfer.add_argument("--middle", dest="middle_station", help="Optional middle transfer station")

    # search-stations
    p_search = subparsers.add_parser("search-stations", help="Search for station telecodes")
    p_search.add_argument("keyword", help="Station name keyword")

    # get-current-time
    subparsers.add_parser("get-current-time", help="Get current date")

    args = parser.parse_args()

    if args.command == "query-tickets":
        result = await query_tickets({
            "from_station": args.from_station, 
            "to_station": args.to_station, 
            "train_date": args.train_date
        })
        print(format_tickets(result))

    elif args.command == "query-ticket-price":
        from core import query_ticket_price
        query_args = {
            "from_station": args.from_station,
            "to_station": args.to_station,
            "train_date": args.train_date
        }
        if args.train_code:
            query_args["train_code"] = args.train_code
        result = await query_ticket_price(query_args)
        def format_price_result(result):
            if not result.get("success"):
                return f"Error: {result.get('error')}\n{result.get('detail', '')}"
            output = []
            output.append(f"=== {result['from_station']} -> {result['to_station']} ({result['train_date']}) ===")
            for train in result.get("data", []):
                output.append(f"[{train['train_no']}] 票价:")
                for seat, price in train.get("prices", {}).items():
                    output.append(f"  {seat}: {price} 元")
                output.append("-" * 30)
            if not result.get("data"):
                output.append("No price data found.")
            return "\n".join(output)
        print(format_price_result(result))

    elif args.command == "query-transfer":
        query_args = {
            "from_station": args.from_station,
            "to_station": args.to_station,
            "train_date": args.train_date
        }
        if args.middle_station:
            query_args["middle_station"] = args.middle_station
            
        result = await query_transfer(query_args)
        print(format_transfer_route(result))

    elif args.command == "search-stations":
        result = await search_stations({"query": args.keyword})
        if result.get("success"):
            for s in result.get("stations", []):
                print(f"Station: {s['name']}, Code: {s['code']}, Pinyin: {s['pinyin']}")
        else:
            print(f"Station '{args.keyword}' not found.")

    elif args.command == "get-current-time":
        print(get_current_date_str())

    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        # Windows compatibility
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
