"""Render six fictional fixture PDFs from the app's authoritative sample pages."""
import argparse
import html
import sys
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.sample_agreements import SAMPLES, sample_pages

SCENARIOS = ("shared_house", "early_exit", "house_rules")


def generate(font_dir: Path) -> None:
    archive = pymupdf.Archive(str(font_dir))
    for scenario in SCENARIOS:
        for language in ("en", "ar"):
            rtl = language == "ar"
            title = SAMPLES[scenario][language]["title"]
            notice = ("عقد افتراضي لأغراض الاختبار، وليس نموذجًا قانونيًا للاستخدام."
                      if rtl else "Fictional agreement for testing. Not a legal template.")
            direction = "rtl" if rtl else "ltr"
            css = """
                @font-face {font-family: Lease; src: url(arial.ttf);}
                @font-face {font-family: Lease; font-weight: bold; src: url(arialbd.ttf);}
                body {font-family: Lease; color: #172840; font-size: 12pt; line-height: 1.45;}
                h1 {font-size: 20pt; color: #312974; line-height: 1.35; margin: 0 0 8pt;}
                p {margin: 0 0 11pt;}
                .notice {font-size: 10pt; color: #4a5671; margin-bottom: 22pt;}
            """
            with pymupdf.open() as document:
                pages = sample_pages(scenario, language)
                for item in pages:
                    number = item["page"]
                    page = document.new_page(width=595, height=842)
                    page.draw_line((48, 47), (547, 47), color=(0.36, 0.32, 0.72), width=2)
                    body = "".join(f"<p>{html.escape(line)}</p>" for line in item["text"].splitlines() if line)
                    markup = (f'<div dir="{direction}" lang="{language}"><h1>{html.escape(title)}</h1>'
                              f'<p class="notice">{notice}</p>{body}</div>')
                    space, _ = page.insert_htmlbox(
                        pymupdf.Rect(48, 66, 547, 766), markup, css=css, archive=archive, scale_low=1
                    )
                    if space < 0:
                        raise ValueError(f"{scenario}/{language} page {number} overflow")
                    page.draw_line((48, 780), (547, 780), color=(0.65, 0.68, 0.76), width=0.6)
                    page.insert_text((48, 801), f"ClauseX AI  |  {number} / {len(pages)}", fontsize=10)
                document.set_metadata({"title": title, "author": "ClauseX AI", "subject": "Fictional test agreement"})
                document.subset_fonts()
                document.save(HERE / f"{scenario}-{language}.pdf", garbage=4, deflate=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font_dir", type=Path, help="Directory containing arial.ttf and arialbd.ttf")
    generate(parser.parse_args().font_dir)
