def parse_supervision_pairs(values: list[str]) -> list[tuple[int, int]]:
    pairs = set()
    for value in values:
        parts = value.split(":")
        if len(parts) != 2 or any(
            not part.isascii() or not part.isdecimal() or len(part) > 10 for part in parts
        ):
            raise ValueError("Selecione um projeto e um curso válidos.")
        project, course = map(int, parts)
        if not (0 < project <= 2147483647 and 0 < course <= 2147483647):
            raise ValueError("Selecione um projeto e um curso válidos.")
        pairs.add((project, course))
    return sorted(pairs)
