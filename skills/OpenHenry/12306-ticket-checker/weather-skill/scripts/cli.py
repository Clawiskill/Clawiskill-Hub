import argparse
import asyncio
import sys
# Add current directory to path so imports work
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import query_weather, format_weather_output

async def main():
    parser = argparse.ArgumentParser(description="Weather Skill CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # query-weather
    p_weather = subparsers.add_parser("query-weather", help="Query weather for a city")
    p_weather.add_argument("--city", help="City name (e.g., '北京')")
    p_weather.add_argument("--adcode", help="City Adcode (e.g., '110000')")
    p_weather.add_argument("--extended", action="store_true", help="Return extended weather data")
    p_weather.add_argument("--forecast", action="store_true", help="Return 3-day forecast")
    p_weather.add_argument("--indices", action="store_true", help="Return life indices")

    args = parser.parse_args()

    if args.command == "query-weather":
        if not args.city and not args.adcode:
            print("Error: Either --city or --adcode is required.")
            sys.exit(1)
            
        result = await query_weather(
            city=args.city,
            adcode=args.adcode,
            extended=args.extended,
            forecast=args.forecast,
            indices=args.indices
        )
        print(format_weather_output(result))
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
