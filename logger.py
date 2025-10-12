LOGGING_ENABLED = True

def log(message, level=None):
    if LOGGING_ENABLED:
        if level:
            print(f"[DatablockNodes] [{level.upper()}] {message}")
        else:
            print(f"[DatablockNodes] {message}")
