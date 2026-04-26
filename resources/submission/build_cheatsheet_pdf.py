#!/usr/bin/env python3
"""Render cheatsheet.md into a styled PDF using WeasyPrint."""
from pathlib import Path
import markdown
from weasyprint import HTML, CSS

HERE = Path(__file__).parent
md_text = (HERE / "cheatsheet.md").read_text(encoding="utf-8")

# Strip the H1 since the cover handles the title
lines = md_text.splitlines()
if lines and lines[0].startswith("# "):
    lines = lines[1:]
md_body = "\n".join(lines).lstrip()

html_body = markdown.markdown(
    md_body,
    extensions=["extra", "sane_lists", "smarty", "tables", "fenced_code"],
)

css = """
@page {
  size: A4;
  margin: 18mm 16mm 18mm 16mm;
  @bottom-center {
    content: "Smadex Cooking  •  Team Cheat Sheet  •  CONFIDENTIAL  •  smadex.cooking";
    font-family: "Helvetica Neue", "Inter", Arial, sans-serif;
    font-size: 8pt;
    color: #888;
  }
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font-family: "Helvetica Neue", "Inter", Arial, sans-serif;
    font-size: 8pt;
    color: #888;
  }
}

html {
  font-family: "Helvetica Neue", "Inter", "Segoe UI", Arial, sans-serif;
  font-size: 9.5pt;
  color: #1a1a1a;
  line-height: 1.45;
}

body { margin: 0; }

.cover {
  border-bottom: 1px solid #e5e5e5;
  padding-bottom: 12px;
  margin-bottom: 18px;
}

.cover .eyebrow {
  font-size: 8pt;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #b8344e;
  margin-bottom: 6px;
  font-weight: 700;
}

.cover .title {
  font-size: 22pt;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #0d0d0d;
  margin: 0 0 4px 0;
}

.cover .subtitle {
  font-size: 10.5pt;
  color: #4a4a4a;
  font-weight: 400;
  margin: 0;
}

.cover .meta {
  margin-top: 10px;
  font-size: 8.5pt;
  color: #6b6b6b;
}

.cover .meta span::before {
  content: "•";
  margin: 0 8px;
  color: #c4c4c4;
}

.cover .meta span:first-child::before {
  content: "";
  margin: 0;
}

h2 {
  font-size: 13pt;
  font-weight: 700;
  color: #0d0d0d;
  margin: 18px 0 6px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid #ececec;
  letter-spacing: -0.005em;
  page-break-after: avoid;
}

h3 {
  font-size: 10.5pt;
  font-weight: 600;
  color: #1a1a1a;
  margin: 12px 0 4px 0;
  page-break-after: avoid;
}

p { margin: 0 0 7px 0; }

ul, ol {
  margin: 4px 0 8px 0;
  padding-left: 18px;
}

li { margin-bottom: 3px; }
li > p { margin: 0 0 3px 0; }

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
  font-size: 8.5pt;
  background: #f5f5f5;
  padding: 1px 4px;
  border-radius: 3px;
  color: #b3284a;
}

pre {
  background: #f8f8f8;
  border: 1px solid #ececec;
  border-left: 3px solid #1f4dd8;
  border-radius: 4px;
  padding: 10px 12px;
  font-family: "JetBrains Mono", "SF Mono", "Menlo", monospace;
  font-size: 7.8pt;
  line-height: 1.45;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  page-break-inside: avoid;
  margin: 8px 0 12px 0;
}

pre code {
  background: transparent;
  padding: 0;
  border-radius: 0;
  color: #1a1a1a;
  font-size: inherit;
}

blockquote {
  border-left: 4px solid #b8344e;
  background: #fdf3f5;
  margin: 10px 0 14px 0;
  padding: 8px 14px;
  color: #2a2a2a;
  border-radius: 0 4px 4px 0;
  font-size: 10pt;
  page-break-inside: avoid;
}

blockquote p { margin: 0; }

table {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0 14px 0;
  font-size: 8.8pt;
  page-break-inside: auto;
}

table thead {
  display: table-header-group;
}

table th {
  text-align: left;
  background: #f4f4f4;
  border-bottom: 1.5px solid #d4d4d4;
  padding: 6px 8px;
  font-weight: 600;
  color: #0d0d0d;
  vertical-align: top;
}

table td {
  border-bottom: 1px solid #ececec;
  padding: 6px 8px;
  vertical-align: top;
}

table tr:nth-child(even) td {
  background: #fafafa;
}

hr {
  border: 0;
  border-top: 1px solid #e5e5e5;
  margin: 18px 0;
}

p, li {
  orphans: 2;
  widows: 2;
}

/* Tighten the architecture map block */
pre + p { margin-top: 0; }
"""

cover = """
<div class="cover">
  <div class="eyebrow">Internal · Team Cheat Sheet · Do Not Share</div>
  <h1 class="title">Smadex Cooking</h1>
  <p class="subtitle">What shipped, what didn't, what we'd defend, what we'd admit. Read end to end before every demo run.</p>
  <div class="meta">
    <span>Aditya · demo lead (A3 + A4)</span>
    <span>Krish · math/ML Q&amp;A</span>
    <span>Andrew · deep tech</span>
  </div>
</div>
"""

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Smadex Cooking — Team Cheat Sheet</title>
</head>
<body>
{cover}
{html_body}
</body>
</html>
"""

out = HERE / "cheatsheet.pdf"
HTML(string=full_html, base_url=str(HERE)).write_pdf(
    str(out),
    stylesheets=[CSS(string=css)],
)
print(f"wrote {out}")
