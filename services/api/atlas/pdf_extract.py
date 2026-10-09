"""Fast, page-complete PDF extraction with tables kept as coherent evidence."""

import re
import os
import statistics
from collections.abc import Callable
import pymupdf
from .extraction import Block, BoundedBlocks, ocr_image


def clean(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text).strip()


def printed_pages(page) -> list[str]:
    footer = page.get_text(
        "words",
        clip=pymupdf.Rect(
            0, page.rect.height * 0.94, page.rect.width, page.rect.height
        ),
    )
    return [
        word[4]
        for word in sorted(footer, key=lambda word: word[0])
        if re.fullmatch(r"\d{1,3}", word[4])
    ]


def panels(page):
    if page.rect.width / page.rect.height > 1.35 and len(printed_pages(page)) >= 2:
        midpoint = page.rect.width / 2
        return [
            pymupdf.Rect(0, 0, midpoint, page.rect.height),
            pymupdf.Rect(midpoint, 0, page.rect.width, page.rect.height),
        ]
    return [page.rect]


def layout(page, rect) -> str:
    """Keep horizontal alignment of unruled subcolumns (years, genders, totals)."""
    words = page.get_text("words", clip=rect)
    if not words:
        return ""
    height = statistics.median(word[3] - word[1] for word in words)
    lines = []
    for word in sorted(words, key=lambda word: (word[1], word[0])):
        if not lines or abs(word[1] - lines[-1][0]) > max(2, height * 0.4):
            lines.append((word[1], [word]))
        else:
            lines[-1][1].append(word)
    char_width = max(2, height * 0.43)
    output = []
    for _, line in lines:
        rendered = ""
        for word in sorted(line, key=lambda word: word[0]):
            column = max(0, round((word[0] - rect.x0) / char_width))
            rendered += " " * max(1, column - len(rendered)) + word[4]
        output.append(rendered.rstrip())
    return clean("\n".join(output))


def extract_pdf(
    data: bytes, progress: Callable[[int, int], None] | None = None
) -> tuple[list[Block], str | None]:
    blocks = BoundedBlocks()
    ocr_count = 0
    table_count = 0
    table_errors = 0
    with pymupdf.open(stream=data, filetype="pdf") as document:
        total_pages = len(document)
        if document.needs_pass:
            raise ValueError(
                "Encrypted PDFs are not supported. Upload a decrypted copy."
            )
        if len(document) > 1500:
            raise ValueError("PDFs are limited to 1,500 pages per file.")
        for page_index, page in enumerate(document):
            page_number = page_index + 1
            printed = printed_pages(page)
            label = f"PDF page {page_number}" + (
                f" · printed {'–'.join(printed)}" if printed else ""
            )
            base = {
                "kind": "page",
                "page": page_number,
                "printed_pages": printed,
                "label": label,
                "pipeline": "pdf-v2",
            }
            full_text = clean(page.get_text("text"))
            if len(full_text) < 30 and page.get_images():
                ocr_count += 1
                if ocr_count > 200:
                    raise ValueError(
                        "Scanned PDFs are limited to 200 OCR pages per file."
                    )
                # MuPDF's native OCR avoids rendering subprocesses and carries
                # the recognized text back to real PDF page coordinates.
                try:
                    text = page.get_text(
                        textpage=page.get_textpage_ocr(
                            language="eng",
                            dpi=150,
                            full=True,
                            tessdata=os.environ.get("TESSDATA_PREFIX"),
                        )
                    )
                except (RuntimeError, ValueError):
                    image = page.get_pixmap(
                        matrix=pymupdf.Matrix(
                            min(2, 2000 / max(page.rect.width, page.rect.height)),
                            min(2, 2000 / max(page.rect.width, page.rect.height)),
                        )
                    )
                    text = ocr_image(image.tobytes("png"))
                if text.strip():
                    blocks.append(
                        Block(text, {**base, "ocr": True, "label": label + " · OCR"})
                    )
            else:
                for panel_index, panel in enumerate(panels(page)):
                    text = clean(page.get_text("text", clip=panel, sort=True))
                    if text:
                        blocks.append(Block(text, {**base, "panel": panel_index + 1}))
                # Process one page at a time; figures/images remain outside model context.
                if len(re.findall(r"\d", full_text)) >= 8:
                    try:
                        found = page.find_tables()
                        for table_index, table in enumerate(found.tables):
                            rows = table.extract()
                            if not rows or table.col_count < 2:
                                continue
                            if not any(
                                re.search(r"\d", str(cell or ""))
                                for row in rows
                                for cell in row
                            ):
                                continue
                            bbox = pymupdf.Rect(table.bbox)
                            panel = next(
                                (
                                    panel
                                    for panel in panels(page)
                                    if panel.contains(bbox.tl)
                                ),
                                page.rect,
                            )
                            context_rect = pymupdf.Rect(
                                max(panel.x0, bbox.x0 - 5),
                                max(0, bbox.y0 - 110),
                                min(panel.x1, bbox.x1 + 5),
                                bbox.y1 + 3,
                            )
                            context = layout(page, context_rect)
                            # Cell extraction may merge unruled numeric subcolumns. The
                            # original aligned layout preserves their actual year/gender labels.
                            title = clean(
                                page.get_text(
                                    "text",
                                    clip=pymupdf.Rect(
                                        panel.x0, 0, panel.x1, min(65, page.rect.height)
                                    ),
                                    sort=True,
                                )
                            )[:400]
                            headers = " | ".join(
                                clean(str(name or "")) for name in table.header.names
                            )
                            row_texts = [
                                " | ".join(
                                    clean(str(cell or "")).replace("\n", " / ")
                                    for cell in row
                                )
                                for row in rows
                            ]
                            table_prefix = f"{title}\nTABLE EVIDENCE — {label}\nOriginal column layout:\n{context}\nExtracted column headers: {headers}\n"
                            # Most corporate tables fit in one block; do not detach a
                            # numeric row from its column context by character slicing.
                            if len(table_prefix) > 11000:
                                table_prefix = table_prefix[:11000]
                            body = "\n".join(row_texts)
                            table_count += 1
                            blocks.append(
                                Block(
                                    table_prefix + "Rows:\n" + body,
                                    {
                                        **base,
                                        "kind": "table",
                                        "table": table_index + 1,
                                        "label": label + f" · table {table_index + 1}",
                                        "structured": True,
                                        "column_headers": table.header.names,
                                        "table_header": table_prefix,
                                    },
                                )
                            )
                    except (ValueError, RuntimeError):
                        table_errors += 1
            if progress:
                progress(page_number, len(document))
    if not blocks:
        raise ValueError("No readable text was found in this PDF.")
    note = f"All {total_pages} PDF pages read; {table_count} structured tables indexed."
    if ocr_count:
        note += f" {ocr_count} pages used OCR; verify important numbers."
    if table_errors:
        note += f" {table_errors} pages used text layout fallback for tables."
    return blocks, note
