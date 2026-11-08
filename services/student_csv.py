import csv
import io
import unicodedata


def read_student_csv(content: bytes) -> list[tuple[int, list[str]]]:
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            source = content.decode("utf-16")
        except UnicodeDecodeError as error:
            raise ValueError("O arquivo UTF-16 está incompleto.") from error
    else:
        try:
            source = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            source = content.decode("latin-1")
    if "\x00" in source:
        raise ValueError("Salve a planilha como CSV UTF-8 e tente novamente.")

    first = next((line for line in source.splitlines() if line.strip()), "")
    if first.strip().lower() in {"sep=;", "sep=,"}:
        delimiter = first.strip()[-1]
        skip_directive = True
    else:
        delimiter = max((";", ",", "\t"), key=lambda sep: _delimiter_score(first, sep))
        skip_directive = False

    rows = []
    reader = csv.reader(io.StringIO(source, newline=""), delimiter=delimiter, strict=True)
    first_record = True
    try:
        while True:
            number = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                break
            if not any(field.strip() for field in row):
                continue
            if skip_directive:
                skip_directive = False
                continue
            if first_record:
                first_record = False
                if _is_header(row[0]):
                    continue
            rows.append((number, row))
            if len(rows) > 5000:
                raise ValueError("O CSV deve ter no máximo 5.000 registros.")
    except csv.Error as error:
        raise ValueError(f"Formato CSV inválido perto da linha {reader.line_num}.") from error

    if not rows:
        raise ValueError("O arquivo não contém alunos para importar.")
    return rows


def _is_header(value: str) -> bool:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return "".join(ch for ch in normalized if ch.isalnum()) in {
        "matricula", "matriculara", "ra", "registroacademico",
    }


def _delimiter_score(line: str, delimiter: str) -> tuple[bool, int]:
    row = next(csv.reader([line], delimiter=delimiter))
    if not row:
        return False, 0
    first = row[0].strip()
    return len(row) >= 2 and (_is_header(first) or first.isdecimal()), len(row)
