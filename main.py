import json
import re
import sys
from pathlib import Path

import pymupdf


def scan_pages(pdf_path: Path) -> None:
    doc = pymupdf.open(pdf_path)
    problems = []

    reg_kangxi_radicals = re.compile(r"[\u2F00-\u2FD5]")
    for i in range(doc.page_count):
        page = doc[i]
        nombre = page.get_label()
        if nombre == "":
            nombre == f"{(i + 1):03}/{doc.page_count:03}"
        for word in page.get_text("words"):
            text = word[4]
            kangxis = reg_kangxi_radicals.findall(text)
            for k in kangxis:
                problems.append({"nombre": nombre, "text": text, "found": k})
            if "判夕" in text:
                problems.append({"nombre": nombre, "text": text, "found": "判夕"})

    doc.close()

    out_path = pdf_path.with_name(f"{pdf_path.stem}_problems.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(problems, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    path = Path(sys.argv[1])
    if path.is_file():
        if path.suffix == ".pdf":
            scan_pages(path)
        else:
            print("invalid path", str(path))
    else:
        for p in path.glob("*.pdf"):
            scan_pages(p)
