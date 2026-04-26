#!/usr/bin/env python3
"""Render about.md into a styled PDF using WeasyPrint."""
from pathlib import Path
import markdown
from weasyprint import HTML, CSS

HERE = Path(__file__).parent
md_text = (HERE / "about.md").read_text(encoding="utf-8")

html_body = markdown.markdown(
    md_text,
    extensions=["extra", "sane_lists", "smarty"],
)

css = """
@page {
  size: A4;
  margin: 22mm 20mm 22mm 20mm;
  @bottom-center {
    content: "Smadex Cooking  •  HackUPC 2026  •  smadex.cooking";
    font-family: "Helvetica Neue", "Inter", Arial, sans-serif;
    font-size: 8.5pt;
    color: #888;
  }
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font-family: "Helvetica Neue", "Inter", Arial, sans-serif;
    font-size: 8.5pt;
    color: #888;
  }
}

html {
  font-family: "Helvetica Neue", "Inter", "Segoe UI", Arial, sans-serif;
  font-size: 10.5pt;
  color: #1a1a1a;
  line-height: 1.55;
}

body {
  margin: 0;
}

.cover {
  border-bottom: 1px solid #e5e5e5;
  padding-bottom: 14px;
  margin-bottom: 22px;
}

.cover .eyebrow {
  font-size: 8.5pt;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #6b6b6b;
  margin-bottom: 6px;
  font-weight: 600;
}

.cover .title {
  font-size: 22pt;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #0d0d0d;
  margin: 0 0 4px 0;
}

.cover .subtitle {
  font-size: 11pt;
  color: #4a4a4a;
  font-weight: 400;
  margin: 0;
}

.cover .meta {
  margin-top: 12px;
  font-size: 9pt;
  color: #6b6b6b;
  display: flex;
  gap: 14px;
}

.cover .meta span::before {
  content: "•";
  margin-right: 8px;
  color: #c4c4c4;
}

.cover .meta span:first-child::before {
  content: "";
  margin-right: 0;
}

h2 {
  font-size: 13.5pt;
  font-weight: 700;
  color: #0d0d0d;
  margin: 22px 0 8px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid #ececec;
  letter-spacing: -0.005em;
  page-break-after: avoid;
}

h3 {
  font-size: 11pt;
  font-weight: 600;
  color: #1a1a1a;
  margin: 14px 0 6px 0;
  page-break-after: avoid;
}

p {
  margin: 0 0 9px 0;
}

ul, ol {
  margin: 6px 0 10px 0;
  padding-left: 18px;
}

li {
  margin-bottom: 5px;
}

li > p {
  margin: 0 0 4px 0;
}

strong {
  color: #0d0d0d;
  font-weight: 600;
}

a {
  color: #1f4dd8;
  text-decoration: none;
  border-bottom: 1px dotted #b9c6f0;
}

code {
  font-family: "JetBrains Mono", "SF Mono", "Menlo", monospace;
  font-size: 9pt;
  background: #f5f5f5;
  padding: 1px 4px;
  border-radius: 3px;
  color: #b3284a;
}

blockquote {
  border-left: 3px solid #d4d4d4;
  margin: 10px 0;
  padding: 2px 12px;
  color: #4a4a4a;
}

/* Avoid widows/orphans on paragraphs */
p, li {
  orphans: 2;
  widows: 2;
}
"""

cover = """
<div class="cover">
  <div class="eyebrow">HackUPC 2026  ·  Smadex Challenge Submission</div>
  <h1 class="title">Smadex Cooking</h1>
  <p class="subtitle">Creative intelligence for mobile advertising. The aggregate is a comfort blanket; the slice is the diagnosis.</p>
  <div class="meta">
    <span>smadex.cooking</span>
    <span>Andrew Robertson · Krish Mathur · Aditya Shah</span>
    <span>Barcelona, 24–26 April 2026</span>
  </div>
</div>
"""

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Smadex Cooking — About</title>
</head>
<body>
{cover}
{html_body}
</body>
</html>
"""

out = HERE / "about.pdf"
HTML(string=full_html, base_url=str(HERE)).write_pdf(
    str(out),
    stylesheets=[CSS(string=css)],
)
print(f"wrote {out}")
