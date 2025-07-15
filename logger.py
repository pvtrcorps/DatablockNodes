# C:/Users/anton/Desktop/addon/addons/DatablockNodes/logger.py
LOGGING_ENABLED = True

def log(message):
    if LOGGING_ENABLED:
        print(f"[DatablockNodes] {message}")
