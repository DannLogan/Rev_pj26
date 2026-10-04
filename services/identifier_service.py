def format_next_identifier(existing_identifiers: list[str], width: int) -> str:
    numbers = [int(value) for value in existing_identifiers if str(value).isdigit()]
    next_number = max(numbers, default=0) + 1
    return str(next_number).zfill(width)
