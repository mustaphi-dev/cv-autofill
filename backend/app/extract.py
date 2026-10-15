"""CV file to plain text in reading order, for the parser. Files are untrusted:
each one is read in a separate worker process with a time and memory limit,
so a crafted file can only kill its own worker. Nothing is written to disk."""

import io
import itertools
import multiprocessing
import re
import resource
import sys
import threading
import zipfile
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as Timeout
from concurrent.futures.process import BrokenProcessPool
from typing import Any

import docx
import pdfplumber
from docx.oxml.ns import qn
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfplumber.utils.exceptions import PdfminerException

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGES = 20
MAX_UNZIPPED = 50 * 1024 * 1024  # A DOCX is a zip: stop zip bombs.
TIMEOUT = 10  # seconds
# Address space per worker (Linux only). A worker needs about 110 MB before it
# reads anything; Render's smallest instance has 512 MB for everything.
MEMORY = 256 * 1024 * 1024
MIN_TEXT = 100  # characters; below this a PDF is treated as scanned

NOT_SUPPORTED = "Upload a PDF or DOCX file."
TOO_BIG = "The file must be under 5 MB."
TOO_LONG = f"CVs over {MAX_PAGES} pages are not supported."
SCANNED = "This PDF looks scanned. Upload a text-based PDF or DOCX."
LOCKED = "This PDF is password-protected. Remove the password and try again."
UNREADABLE = "We couldn't read this file. Try exporting it again as PDF or DOCX."


class Unreadable(Exception):
    """The file cannot be turned into text. The message is for the user."""


def extract(data: bytes) -> str:
    """The CV's text, or Unreadable with a message for the user."""
    if len(data) > MAX_BYTES:
        raise Unreadable(TOO_BIG)
    # ponytail: one file at a time keeps memory bounded on a 512 MB instance.
    # A file takes well under a second; allow more workers on a bigger one.
    with (
        _one_at_a_time,
        ProcessPoolExecutor(
            1, mp_context=_CONTEXT, initializer=_limit, initargs=(MEMORY,)
        ) as pool,
    ):
        future = pool.submit(_read, data)
        try:
            return future.result(timeout=TIMEOUT)
        except Timeout:
            pool.kill_workers()
            raise Unreadable(UNREADABLE) from None
        except BrokenProcessPool:  # The worker died, e.g. out of memory.
            raise Unreadable(UNREADABLE) from None


def _limit(memory: int) -> None:
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))


def _read(data: bytes) -> str:
    """Runs in the worker. Any parser error means an unreadable file. The
    original error is dropped, not chained: its message can quote the file."""
    try:
        if data.startswith(b"%PDF-"):
            return _pdf(data)
        if data.startswith(b"PK\x03\x04"):
            return _docx(data)
    except Unreadable:
        raise
    except Exception:  # noqa: BLE001 - any parser failure means the same thing
        raise Unreadable(UNREADABLE) from None
    raise Unreadable(NOT_SUPPORTED)


# PDF ---------------------------------------------------------------------

Word = dict[str, Any]
GAP = 20  # points; a wider gap inside a line becomes " | " (tables, dates)


def _pdf(data: bytes) -> str:
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except PdfminerException as error:
        if isinstance(error.args[0], PDFPasswordIncorrect):
            raise Unreadable(LOCKED) from None
        raise
    with pdf:
        if len(pdf.pages) > MAX_PAGES:
            raise Unreadable(TOO_LONG)
        pages, links = [], []
        for page in pdf.pages:
            pages.append(_page(page.extract_words(), float(page.width)))
            links += [link["uri"] for link in page.hyperlinks]
            page.close()  # Frees its cache: 20 pages kept use ~360 MB, not ~70.
        text = "\n\n".join(page for page in pages if page)
        if len(text) < MIN_TEXT:
            raise Unreadable(SCANNED)
        return _with_links(text, links)


def _page(words: list[Word], width: float) -> str:
    rows = _rows(words)
    gutter = _gutter(rows, width)
    if gutter is None:
        return "\n".join(_line(row) for row in rows)
    # Rows that cross the gutter are full width (name, contact, footer). Between
    # them, read the whole left column, then the whole right column.
    out: list[str] = []
    left: list[Word] = []
    right: list[Word] = []
    for row in rows:
        if _crosses(row, gutter):
            out += _column(left) + _column(right) + [_line(row)]
            left, right = [], []
        else:
            left += [w for w in row if w["x1"] <= gutter]
            right += [w for w in row if w["x0"] >= gutter]
    out += _column(left) + _column(right)
    return "\n".join(out)


def _rows(words: list[Word]) -> list[list[Word]]:
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and word["top"] - rows[-1][0]["top"] <= 3:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: w["x0"]) for row in rows]


# A glyph with no text mapping, e.g. "(cid:127)", or a private-use character
# such as Word's Symbol-font bullet. Leading a line, it is a bullet.
GLYPH = re.compile(r"\(cid:\d+\)|[\ue000-\uf8ff]")


def _line(row: list[Word]) -> str:
    line = row[0]["text"]
    for before, word in itertools.pairwise(row):
        line += (" | " if word["x0"] - before["x1"] > GAP else " ") + word["text"]
    if bullet := GLYPH.match(line):
        line = "• " + line[bullet.end() :].lstrip()
    return GLYPH.sub("", line)


def _column(words: list[Word]) -> list[str]:
    return [_line(row) for row in _rows(words)]


def _crosses(row: list[Word], x: float) -> bool:
    return any(w["x0"] - 5 < x < w["x1"] + 5 for w in row)


def _gutter(rows: list[list[Word]], width: float) -> float | None:
    """The x of the gap between two columns, if the page has two. Strict on
    purpose: a single-column CV with right-aligned dates also has a gap, but
    its text crosses the middle and the dates are a small share of it. A table
    has a gap too, but its rows pair up across it."""
    sized = [(row, sum(len(w["text"]) for w in row)) for row in rows]
    total = sum(n for _, n in sized)
    best, best_share = None, 0.0
    for x in range(int(width * 0.2), int(width * 0.8), 2):
        left = right = crossing = 0
        for row, n in sized:
            if _crosses(row, x):
                crossing += n
                if crossing > 0.2 * total:
                    break
            else:
                here = sum(len(w["text"]) for w in row if w["x1"] <= x)
                left, right = left + here, right + n - here
        share = min(left, right) / total if total else 0
        if crossing <= 0.2 * total and share >= 0.1 and share > best_share:
            best, best_share = float(x), share
    if best is not None:
        # Rows that pair up across the gap are a table (label | value): those
        # read row by row. Columns run independently, so few rows pair up.
        sides = [
            {w["x1"] <= best for w in row} for row in rows if not _crosses(row, best)
        ]
        if sum(len(side) == 2 for side in sides) >= 0.8 * len(sides):
            return None
    return best


def _with_links(text: str, uris: list[str]) -> str:
    """CVs often show "LinkedIn" with the address only in the link."""
    missing = [uri for uri in dict.fromkeys(uris) if uri and uri not in text]
    return text + "\n\nLinks:\n" + "\n".join(missing) if missing else text


# DOCX --------------------------------------------------------------------

P, TBL, TR, TC = qn("w:p"), qn("w:tbl"), qn("w:tr"), qn("w:tc")
TEXT_BOX = qn("w:txbxContent")
# Word saves each text box twice: a modern copy and a fallback for old readers.
FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _docx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if "word/document.xml" not in archive.namelist():
            raise Unreadable(NOT_SUPPORTED)
        if sum(info.file_size for info in archive.infolist()) > MAX_UNZIPPED:
            raise Unreadable(UNREADABLE)
    document = docx.Document(io.BytesIO(data))
    # Each section repeats the header and footer: keep them once. The body
    # keeps its repeats (two jobs can share a title).
    header = [_blocks(s.header._element) for s in document.sections]
    footer = [_blocks(s.footer._element) for s in document.sections]
    lines = [
        *dict.fromkeys(itertools.chain(*header)),
        *_blocks(document.element.body),
        *dict.fromkeys(itertools.chain(*footer)),
    ]
    links = [
        rel.target_ref
        for rel in document.part.rels.values()
        if rel.is_external and rel.reltype.endswith("/hyperlink")
    ]
    return _with_links("\n".join(line for line in lines if line), links)


def _blocks(element: Any) -> Iterator[str]:
    for child in element:
        if child.tag == P:
            yield _paragraph(child)
            for box in child.iter(TEXT_BOX):
                if not any(a.tag == FALLBACK for a in box.iterancestors()):
                    yield from _blocks(box)
        elif child.tag == TBL:
            yield from _table(child)
        elif child.tag != FALLBACK:
            yield from _blocks(child)


def _paragraph(p: Any) -> str:
    text: str = p.text.strip()
    style = p.style or ""
    bullet = (p.pPr is not None and p.pPr.numPr is not None) or style.startswith("List")
    return f"• {text}" if text and bullet else text


def _table(table: Any) -> Iterator[str]:
    """A data table reads row by row. A layout table (cells holding several
    paragraphs, as in two-column templates) reads cell by cell."""
    for row in table.findall(TR):
        cells = [c for c in row if c.tag == TC]
        if all(len(c.findall(P)) <= 1 for c in cells):
            yield " | ".join(t for c in cells if (t := "".join(_blocks(c))))
        else:
            for cell in cells:
                yield from _blocks(cell)


# The worker is forked from a server that has already imported this module, so
# each file starts in a fresh process without paying the import cost again.
_CONTEXT = multiprocessing.get_context("forkserver")
_one_at_a_time = threading.Lock()
_CONTEXT.set_forkserver_preload([__name__])
