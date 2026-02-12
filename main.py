import json
import re
import sys
from itertools import groupby
from pathlib import Path

import pymupdf


def scan_pages(pdf_path: Path) -> None:
    print(f"処理開始：{str(pdf_path)}")
    doc = pymupdf.open(pdf_path)
    problems: list[dict[str, str | int | tuple[float, float, float, float]]] = []

    reg_kangxi_radicals = re.compile(r"[\u2F00-\u2FD5]")
    for page_index in range(doc.page_count):
        page = doc[page_index]
        nombre = page.get_label()
        if nombre == "":
            nombre = f"{(page_index + 1):03}/{doc.page_count:03}"
        else:
            nombre = f"p.{nombre}"

        # search for invalid text pattern
        for word in page.get_text("words"):
            text = word[4]
            rect = word[0:4]
            for kangxi_match in reg_kangxi_radicals.finditer(text):
                print(f"{nombre} 康煕部首「{kangxi_match.group()}」を検出")
                problems.append(
                    {
                        "page_index": page_index,
                        "nombre": nombre,
                        "text": text,
                        "position": kangxi_match.start(),
                        "found": kangxi_match.group(),
                        "rect": rect,
                    }
                )
            for bad_match in re.finditer(r"判夕", text):
                print(f"{nombre} 「判夕」（はんゆう）を検出")
                problems.append(
                    {
                        "page_index": page_index,
                        "nombre": nombre,
                        "text": text,
                        "position": bad_match.start(),
                        "found": bad_match.group(),
                        "rect": rect,
                    }
                )

        # search for large image
        for img in page.get_images():
            xref = img[0]
            image_stream = doc.xref_stream(xref)
            image_size = len(image_stream)
            if image_size < 6 * 1024 * 1024:
                continue

            print(f"{nombre} 6MBを超える画像を検出")
            img_rects = page.get_image_rects(xref)
            for rect in img_rects:
                problems.append(
                    {
                        "page_index": page_index,
                        "nombre": nombre,
                        "text": f"Large image: {image_size / (1024 * 1024):.2f}MB",
                        "position": -1,
                        "found": "",
                        "rect": (rect.x0, rect.y0, rect.x1, rect.y1),
                    }
                )

    if len(problems) < 1:
        print(f"問題は見つかりませんでした：{str(pdf_path)}")
        return

    out_json_path = pdf_path.with_name(f"{pdf_path.stem}_problems.json")
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(problems, f, indent=2, ensure_ascii=False)

    annot_pdf = pymupdf.Document()
    annot_pdf_path = out_json_path.with_suffix(".pdf")

    for idx, (page_index, group) in enumerate(
        groupby(problems, key=lambda p: p["page_index"])
    ):
        annot_pdf.insert_pdf(doc, from_page=page_index, to_page=page_index)
        page_to_annotate = annot_pdf[idx]
        grouped_problems = list(group)
        for g in grouped_problems:
            annot = page_to_annotate.add_rect_annot(pymupdf.Rect(g["rect"]))
            color = annot.colors
            if g["position"] != -1:
                color["stroke"] = [1.0, 0.0, 0.0]
                annot.set_info(
                    content=f"{int(g['position']) + 1}文字目「{g['found']}」"
                )
            else:
                color["stroke"] = [0.0, 0.0, 1.0]
                annot.set_info(content=g["text"])
            annot.set_colors(color)
            annot.update()

    annot_pdf.save(annot_pdf_path, garbage=3, clean=True, pretty=True)

    doc.close()
    annot_pdf.close()


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
