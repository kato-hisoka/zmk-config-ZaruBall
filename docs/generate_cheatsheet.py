#!/usr/bin/env python3
"""Generate ZaruBall keymap cheatsheet HTML (and PDF via Chrome)."""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYMAP = ROOT / "config/ZaruBall.keymap"
INFO = ROOT / "config/info.json"
OUT_HTML = ROOT / "docs/keymap-cheatsheet.html"
OUT_PDF = ROOT / "docs/ZaruBall-keymap-cheatsheet.pdf"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

LABELS = {
    "&trans": "▽",
    "&none": "·",
    "&kp ESC": "Esc",
    "&kp TAB": "Tab",
    "&kp LEFT_CONTROL": "Ctrl",
    "&kp LSHFT": "Shift",
    "&kp RIGHT_SHIFT": "Shift",
    "&kp LSHIFT": "Shift",
    "&kp SPACE": "Space",
    "&kp BACKSPACE": "⌫",
    "&kp RET": "Enter",
    "&kp C_MUTE": "Mute",
    "&kp LEFT_ALT": "Alt",
    "&kp LEFT_COMMAND": "⌘",
    "&kp TILDE": "~",
    "&kp MINUS": "-",
    "&kp EQUAL": "=",
    "&kp GRAVE": "`",
    "&kp SEMI": ";",
    "&kp SQT": "'",
    "&kp COMMA": ",",
    "&kp DOT": ".",
    "&kp FSLH": "/",
    "&kp NON_US_BACKSLASH": "¥",
    "&kp NUMBER_6": "6",
    "&kp SINGLE_QUOTE": "'",
    "&kp SEMICOLON": ";",
    "&kp CAPS": "Caps",
    "&kp HOME": "Home",
    "&kp END": "End",
    "&kp PG_UP": "PgUp",
    "&kp PG_DN": "PgDn",
    "&kp LEFT": "←",
    "&kp RIGHT": "→",
    "&kp UP": "↑",
    "&kp DOWN": "↓",
    "&kp LEFT_ARROW": "←",
    "&kp RIGHT_ARROW": "→",
    "&kp DOWN_ARROW": "↓",
    "&kp DEL": "Del",
    "&kp RSHFT": "RSft",
    "&kp LPAR": "(",
    "&kp RPAR": ")",
    "&kp LEFT_PARENTHESIS": "(",
    "&kp RIGHT_PARENTHESIS": ")",
    "&kp LEFT_BRACKET": "[",
    "&kp RIGHT_BRACKET": "]",
    "&kp C_VOL_UP": "Vol+",
    "&kp C_VOL_DN": "Vol-",
    "&kp KP_ENTER": "KP⏎",
    "&kp KP_N0": "KP0",
    "&kp KP_N1": "KP1",
    "&kp KP_N2": "KP2",
    "&kp KP_N3": "KP3",
    "&kp KP_N4": "KP4",
    "&kp KP_N5": "KP5",
    "&kp KP_N6": "KP6",
    "&kp KP_N7": "KP7",
    "&kp KP_N8": "KP8",
    "&kp KP_N9": "KP9",
    "&kp KP_DOT": "KP.",
    "&kp KP_PLUS": "KP+",
    "&kp KP_MINUS": "KP-",
    "&kp KP_MULTIPLY": "KP*",
    "&kp KP_DIVIDE": "KP/",
    "&kp KP_SLASH": "KP/",
    "&kp KP_EQUAL": "KP=",
    "&kp KP_NUMLOCK": "NumLk",
    "&td0_sft": "英数/Alt\n×2 Raise\n×3 Mouse\n⇧=td1",
    "&td1": "かな/Ctrl\n×2 Raise\n×3 Mouse",
    "&td0": "英数/Alt",
    "&mo 3": "Raise",
    "&studio_unlock": "Studio",
    "&ind_bat": "Bat",
    "&ind_con": "BT sts",
    "&out OUT_TOG": "USB/BT",
    "&bt BT_CLR": "BT CLR",
    "&bt BT_CLR_ALL": "CLR ALL",
    "&mkp LCLK": "LCLK",
    "&mkp RCLK": "RCLK",
    "&mkp MCLK": "MCLK",
    "&mkp MB4": "MB4",
    "&mkp MB5": "MB5",
    "&msc SCRL_UP": "Scr↑",
    "&msc SCRL_DOWN": "Scr↓",
    "&msc SCRL_LEFT": "Scr←",
    "&msc SCRL_RIGHT": "Scr→",
    "&msc MOVE_Y(10)": "MoveY",
    "&kp LA(F1)": "⌥F1",
    "&kp LA(F2)": "⌥F2",
}
for i in range(1, 13):
    LABELS[f"&kp F{i}"] = f"F{i}"
for i in range(10):
    LABELS[f"&kp N{i}"] = str(i)
for c in "QWERTYUIOPASDFGHJKLZXCVBNM":
    LABELS[f"&kp {c}"] = c
for i in range(5):
    LABELS[f"&bt BT_SEL {i}"] = f"BT{i}"


def parse_layers(text: str) -> list[tuple[str, list[str]]]:
    layer_re = re.compile(
        r"(\w+_layer)\s*\{[^}]*?display-name\s*=\s*\"([^\"]+)\";"
        r".*?[^-\w]bindings\s*=\s*<([^>]*)>;",
        re.S,
    )
    layers: list[tuple[str, list[str]]] = []
    for m in layer_re.finditer(text):
        name = m.group(2)
        parts = [
            p.strip()
            for p in re.split(r"(?=&)", m.group(3).strip())
            if p.strip().startswith("&")
        ]
        bindings = [" ".join(p.split()) for p in parts]
        layers.append((name, bindings))
    return layers


def label_for(binding: str) -> str:
    b = binding.strip()
    if b in LABELS:
        return LABELS[b]
    m = re.match(r"&to_layer_0\s+(\S+)", b)
    if m:
        key = m.group(1)
        alias = {
            "ESC": "Esc",
            "TAB": "Tab",
            "CAPS": "Caps",
            "LSHIFT": "Shift",
            "MINUS": "-",
            "EQUAL": "=",
            "SINGLE_QUOTE": "'",
            "SEMICOLON": ";",
        }
        if key.startswith("N") and key[1:].isdigit():
            return f"{key[1:]}\n→Base"
        return f"{alias.get(key, key)}\n→Base"
    if b.startswith("&kp "):
        return b[4:]
    return b.replace("&", "")


def key_class(label: str, binding: str) -> str:
    if binding == "&trans":
        return "trans"
    if binding == "&none":
        return "none"
    if binding.startswith("&td") or binding.startswith("&mo") or "Studio" in label:
        return "layer"
    if binding.startswith("&mkp") or binding.startswith("&msc"):
        return "mouse"
    if binding.startswith("&bt") or "OUT_TOG" in binding or binding.startswith("&ind"):
        return "sys"
    if any(x in binding for x in ("SHIFT", "CONTROL", "ALT", "COMMAND", "LSHFT", "RSHFT")):
        return "mod"
    if "英数" in label or "かな" in label:
        return "ime"
    return ""


def build_html(layout: list[dict], layers: list[tuple[str, list[str]]]) -> str:
    notes = """
<ul>
  <li><b>td0_sft</b>（左親指）: タップ=英数 / ホールド=Alt / ダブル=Raise / トリプル=Mouse。Shift押し中は td1（かな/Ctrl）</li>
  <li><b>td1</b>（右親指）: タップ=かな / ホールド=Ctrl / ダブル=Raise / トリプル=Mouse</li>
  <li><b>Adjust</b>: Lower + Raise 同時押し（tri-layer）</li>
  <li><b>トラックボール</b>: 通常ポインタ、Lower(SCROLL) でスクロール。操作で一時的に Mouse 層</li>
  <li><b>Combo</b>: キー位置 56+61 → macro「skater」+ Enter</li>
</ul>
"""
    unit = 52
    pad = 20
    max_x = max(k["x"] + k.get("w", 1) for k in layout)
    max_y = max(k["y"] + 1 for k in layout)
    width = int(max_x * unit + pad * 2)
    height = int(max_y * unit + pad * 2 + 30)

    sections: list[str] = []
    for layer_name, bindings in layers:
        keys_html: list[str] = []
        for i, k in enumerate(layout):
            binding = bindings[i]
            lab = label_for(binding)
            cls = key_class(lab, binding)
            w = k.get("w", 1)
            x = pad + k["x"] * unit
            y = pad + 8 + k["y"] * unit
            r = k.get("r", 0)
            kw = w * unit - 4
            kh = unit - 4
            transform = ""
            if r:
                cx = x + kw / 2
                cy = y + kh / 2
                transform = f"transform: rotate({r}deg); transform-origin: {cx}px {cy}px;"
            lines = lab.split("\n")
            inner = "<br>".join(html.escape(line) for line in lines)
            title = html.escape(binding)
            font_class = "small" if len(lines) > 1 or len(lab) > 6 else ""
            keys_html.append(
                f'<div class="key {cls} {font_class}" '
                f'style="left:{x}px;top:{y}px;width:{kw}px;height:{kh}px;{transform}" '
                f'title="{title}"><span>{inner}</span></div>'
            )
        sections.append(
            f"""
    <section class="layer">
      <h2>{html.escape(layer_name)}</h2>
      <div class="board" style="width:{width}px;height:{height}px">
        {"".join(keys_html)}
      </div>
    </section>
"""
        )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>ZaruBall Keymap Cheatsheet</title>
<style>
  @page {{ size: A4 landscape; margin: 8mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP",
      "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a;
    background: #fff;
    margin: 0;
    padding: 12px 16px;
  }}
  header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 2px solid #222;
    margin-bottom: 10px;
    padding-bottom: 4px;
  }}
  h1 {{ font-size: 20px; margin: 0; }}
  .sub {{ font-size: 11px; color: #555; }}
  .notes {{
    font-size: 10.5px;
    background: #faf8f5;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 10px;
  }}
  .notes ul {{ margin: 0; padding-left: 16px; }}
  .notes li {{ margin: 1px 0; }}
  .layer {{
    page-break-inside: avoid;
    break-inside: avoid;
    margin-bottom: 12px;
    background: #fff;
    border: 1px solid #e2e0db;
    border-radius: 8px;
    padding: 6px 8px 8px;
  }}
  h2 {{
    font-size: 13px;
    margin: 0 0 4px 0;
    border-left: 4px solid #c45c26;
    padding-left: 8px;
  }}
  .board {{ position: relative; margin: 0 auto; }}
  .key {{
    position: absolute;
    background: linear-gradient(180deg, #fafafa, #ececec);
    border: 1px solid #bbb;
    border-radius: 5px;
    box-shadow: 0 1px 0 #999;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    line-height: 1.1;
    padding: 1px;
    overflow: hidden;
  }}
  .key.small {{ font-size: 7.5px; font-weight: 500; }}
  .key.trans {{ background: #f3f3f3; color: #bbb; border-style: dashed; box-shadow: none; }}
  .key.none {{ background: #ececec; color: #ccc; box-shadow: none; }}
  .key.layer {{ background: linear-gradient(180deg, #ffe8d6, #ffd0ad); border-color: #c45c26; }}
  .key.mouse {{ background: linear-gradient(180deg, #e3f2fd, #bbdefb); border-color: #1976d2; }}
  .key.sys {{ background: linear-gradient(180deg, #f3e5f5, #e1bee7); border-color: #7b1fa2; }}
  .key.mod {{ background: linear-gradient(180deg, #e8f5e9, #c8e6c9); border-color: #388e3c; }}
  .key.ime {{ background: linear-gradient(180deg, #fff8e1, #ffe082); border-color: #f9a825; }}
  .legend {{
    display: flex; gap: 10px; flex-wrap: wrap; font-size: 10px;
    margin-bottom: 8px;
  }}
  .legend span {{ display: inline-flex; align-items: center; gap: 4px; }}
  .swatch {{
    width: 11px; height: 11px; border-radius: 2px; border: 1px solid #999;
    display: inline-block;
  }}
  footer {{ font-size: 9px; color: #777; text-align: right; margin-top: 4px; }}
</style>
</head>
<body>
  <header>
    <h1>ZaruBall Keymap Cheatsheet</h1>
    <div class="sub">config/ZaruBall.keymap</div>
  </header>
  <div class="legend">
    <span><i class="swatch" style="background:#ffd0ad"></i> Layer / TapDance</span>
    <span><i class="swatch" style="background:#bbdefb"></i> Mouse</span>
    <span><i class="swatch" style="background:#c8e6c9"></i> Modifier</span>
    <span><i class="swatch" style="background:#ffe082"></i> IME</span>
    <span><i class="swatch" style="background:#e1bee7"></i> System / BT</span>
    <span><i class="swatch" style="background:#f3f3f3;border-style:dashed"></i> Transparent</span>
  </div>
  <div class="notes">{notes}</div>
  {"".join(sections)}
  <footer>Generated from ZaruBall.keymap · A4 landscape</footer>
</body>
</html>
"""


def to_pdf(html_path: Path, pdf_path: Path) -> None:
    if not CHROME.exists():
        print(f"Chrome not found at {CHROME}; skip PDF", file=sys.stderr)
        return
    subprocess.run(
        [
            str(CHROME),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
    )


def main() -> None:
    info = json.loads(INFO.read_text())
    layout = info["layouts"]["default_transform"]["layout"]
    layers = parse_layers(KEYMAP.read_text())
    for name, bindings in layers:
        if len(bindings) != len(layout):
            raise SystemExit(
                f"{name}: {len(bindings)} bindings vs {len(layout)} layout keys"
            )
    OUT_HTML.write_text(build_html(layout, layers), encoding="utf-8")
    print(f"Wrote {OUT_HTML}")
    to_pdf(OUT_HTML, OUT_PDF)
    if OUT_PDF.exists():
        print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
