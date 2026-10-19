"""Render a palette to a preview PNG: mock bar, mock terminal, swatches, wallpapers."""
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .core.color import mix
from .core.contrast import report
from .core.palette import ANSI

W, H = 1280, 760


def _kitty_font():
    """The font_family set in kitty.conf, if any, so the preview looks like the user's terminal."""
    conf = Path.home() / ".config/kitty/kitty.conf"
    try:
        for line in conf.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and parts[0] == "font_family" and parts[1] != "monospace":
                return parts[1].strip().strip('"')
    except OSError:
        pass
    return None


def _font(size, bold=False):
    """A real monospace font: kitty's own first, then common ones, then any installed."""
    if shutil.which("fc-match"):
        weight = "bold" if bold else "regular"
        favourites = [_kitty_font(), "JetBrains Mono", "JetBrainsMono Nerd Font", "DejaVu Sans Mono",
                      "Fira Code", "Hack", "Adwaita Mono", "Noto Sans Mono", "Liberation Mono", "monospace"]
        for family in filter(None, favourites):
            try:
                res = subprocess.run(["fc-match", "-f", "%{family}|%{spacing}|%{file}", f"{family}:{weight}"],
                                     capture_output=True, text=True, timeout=3).stdout
                got, spacing, path = (res.split("|", 2) + ["", ""])[:3]
                # Only fonts fontconfig marks as monospace (spacing 100); .ttc bundles can
                # hold a proportional font first, so they are skipped
                if spacing == "100" and path.endswith((".ttf", ".otf")):
                    return ImageFont.truetype(path, size)
            except (OSError, subprocess.SubprocessError):
                pass
        try:  # any installed monospace font
            res = subprocess.run(["fc-list", ":spacing=100", "file"], capture_output=True, text=True, timeout=3).stdout
            for line in sorted(res.splitlines()):
                path = line.split(":")[0].strip()
                if path.endswith((".ttf", ".otf")):
                    return ImageFont.truetype(path, size)
        except (OSError, subprocess.SubprocessError):
            pass
    import os, sys
    if sys.platform == "win32":   # Windows' own monospace fonts
        fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for name in (("CascadiaMono-Bold.ttf", "consolab.ttf") if bold else ("CascadiaMono.ttf", "consola.ttf")):
            if (fonts / name).exists():
                return ImageFont.truetype(str(fonts / name), size)
    return ImageFont.load_default(size=size)


def _rounded(d, box, r, fill, outline=None, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def render(p, out, images=(), cfg=None):
    f = _font(15)
    fb = _font(15, bold=True)
    small = _font(12)
    big = _font(24, bold=True)

    img = Image.new("RGB", (W, H), p.shadow)
    d = ImageDraw.Draw(img)

    # Background: first wallpaper dimmed, else the surface colour
    if images:
        wp = Image.open(images[0]).convert("RGB")
        scale = max(W / wp.width, H / wp.height)          # cover, like a wallpaper
        wp = wp.resize((round(wp.width * scale), round(wp.height * scale)))
        left, top = (wp.width - W) // 2, (wp.height - H) // 2
        wp = wp.crop((left, top, left + W, top + H))
        img.paste(Image.blend(wp, Image.new("RGB", (W, H), p.shadow), 0.45))
        d = ImageDraw.Draw(img)
    else:
        d.rectangle((0, 0, W, H), fill=mix(p.surface, p.shadow, 0.5))

    # --- mock bar
    _rounded(d, (16, 12, W - 16, 52), 10, p.surface, p.outline)
    x = 30
    for i in range(1, 6):
        active = i == 2
        _rounded(d, (x, 20, x + 30, 44), 7, p.primary if active else p.variant)
        d.text((x + 15, 32), str(i), font=fb, anchor="mm", fill=p.surface if active else p.on_variant)
        x += 38
    d.text((W // 2, 32), "21:47", font=fb, anchor="mm", fill=p.on_surface)
    for i, c in enumerate([p.error, p.tertiary, p.secondary, p.primary]):
        _rounded(d, (W - 60 - i * 34, 22, W - 34 - i * 34, 42), 6, p.variant, c, 2)

    # --- mock terminal window (active border = primary)
    tx, ty, tw, th = 30, 80, 720, 440
    _rounded(d, (tx - 3, ty - 3, tx + tw + 3, ty + th + 3), 12, p.primary)
    _rounded(d, (tx, ty, tx + tw, ty + th), 10, p.surface)
    _rounded(d, (tx, ty, tx + tw, ty + 30), 10, p.variant)
    d.rectangle((tx, ty + 20, tx + tw, ty + 30), fill=p.variant)
    d.text((tx + 14, ty + 15), "kitty", font=f, anchor="lm", fill=p.on_variant)

    n, b = p.normal, p.bright
    lines = [
        [(p.normal[2], "fested"), (p.on_surface, "@"), (p.normal[4], "nerv"), (p.on_surface, " ~/themes "), (p.primary, "> "), (p.on_surface, "ls -la")],
        [(n[4], "drwxr-xr-x "), (p.on_variant, "  4096 "), (n[4], "presets/")],
        [(n[2], "-rwxr-xr-x "), (p.on_variant, "  1287 "), (n[2], "switch.sh")],
        [(p.on_surface, "-rw-r--r-- "), (p.on_variant, "   412 "), (p.on_surface, "kitty.conf")],
        [(n[5], "lrwxrwxrwx "), (p.on_variant, "    18 "), (n[6], "active.lua"), (p.on_variant, " -> "), (n[3], "themes/")],
        [(p.error, "error: "), (p.on_surface, "contrast below 4.5 on "), (n[3], "'dim text'")],
        [(n[1], "warning: "), (p.on_surface, "theme exists, use "), (p.secondary, "--force")],
        [(p.normal[2], "fested"), (p.on_surface, "@"), (p.normal[4], "nerv"), (p.on_surface, " ~/themes "), (p.primary, "> "), (p.on_surface, "█")],
    ]
    y = ty + 48
    for line in lines:
        x = tx + 18
        for colour, text in line:
            d.text((x, y), text, font=f, fill=colour)
            x += d.textlength(text, font=f)
        y += 26
    # the 16 terminal colours, fastfetch style
    y += 14
    for row, colours in enumerate((n, b)):
        for i, c in enumerate(colours):
            d.rectangle((tx + 18 + i * 44, y + row * 34, tx + 56 + i * 44, y + 28 + row * 34), fill=c)
    d.text((tx + 18, y + 76), "  ".join(f"{i}:{name}" for i, name in enumerate(ANSI)), font=small, fill=p.on_variant)

    # --- swatches panel
    sx, sy = 780, 80
    _rounded(d, (sx, sy, W - 30, sy + th), 10, p.surface, p.outline)
    title, width = p.title, W - 30 - sx - 36
    while d.textlength(title, font=big) > width and len(title) > 4:
        title = title[:-2].rstrip() + "…"
    note = p.note
    while d.textlength(note, font=small) > width and len(note) > 4:
        note = note[:-2].rstrip() + "…"
    d.text((sx + 18, sy + 18), title, font=big, fill=p.on_surface)
    d.text((sx + 18, sy + 50), note, font=small, fill=p.on_variant)
    roles = ["primary", "secondary", "tertiary", "error", "surface", "variant",
             "hover", "outline", "shadow", "on_surface", "on_variant"]
    for i, role in enumerate(roles):
        col, row = i % 2, i // 2
        x, y = sx + 18 + col * 232, sy + 82 + row * 52
        _rounded(d, (x, y, x + 40, y + 40), 6, p[role], p.outline)
        d.text((x + 50, y + 4), role, font=fb, fill=p.on_surface)
        d.text((x + 50, y + 22), p[role], font=small, fill=p.on_variant)

    # --- contrast checks
    kw = {"text_min": cfg.text_min, "accent_min": cfg.accent_min} if cfg else {}
    rows = report(p, **kw)
    failed = [r for r in rows if not r[5]]
    cy = ty + th + 24
    _rounded(d, (30, cy, W - 30, cy + 44), 10, p.surface, p.outline)
    if failed:
        msg = "Contrast: " + ", ".join(f"{r[0]} {r[3]:.1f}<{r[4]:g}" for r in failed[:5])
        d.text((48, cy + 22), msg, font=f, anchor="lm", fill=p.error)
    else:
        d.text((48, cy + 22), f"Contrast: all {len(rows)} checks pass", font=f, anchor="lm", fill=p.normal[2])

    # --- wallpaper thumbnails
    y0 = cy + 62
    for i, path in enumerate(images[:2]):
        th_img = Image.open(path).convert("RGB")
        th_img.thumbnail((290, H - y0 - 16))
        x0 = 30 + i * 310
        img.paste(th_img, (x0, y0))
        d.rectangle((x0, y0, x0 + th_img.width, y0 + th_img.height), outline=p.outline)
        d.text((x0 + 8, y0 + 6), f"wp{i + 1}", font=fb, fill="#ffffff")
    if not images:
        d.text((40, y0 + 10), "No wallpaper yet: add --image, or put wp1.png / wp2.png in the theme folder.",
               font=f, fill=p.on_variant)

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return Path(out)


def open_image(path):
    """Open the preview in the user's image viewer, without blocking."""
    import os, sys
    if sys.platform == "win32":
        os.startfile(str(path))   # the default Photos app
        return True
    for cmd in ("xdg-open", "imv", "feh"):
        if shutil.which(cmd):
            subprocess.Popen([cmd, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
            return True
    return False
