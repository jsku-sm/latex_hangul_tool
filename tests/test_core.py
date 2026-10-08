import tempfile
import unittest
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import EXAMPLES, NS, convert, parse_document, write_hwpx


class ConversionTests(unittest.TestCase):
    def test_known_mathematics(self):
        cases = {
            r"\frac{a+b}{c}": "{a + b} over {c}",
            r"\frac{1}{\frac{2}{3}}": "{1} over {{2} over {3}}",
            r"x^23": "x ^{2} 3",
            r"x^{23}": "x ^{23}",
            r"x_i^2": "x _{i} ^{2}",
            r"\frac12": "{1} over {2}",
            r"\sqrt[3]{x}": "root {3} of {x}",
            r"\lim_{x\to0}x": "lim _{x -> 0} x",
            r"\sin x+\cos x": "sin x + cos x",
            r"\binom{n}{r}": "{n} choose {r}",
            r"\begin{bmatrix}1&2\\3&4\end{bmatrix}": "bmatrix {1 & 2 # 3 & 4}",
            r"\begin{vmatrix}a&b\\c&d\end{vmatrix}": "dmatrix {a & b # c & d}",
            r"\left(\frac12\right)": "LEFT ( {1} over {2} RIGHT )",
            r"\bar{x}": "bar {x}",
            r"\alpha+\beta": "alpha + beta",
            r"x\leq2": "x leq 2",
            r"a\,b": "a ` b",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(convert(source), expected)

    def test_supported_examples(self):
        for name, source in EXAMPLES.items():
            with self.subTest(name=name):
                self.assertTrue(convert(source))

    def test_wrappers(self):
        for source in ["$x^2$", "$$x^2$$", r"\(x^2\)", r"\[x^2\]", "```latex\nx^2\n```"]:
            with self.subTest(source=source):
                self.assertEqual(convert(source), "x ^{2}")

    def test_invalid_or_unsupported_refuses(self):
        for source in ["", "{x", "x}", r"\fraq{1}{2}", r"\sqrt", r"\frac{a}",
                       r"x^", r"\frac{a}{b}\input{secret}", r"\write18{command}",
                       r"\begin{matrix}1\end{cases}", r"\begin{align}x&=1\end{align}",
                       r"\left(x", r"x\!y"]:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    convert(source)

    def test_limits(self):
        with self.assertRaises(ValueError):
            convert("x" * 10001)
        with self.assertRaises(ValueError):
            convert("{" * 100 + "x" + "}" * 100)

    def test_document_preserves_text_order(self):
        source = "분수 $\\frac{1}{2}$와 근호 \\(\\sqrt{2}\\)\n끝"
        parts = parse_document(source, "document")
        self.assertEqual([p.kind for p in parts], ["text", "equation", "text", "equation", "text"])
        self.assertEqual(parts[0].source, "분수 ")
        self.assertEqual(parts[2].source, "와 근호 ")
        self.assertEqual(parts[4].source, "\n끝")

    def test_document_missing_fence(self):
        for text in ["분수 $x", "분수 \\[x", "수식 없음"]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_document(text, "document")

    def test_all_parts_validate_before_writing(self):
        with self.assertRaises(ValueError):
            parse_document("$x^2$ 다음 $\\unknown{x}$", "document")

    def test_escaped_dollar(self):
        parts = parse_document(r"가격 \$5와 $x^2$", "document")
        self.assertEqual(sum(p.kind == "equation" for p in parts), 1)

    def test_no_xml_control_characters(self):
        with self.assertRaises(ValueError):
            parse_document("문장\x00$x$", "document")


class HwpxTests(unittest.TestCase):
    def test_native_objects_and_manifest(self):
        text = "비교 & 설명\n$" + EXAMPLES["근의 공식"] + "$\n$" + EXAMPLES["행렬"] + "$"
        parts = parse_document(text, "document")
        with tempfile.TemporaryDirectory() as d:
            path = write_hwpx(parts, Path(d) / "test.hwpx", 13)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(z.namelist()[0], "mimetype")
                self.assertEqual(z.getinfo("mimetype").compress_type, zipfile.ZIP_STORED)
                self.assertEqual(z.read("mimetype"), b"application/hwp+zip")
                for name in z.namelist():
                    if name.endswith((".xml", ".hpf", ".rdf")):
                        ET.fromstring(z.read(name))
                sec = ET.fromstring(z.read("Contents/section0.xml"))
                equations = sec.findall(".//hp:equation", NS)
                self.assertEqual(len(equations), 2)
                self.assertEqual([x.find("hp:script", NS).text for x in equations],
                                 [p.script for p in parts if p.kind == "equation"])
                self.assertEqual(len(sec.findall(".//hp:secPr", NS)), 1)
                self.assertEqual(len(sec.findall(".//hp:linesegarray", NS)), 0)
                self.assertIn("비교 & 설명", [n.text for n in sec.findall(".//hp:t", NS)])
                for eq in equations:
                    self.assertEqual(eq.get("baseUnit"), "1300")
                    self.assertGreater(int(eq.find("hp:sz", NS).get("height")), 0)
                    self.assertGreater(int(eq.find("hp:sz", NS).get("width")), 0)
                pkg = ET.fromstring(z.read("Contents/content.hpf"))
                for item in pkg.findall("opf:manifest/opf:item", NS):
                    self.assertIn(item.get("href"), z.namelist())
                # No old template equation remains.
                self.assertNotIn("pmatrix {1 & 0 # 0 & 1}", z.read("Contents/section0.xml").decode())

    def test_each_example_is_exportable(self):
        with tempfile.TemporaryDirectory() as d:
            for i, tex in enumerate(EXAMPLES.values()):
                with self.subTest(tex=tex):
                    write_hwpx(parse_document(tex), Path(d) / f"{i}.hwpx")

    def test_bad_size_or_width_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "keep.hwpx"
            dest.write_bytes(b"original")
            with self.assertRaises(ValueError):
                write_hwpx(parse_document("x"), dest, 99)
            self.assertEqual(dest.read_bytes(), b"original")
            with self.assertRaises(ValueError):
                write_hwpx(parse_document("+".join(["x"] * 150)), dest)
            self.assertEqual(dest.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
