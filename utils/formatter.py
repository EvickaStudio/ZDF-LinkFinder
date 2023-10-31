def format_duration(milliseconds: int) -> str:
    """
    Formats the duration.

    Parameters:
    milliseconds (int): Duration in milliseconds

    Returns:
    str: Formatted duration as HH:MM:SS
    """
    seconds = milliseconds // 1000
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
