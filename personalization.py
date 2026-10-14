"""Spreadsheet import and per-recipient variable rendering."""
import csv
import io
import re
from pathlib import Path

MISSING = {"", "null", "none", "nan", "n/a", "na", "0", "undefined", "-"}
TOKEN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


def missing(value):
    return value is None or str(value).strip().lower() in MISSING


def render(template, values):
    return TOKEN.sub(lambda m: str(values.get(m.group(1), m.group(0))), template)


def read_table(filename, content):
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        raw = content.decode("utf-8-sig") if not content.startswith((b"\xff\xfe", b"\xfe\xff")) else content.decode("utf-16")
        sample = raw[:8192]
        try: dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error: dialect = csv.excel
        rows = list(csv.reader(io.StringIO(raw), dialect))
    elif suffix == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        try: rows = list(wb.active.values)
        finally: wb.close()
    elif suffix == ".xls":
        try: import xlrd
        except ImportError as exc: raise ValueError("Для XLS установите xlrd из requirements.txt") from exc
        book = xlrd.open_workbook(file_contents=content)
        sheet = book.sheet_by_index(0)
        rows = [sheet.row_values(i) for i in range(sheet.nrows)]
    else:
        raise ValueError("Поддерживаются CSV, XLSX и XLS.")
    if not rows: raise ValueError("Таблица пуста.")
    width = max(map(len, rows))
    headers = [str(rows[0][i]).strip() if i < len(rows[0]) and not missing(rows[0][i]) else f"Столбец {i+1}" for i in range(width)]
    result=[]
    for raw in rows[1:]:
        cells=[str(raw[i]).strip() if i < len(raw) and raw[i] is not None else "" for i in range(width)]
        if not any(cells): continue
        email=cells[0]
        if not email or "@" not in email or "." not in email.rsplit("@",1)[-1]:
            raise ValueError(f"Некорректный email в строке {len(result)+2}: {email or '(пусто)'}")
        result.append(cells)
    if not result: raise ValueError("Нет строк с получателями.")
    if len(result)>10000: raise ValueError("Максимум 10 000 получателей в одном файле.")
    return {"headers":headers,"rows":result}


def prepare_rows(rows, columns):
    if not isinstance(rows,list) or not isinstance(columns,list): raise ValueError("Некорректные данные таблицы.")
    if len(rows)>10000 or len(columns)>100: raise ValueError("Таблица слишком большая.")
    names=set(); mappings=[]
    for item in columns:
        idx=item.get("index")
        name=str(item.get("name","")).strip()
        if not isinstance(idx,int) or idx<1 or not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*",name):
            raise ValueError("Названия переменных: латиница, цифры и _, первый символ — буква или _.")
        if name in names or name=="email": raise ValueError("Переменные должны быть уникальными; email зарезервирована.")
        names.add(name); mappings.append((idx,name,str(item.get("default", ""))))
    result={}
    for cells in rows:
        if not isinstance(cells,list) or not cells: raise ValueError("Некорректная строка таблицы.")
        email=str(cells[0]).strip()
        if "@" not in email or "." not in email.rsplit("@",1)[-1]: raise ValueError(f"Некорректный email: {email}")
        if email in result: raise ValueError(f"Повторяющийся email: {email}")
        values={"email":email}
        for idx,name,default in mappings:
            value=cells[idx] if idx<len(cells) else None
            values[name]=default if missing(value) else str(value)
        result[email]=values
    return result
