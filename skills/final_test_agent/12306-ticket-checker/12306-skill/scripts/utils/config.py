import os

class Settings:
    def __init__(self):
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.debug = os.getenv("DEBUG", "False").lower() == "true"

def get_settings():
    return Settings()
