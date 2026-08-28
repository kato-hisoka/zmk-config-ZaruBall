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
    "&kp BACKSLASH": "\\",
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
    "&mo 2": "Lower",
    "&mo 3": "Raise",
    "&mo SCROLL": "Scroll",
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
  <li><b>トラックボール</b>: 通常ポインタ。Lower / Scroll 層でスクロール。移動量で一時的に Mouse 層（AML）</li>
  <li><b>Scroll</b>: Mouse 層の Scroll キー押し続けで有効。キーは透過、ボールはスクロール</li>
  <li><b>Combo</b>: キー位置 56+61（Lower + KP Enter）→ macro「skater」+ Enter</li>
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


COLORS = {
    "": ((250, 250, 250), (187, 187, 187), (26, 26, 26)),
    "trans": ((243, 243, 243), (200, 200, 200), (187, 187, 187)),
    "none": ((236, 236, 236), (210, 210, 210), (204, 204, 204)),
    "layer": ((255, 232, 214), (196, 92, 38), (90, 40, 10)),
    "mouse": ((227, 242, 253), (25, 118, 210), (13, 71, 161)),
    "sys": ((243, 229, 245), (123, 31, 162), (74, 20, 140)),
    "mod": ((232, 245, 233), (56, 142, 60), (27, 94, 32)),
    "ime": ((255, 248, 225), (249, 168, 37), (121, 85, 0)),
}


def _load_font(size: int) -> "ImageFont.FreeTypeFont | ImageFont.ImageFont":
    from PIL import ImageFont

    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size, index=0)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_rounded_rect(draw, xy, radius, fill, outline, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def render_layer_image(layout: list[dict], layer_name: str, bindings: list[str], scale: int = 56):
    from PIL import Image, ImageDraw

    pad = 24
    max_x = max(k["x"] + k.get("w", 1) for k in layout)
    max_y = max(k["y"] + 1.1 for k in layout)
    width = int(max_x * scale + pad * 2)
    height = int(max_y * scale + pad * 2 + 36)

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    title_font = _load_font(22)
    key_font = _load_font(13)
    small_font = _load_font(9)

    draw.text((pad, 6), layer_name, fill=(26, 26, 26), font=title_font)
    draw.rectangle((pad, 32, pad + 6, 48), fill=(196, 92, 38))

    for i, k in enumerate(layout):
        binding = bindings[i]
        lab = label_for(binding)
        cls = key_class(lab, binding)
        fill, outline, text_color = COLORS.get(cls, COLORS[""])
        w = k.get("w", 1)
        x = pad + k["x"] * scale
        y = pad + 36 + k["y"] * scale
        kw = w * scale - 4
        kh = scale - 4
        r = k.get("r", 0)

        key_img = Image.new("RGBA", (int(kw) + 4, int(kh) + 4), (0, 0, 0, 0))
        key_draw = ImageDraw.Draw(key_img)
        _draw_rounded_rect(
            key_draw,
            (1, 1, kw, kh),
            radius=6,
            fill=fill + ((255,) if isinstance(fill, tuple) else ()),
            outline=outline,
            width=1 if cls != "trans" else 1,
        )
        if cls == "trans":
            # dashed look via lighter outline already
            pass

        lines = lab.split("\n")
        font = small_font if len(lines) > 1 or len(lab) > 6 else key_font
        total_h = sum(
            (font.getbbox(line)[3] - font.getbbox(line)[1]) + 1 for line in lines
        )
        ty = (kh - total_h) / 2 + 1
        for line in lines:
            bbox = font.getbbox(line)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            key_draw.text(((kw - lw) / 2 + 1, ty), line, fill=text_color, font=font)
            ty += lh + 1

        if r:
            key_img = key_img.rotate(-r, expand=True, resample=Image.Resampling.BICUBIC)
            ox = int(x + kw / 2 - key_img.width / 2)
            oy = int(y + kh / 2 - key_img.height / 2)
            img.paste(key_img, (ox, oy), key_img)
        else:
            img.paste(key_img, (int(x), int(y)), key_img)

    return img


def build_pdf(layout: list[dict], layers: list[tuple[str, list[str]]], pdf_path: Path) -> None:
    from PIL import Image, ImageDraw

    # A4 landscape at 150 DPI
    page_w, page_h = 1754, 1240
    margin = 36
    notes = [
        "td0_sft（左親指）: タップ=英数 / ホールド=Alt / ダブル=Raise / トリプル=Mouse。Shift押し中は td1",
        "td1（右親指）: タップ=かな / ホールド=Ctrl / ダブル=Raise / トリプル=Mouse",
        "Adjust: Lower + Raise 同時押し（tri-layer）  /  Scroll: Mouse層のScrollキー押し続け",
        "トラックボール: 通常ポインタ。Lower/Scrollでスクロール。移動量で一時Mouse(AML)",
        "Combo: キー位置 56+61（Lower + KP Enter）→ macro「skater」+ Enter",
    ]

    layer_imgs = [
        (name, render_layer_image(layout, name, bindings)) for name, bindings in layers
    ]

    pages: list[Image.Image] = []

    # Page 1: title + notes + first 2 layers
    page = Image.new("RGB", (page_w, page_h), (255, 255, 255))
    draw = ImageDraw.Draw(page)
    title_font = _load_font(32)
    body_font = _load_font(16)
    small_font = _load_font(13)
    draw.text((margin, 24), "ZaruBall Keymap Cheatsheet", fill=(26, 26, 26), font=title_font)
    draw.text(
        (page_w - margin - 280, 36),
        "config/ZaruBall.keymap",
        fill=(100, 100, 100),
        font=small_font,
    )
    draw.line((margin, 70, page_w - margin, 70), fill=(34, 34, 34), width=2)

    y = 86
    draw.rounded_rectangle(
        (margin, y, page_w - margin, y + 110),
        radius=8,
        fill=(250, 248, 245),
        outline=(221, 221, 221),
    )
    ty = y + 10
    for line in notes:
        draw.text((margin + 14, ty), "• " + line, fill=(40, 40, 40), font=small_font)
        ty += 18

    y = y + 126
    # legend
    legend = [
        ("Layer / TapDance", COLORS["layer"][0]),
        ("Mouse", COLORS["mouse"][0]),
        ("Modifier", COLORS["mod"][0]),
        ("IME", COLORS["ime"][0]),
        ("System / BT", COLORS["sys"][0]),
        ("Transparent", COLORS["trans"][0]),
    ]
    lx = margin
    for text, color in legend:
        draw.rectangle((lx, y, lx + 14, y + 14), fill=color, outline=(153, 153, 153))
        draw.text((lx + 18, y - 1), text, fill=(60, 60, 60), font=small_font)
        lx += 14 + 8 + small_font.getbbox(text)[2] + 18

    y += 28
    for name, limg in layer_imgs[:2]:
        # scale to fit width
        max_w = page_w - 2 * margin
        if limg.width > max_w:
            ratio = max_w / limg.width
            limg = limg.resize(
                (int(limg.width * ratio), int(limg.height * ratio)),
                Image.Resampling.LANCZOS,
            )
        page.paste(limg, (margin, y))
        y += limg.height + 12
    pages.append(page)

    # Remaining layers, 2 per page
    rest = layer_imgs[2:]
    for i in range(0, len(rest), 2):
        page = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        y = margin
        for name, limg in rest[i : i + 2]:
            max_w = page_w - 2 * margin
            if limg.width > max_w:
                ratio = max_w / limg.width
                limg = limg.resize(
                    (int(limg.width * ratio), int(limg.height * ratio)),
                    Image.Resampling.LANCZOS,
                )
            page.paste(limg, (margin, y))
            y += limg.height + 16
        pages.append(page)

    pages[0].save(
        pdf_path,
        "PDF",
        resolution=150.0,
        save_all=True,
        append_images=pages[1:],
    )


def to_pdf_chrome(html_path: Path, pdf_path: Path) -> bool:
    if not CHROME.exists():
        return False
    try:
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
            timeout=60,
        )
        return pdf_path.exists() and pdf_path.stat().st_size > 1000
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False


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

    if not to_pdf_chrome(OUT_HTML, OUT_PDF):
        build_pdf(layout, layers, OUT_PDF)
    if OUT_PDF.exists():
        print(f"Wrote {OUT_PDF} ({OUT_PDF.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
