from datetime import datetime

def validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def get_current_date_str() -> str:
    """Returns current date in YYYY-MM-DD format"""
    return datetime.now().strftime("%Y-%m-%d")
