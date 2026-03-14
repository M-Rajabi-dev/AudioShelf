import os
import tempfile
import unittest
import zipfile

from ebook_content import EbookLoadError, load_ebook_content


class EbookContentTests(unittest.TestCase):
    def test_load_plain_text_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "book.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Hello\\n\\nWorld")

            content = load_ebook_content(path)
            self.assertIn("Hello", content.text)
            self.assertIn("World", content.text)
            self.assertTrue(content.chapters)
            self.assertEqual(content.chapters[0].start_offset, 0)

    def test_load_simple_epub(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "book.epub")
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr(
                    "META-INF/container.xml",
                    """<?xml version="1.0"?>
                    <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                      <rootfiles>
                        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
                      </rootfiles>
                    </container>"""
                )
                zf.writestr(
                    "OEBPS/content.opf",
                    """<?xml version="1.0" encoding="UTF-8"?>
                    <package version="2.0" xmlns="http://www.idpf.org/2007/opf">
                      <manifest>
                        <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
                      </manifest>
                      <spine toc="ncx">
                        <itemref idref="chap1"/>
                      </spine>
                    </package>"""
                )
                zf.writestr(
                    "OEBPS/chapter1.xhtml",
                    "<html><body><h1>Chapter One</h1><p>First paragraph.</p></body></html>"
                )

            content = load_ebook_content(path)
            self.assertIn("Chapter One", content.text)
            self.assertIn("First paragraph.", content.text)
            self.assertTrue(content.chapters)
            self.assertEqual(content.chapters[0].title, "Chapter One")

    def test_load_cbz_returns_placeholder_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "comic.cbz")
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("001.jpg", b"fake-image")
                zf.writestr("002.png", b"fake-image")

            content = load_ebook_content(path)
            self.assertIn("Comic archive detected.", content.text)
            self.assertIn("Total pages: 2.", content.text)

    def test_unsupported_extension_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "book.docx")
            with open(path, "wb") as f:
                f.write(b"not supported")

            with self.assertRaises(EbookLoadError):
                load_ebook_content(path)


if __name__ == "__main__":
    unittest.main()
