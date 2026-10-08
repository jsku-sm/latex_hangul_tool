"""Offline LaTeX conversion and native editable HWPX document export."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from vendor.equation.authoring import latex_to_eqedit
from vendor.equation.eqedit import EquationConversionError
from vendor.equation.measure import measure_equation

ROOT = Path(__file__).resolve().parent
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS = "http://www.hancom.co.kr/hwpml/2011/section"
OPF = "http://www.idpf.org/2007/opf/"
for prefix, uri in (("hp", HP), ("hs", HS), ("opf", OPF)):
    ET.register_namespace(prefix, uri)
NS = {"hp": HP, "hs": HS, "opf": OPF}


@dataclass(frozen=True)
class Part:
    kind: str
    source: str
    script: str = ""


def normalize_latex(source: str) -> str:
    text = source.strip()
    match = re.fullmatch(r"```(?:latex|tex)?\s*\n(.*?)\n```", text, re.S)
    if match:
        text = match.group(1).strip()
    for left, right in ((r"\[", r"\]"), (r"\(", r"\)"), ("$$", "$$"), ("$", "$")):
        if text.startswith(left) and text.endswith(right) and len(text) > len(left) + len(right):
            text = text[len(left):-len(right)].strip()
            break
    # Comments end at a newline. Escaped percent signs stay literal.
    text = re.sub(r"(?<!\\)%[^\n]*", "", text)
    return text


def convert(source: str) -> str:
    if len(source) > 10000:
        raise ValueError("수식 하나는 10,000자 이하로 입력해 주세요.")
    text = normalize_latex(source)
    if not text:
        raise ValueError("LaTeX 수식을 입력해 주세요.")
    # Source text is never evaluated or passed to a shell.
    try:
        return latex_to_eqedit(text)
    except RecursionError as exc:
        raise ValueError("수식 중첩이 너무 깊습니다. 수식을 나누어 주세요.") from exc


def _escaped(text: str, i: int) -> bool:
    n = 0
    j = i - 1
    while j >= 0 and text[j] == "\\":
        n += 1
        j -= 1
    return n % 2 == 1


def parse_document(source: str, mode: str = "formula") -> list[Part]:
    """Validate everything before any file write or native document mutation.

    Document mode recognizes $, $$, \\( \\), and \\[ \\] explicitly.
    Unmatched delimiters are errors, never silently ignored.
    """
    if len(source) > 200000:
        raise ValueError("한 번에 200,000자 이하로 입력해 주세요.")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in source):
        raise ValueError("입력에 사용할 수 없는 제어 문자가 포함되어 있습니다.")
    if mode == "formula":
        return [Part("equation", normalize_latex(source), convert(source))]
    if mode != "document":
        raise ValueError("알 수 없는 입력 방식입니다.")
    parts: list[Part] = []
    text_start = i = count = 0
    while i < len(source):
        opener = closer = None
        if not _escaped(source, i):
            if source.startswith("$$", i):
                opener = closer = "$$"
            elif source[i] == "$":
                opener = closer = "$"
            elif source.startswith(r"\(", i):
                opener, closer = r"\(", r"\)"
            elif source.startswith(r"\[", i):
                opener, closer = r"\[", r"\]"
        if not opener:
            i += 1
            continue
        if i > text_start:
            parts.append(Part("text", source[text_start:i]))
        start = i + len(opener)
        end = start
        while end < len(source):
            if source.startswith(closer, end) and not _escaped(source, end):
                break
            end += 1
        if end == len(source):
            raise ValueError(f"{opener}로 시작한 수식의 닫는 기호 {closer}가 없습니다. (위치 {i + 1})")
        body = source[start:end]
        count += 1
        if count > 200:
            raise ValueError("한 번에 수식 200개까지 변환할 수 있습니다.")
        try:
            parts.append(Part("equation", normalize_latex(body), convert(body)))
        except (EquationConversionError, ValueError) as exc:
            raise ValueError(f"{count}번째 수식: {exc}") from exc
        i = text_start = end + len(closer)
    if text_start < len(source):
        parts.append(Part("text", source[text_start:]))
    if count == 0:
        raise ValueError("문장 + 수식 모드에서는 수식을 $...$ 또는 \\[...\\]로 감싸 주세요.")
    return parts


def _xml(element: ET.Element) -> bytes:
    return ET.tostring(element, encoding="utf-8", xml_declaration=True)


def write_hwpx(parts: list[Part], path: Path, size_pt: int = 12) -> Path:
    """Write equation controls, not images, into a HWPX package.

    Character/paragraph definitions and section controls come from a Hancom-saved
    Apache-licensed upstream fixture. Cached line layout is removed for reflow.
    Equation boxes are estimated by the upstream font metric model.
    """
    if not 8 <= size_pt <= 32:
        raise ValueError("수식 크기는 8~32pt로 설정해 주세요.")
    path = Path(path).expanduser().resolve()
    if path.suffix.lower() != ".hwpx":
        raise ValueError("저장 파일의 확장자는 .hwpx여야 합니다.")
    with zipfile.ZipFile(ROOT / "assets" / "equation_template.hwpx") as z:
        files = {name: z.read(name) for name in z.namelist()}
    sec = ET.fromstring(files["Contents/section0.xml"])
    original = sec.find("hp:p", NS)
    eq_template = deepcopy(sec.find(".//hp:equation", NS))
    props = deepcopy(original.find("hp:run", NS))
    for element in list(sec):
        sec.remove(element)
    paragraph_no = 0
    equation_no = 0

    def new_paragraph() -> ET.Element:
        nonlocal paragraph_no
        paragraph_no += 1
        p = ET.SubElement(sec, f"{{{HP}}}p", {
            "id": str(paragraph_no), "paraPrIDRef": "0", "styleIDRef": "0",
            "pageBreak": "0", "columnBreak": "0", "merged": "0",
        })
        if paragraph_no == 1:
            p.append(props)
        return p

    p = new_paragraph()
    for part in parts:
        if part.kind == "text":
            lines = part.source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            for i, line in enumerate(lines):
                if i:
                    p = new_paragraph()
                run = ET.SubElement(p, f"{{{HP}}}run", {"charPrIDRef": "0"})
                ET.SubElement(run, f"{{{HP}}}t").text = line
        else:
            equation_no += 1
            box = measure_equation(part.script, base_unit=size_pt * 100)
            if box.width > 42520:
                raise ValueError(f"{equation_no}번째 수식이 A4 본문 폭보다 깁니다. 수식 크기를 줄이거나 나누어 주세요.")
            if box.height > 60000:
                raise ValueError("수식 높이가 한 페이지보다 큽니다. 수식을 나누어 주세요.")
            run = ET.SubElement(p, f"{{{HP}}}run", {"charPrIDRef": "0"})
            eq = deepcopy(eq_template)
            eq.set("id", str(1000000 + equation_no))
            eq.set("zOrder", str(equation_no - 1))
            eq.set("baseUnit", str(size_pt * 100))
            eq.set("baseLine", str(box.base_line))
            eq.find("hp:script", NS).text = part.script
            eq.find("hp:sz", NS).set("width", str(max(1, box.width)))
            eq.find("hp:sz", NS).set("height", str(max(1, box.height)))
            eq.find("hp:pos", NS).set("affectLSpacing", "1")
            run.append(eq)
            ET.SubElement(run, f"{{{HP}}}t")
    for para in sec:
        if not para.findall("hp:run", NS):
            run = ET.SubElement(para, f"{{{HP}}}run", {"charPrIDRef": "0"})
            ET.SubElement(run, f"{{{HP}}}t")
    files["Contents/section0.xml"] = _xml(sec)
    metadata = ET.fromstring(files["Contents/content.hpf"])
    metadata.find("opf:metadata/opf:title", NS).text = "LaTeX 수식 변환"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for item in metadata.findall("opf:metadata/opf:meta", NS):
        name = item.get("name")
        if name in {"creator", "lastsaveby"}:
            item.text = "LaTeX to Hangul"
        elif name in {"CreatedDate", "ModifiedDate", "date"}:
            item.text = now
    files["Contents/content.hpf"] = _xml(metadata)
    files["Preview/PrvText.txt"] = "".join(p.source for p in parts).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as temp:
        tmp = Path(temp.name)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("mimetype", files.pop("mimetype"), compress_type=zipfile.ZIP_STORED)
            for name, content in files.items():
                z.writestr(name, content)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    return path


EXAMPLES = {
    "근의 공식": r"x=\frac{-b\pm\sqrt{b^2-4ac}}{2a}",
    "분수와 제곱근": r"\frac{a+b}{\sqrt{c}}",
    "시그마": r"\sum_{k=1}^{n} k=\frac{n(n+1)}{2}",
    "극한": r"\lim_{x\to 0}\frac{\sin x}{x}=1",
    "적분": r"\int_{0}^{1}x^2\,dx=\frac{1}{3}",
    "행렬": r"A=\begin{pmatrix}1 & 2 \\ 3 & 4\end{pmatrix}",
    "경우 나누기": r"f(x)=\begin{cases}x^2 & x\geq 0 \\ -x & x<0\end{cases}",
    "집합": r"A\cap B=\{x\mid x\in A,\ x\in B\}",
    "조합": r"\binom{n}{r}=\frac{n!}{r!(n-r)!}",
    "벡터": r"\overrightarrow{AB}=\begin{pmatrix}3\\4\end{pmatrix}",
}
