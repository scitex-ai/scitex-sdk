"""Real PDF.js browser qualification, no live projects or service dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def fixture_pdf() -> bytes:
    """Two pages, cropped/rotated first page and an internal destination link."""
    text1 = b"BT /F1 12 Tf 60 700 Td (SDK fixture searchable text) Tj ET"
    text2 = b"BT /F1 12 Tf 60 700 Td (Second page destination) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 500 760] /CropBox [20 30 480 730] /Rotate 90 /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R /Annots [8 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 500 760] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(text1)).encode()
        + b" >>\nstream\n"
        + text1
        + b"\nendstream",
        b"<< /Length "
        + str(len(text2)).encode()
        + b" >>\nstream\n"
        + text2
        + b"\nendstream",
        b"<< /Type /Annot /Subtype /Link /Rect [60 620 240 655] /Border [0 0 0] /Dest [4 0 R /Fit] >>",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:])
    data += f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    bundle = repo / "src/scitex_sdk/ui/static/scitex_sdk/ui/js/app/pdf-viewer.js"
    vendor = repo / "node_modules/pdfjs-dist/build"
    html = """<div id="viewer" style="width:750px;height:480px;overflow:auto"></div>
<script type="module">
import {createPdfViewer} from '/viewer.js';
import * as pdfjs from '/pdf.mjs';
window.surfaces=[];window.renders=[];
window.viewer=createPdfViewer({container:document.querySelector('#viewer'),pdfjs,workerSrc:'/pdf.worker.mjs',textLayer:true,linkLayer:true,hooks:{onPageRender:(page,viewport,surface)=>{window.surfaces[page-1]=surface;window.renders.push({page,...viewport})}}});
viewer.setInteractive(false);await viewer.load('/fixture.pdf');window.ready=true;
</script>"""
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        def serve(route):
            name = route.request.url.split("/")[-1]
            if name == "viewer.js":
                route.fulfill(content_type="text/javascript", body=bundle.read_bytes())
            elif name in ["pdf.mjs", "pdf.worker.mjs"]:
                route.fulfill(
                    content_type="text/javascript", body=(vendor / name).read_bytes()
                )
            elif name == "fixture.pdf":
                route.fulfill(content_type="application/pdf", body=fixture_pdf())
            else:
                route.fulfill(content_type="text/html", body=html)

        page.route("http://pdf.test/**", serve)
        page.goto("http://pdf.test/")
        page.wait_for_function("window.ready===true")
        assert page.locator("#viewer canvas").count() == 4
        assert (
            "SDK fixture searchable text"
            in page.locator(".stx-pdf-text-layer").first.inner_text()
        )
        proof = page.evaluate("""() => {
const s=surfaces[0],point=s.pdfToViewportPoint(80,680),back=s.viewportToPdfPoint(...point);
const span=s.element.querySelector('.stx-pdf-text-layer span');let range=document.createRange();range.selectNodeContents(span);getSelection().removeAllRanges();getSelection().addRange(range);
return {back,selected:getSelection().toString(),rotationWidth:renders[0].width,rotationHeight:renders[0].height,rect:s.pdfToViewportRect([60,620,240,655]),textRect:[span.getBoundingClientRect().width,span.getBoundingClientRect().height]};}""")
        assert proof["back"] == [80, 680], proof
        assert proof["rotationWidth"] == 1050 and proof["rotationHeight"] == 690, proof
        assert proof["selected"] == "SDK fixture searchable text", proof
        assert all(value > 0 for value in proof["textRect"]), proof
        page.locator(".stx-pdf-link-layer a").click()
        page.wait_for_function('document.querySelector("#viewer").scrollTop>0')
        old = page.evaluate_handle("window.surfaces[0].element")
        page.evaluate("window.viewer.setScale(2)")
        assert old.evaluate("(element)=>!element.isConnected")
        assert page.locator(".stx-pdf-text-layer").count() == 2
        page.evaluate("window.viewer.destroy()")
        assert (
            page.locator("#viewer").evaluate("(element)=>element.childElementCount")
            == 0
        )
        assert errors == [], errors
        print(
            json.dumps(
                {
                    "rendered_pages": 2,
                    "crop_rotation_roundtrip": proof,
                    "internal_link_navigated": True,
                    "scale_replaced_surfaces": True,
                    "destroy_removed_layers": True,
                    "page_errors": errors,
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
