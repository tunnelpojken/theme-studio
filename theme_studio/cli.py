"""theme-studio command line.

  theme-studio list
  theme-studio preview --image wp1.png [wp2.png] [--name neon-city]
  theme-studio make    --image wp1.png [wp2.png] [--name neon-city]
  theme-studio make    --preset nord
  theme-studio make    --all-presets            (what make-themes.py used to do)
  theme-studio check   rei-ayanami | --preset nord | --palette file.json
  theme-studio remove  neon-city
  theme-studio make    --prompt "Blade Runner, orange haze and teal"
  theme-studio make    --image wp.png --prompt "but colder"     (wallpaper colours + idea)
  theme-studio apply   neon-city            switch to a theme (runs your switch.sh if you have one)
  theme-studio unhook                       undo every change apply made to your configs
  theme-studio backend                      test the Ollama / API connection
  theme-studio init                         write a starter config.toml
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

from . import targets as targets_mod
from .core import config as config_mod
from .core.contrast import fix, report
from .core.lightmode import to_light
from .core.safewrite import Session
from .sources import llm
from .targets.base import Action
import subprocess
from .core.palette import Palette, camel, slugify
from .preview import open_image, render
from .sources.extract import extract
from .sources.rules import build

PRESETS = Path(__file__).resolve().parent / "presets"
MANIFEST = ".theme-studio.json"


# ---------------------------------------------------------------- helpers

def user_presets():
    return config_mod.platform.config_dir() / "presets"


def preset_files():
    found = {}
    for folder in (PRESETS, user_presets()):   # user presets override bundled ones
        if folder.is_dir():
            for f in sorted(folder.glob("*.json")):
                found[f.stem] = f
    return found


def load_preset(name):
    files = preset_files()
    if name not in files:
        sys.exit(f"No preset called '{name}'. Run 'theme-studio list' to see them.")
    return Palette.load(files[name])


def ask(question, assume_yes):
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print(f"{question} -> not a terminal, so not doing it. Add --yes to skip this question.")
        return False
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def light(args):
    """--light, or a directive that asks for one ("light theme", "light mode")."""
    prompt = (getattr(args, "prompt", None) or "").lower()
    return bool(getattr(args, "light", False)) or bool(re.search(r"\blight (theme|mode)\b", prompt))


def lighten(p, args):
    """Light version; without --name it gets its own name, so the dark one isn't overwritten."""
    from dataclasses import replace
    p = to_light(p)
    if not args.name and not p.name.endswith("-light"):
        p = replace(p, name=p.name + "-light", title=p.title + " Light", palette=p.palette + "Light")
    return p


def palette_from_args(args, cfg):
    """Build the palette from --preset, --palette, --image and/or --prompt. Returns (palette, images, notes)."""
    notes = []
    prompt = getattr(args, "prompt", None)
    if prompt and (getattr(args, "preset", None) or getattr(args, "palette", None)):
        sys.exit("--prompt works on its own or with --image, not with --preset/--palette.")
    if getattr(args, "preset", None):
        p = load_preset(args.preset)
        if args.name:
            p = Palette.from_dict({**p.__dict__, "name": args.name})
        images = []
        if light(args):
            p = lighten(p, args)
        if args.fix or light(args):
            p, changes = fix(p, text_min=cfg.text_min, accent_min=cfg.accent_min)
            notes += changes
        return p, images, notes
    if getattr(args, "palette", None):
        p = Palette.load(args.palette)
        return p, list(args.image or []), notes
    if getattr(args, "image", None):
        images = [Path(i).expanduser() for i in args.image]
        for i in images:
            if not i.is_file():
                sys.exit(f"Image not found: {i}")
        name = args.name or short_name(images[0].stem)
        if args.accent and not re.match(r"^#[0-9a-fA-F]{6}$", args.accent):
            sys.exit(f"--accent must look like #ff8a3d, got {args.accent!r}")
        colours = extract(images)
        if args.ai:   # opt-in: the model assigns roles from the wallpaper's colours
            p = model_palette(cfg, name, prompt, colours, args)
        else:
            p = build(colours, name, title=args.title, accent=args.accent,
                      note=f"Generated from {', '.join(i.name for i in images)}")
            if prompt:   # colours named in the directive steer the accents, no model needed
                from .core.colornames import honour
                picks, named = honour({r: p[r] for r in ("primary", "secondary", "tertiary")}, prompt)
                for n in named:
                    print(f"  colour fix: {n}")
                p = Palette.from_dict({**p.__dict__, **picks})
        if light(args):
            p = lighten(p, args)
        if not args.no_fix:
            p, changes = fix(p, text_min=cfg.text_min, accent_min=cfg.accent_min)
            notes += changes
        return p, images, notes
    if prompt:
        name = args.name or slugify(prompt)[:32].strip("-")
        p = model_palette(cfg, name, prompt, None, args)
        if light(args):
            p = lighten(p, args)
        if not args.no_fix:
            p, changes = fix(p, text_min=cfg.text_min, accent_min=cfg.accent_min)
            notes += changes
        return p, [], notes
    sys.exit("Give one of --image, --prompt, --preset or --palette.")


def short_name(stem, words=3):
    """'geralt-of-rivia-pure-arts-the-witcher-3-...' -> 'geralt-of-rivia'."""
    parts = [w for w in slugify(stem).split("-") if w]
    return "-".join(parts[:words]) or "theme"


def model_palette(cfg, name, prompt, hints, args):
    try:
        p = llm.generate(cfg.backend, name, prompt=prompt, hints=hints)
    except llm.BackendError as e:
        sys.exit(f"Model error: {e}")
    if not hints:   # image-based MAGI picks from the wallpaper's own colours: nothing to tidy
        from .core.colornames import apply as apply_words, wants_black
        from .core.tidy import tidy
        _, _, locked = apply_words({r: p[r] for r in ("primary", "secondary", "tertiary")}, prompt or "")
        p, tidied = tidy(p, tint_ok=not wants_black(prompt), locked=locked)
        for t in tidied:
            print(f"  tidy: {t}")
    over = {}
    if not args.name:   # name the theme after the model's title, e.g. "blade-runner"
        slug = slugify(p.title)[:40].strip("-") or name
        over.update(name=slug, palette=camel(slug))
    if args.title:
        over["title"] = args.title
    if args.accent:
        over["primary"] = args.accent.lower()
    return Palette.from_dict({**p.__dict__, **over}) if over else p


def plan_for(p, cfg, selected, images):
    folder = cfg.themes / p.name
    plan = {}
    for t in selected:
        plan.update(t.plan(p, cfg, folder))
    plan[folder / "palette.json"] = p.to_json()
    return folder, plan


def show_fixes(notes):
    for role, before, after in notes:
        print(f"  contrast fix: {role} {before} -> {after}")


# ---------------------------------------------------------------- commands

def cmd_list(args, cfg):
    print("Presets:")
    for name, f in preset_files().items():
        p = Palette.load(f)
        print(f"  {name:<20} {p.note}")
    print(f"\nInstalled themes in {cfg.themes}:")
    current = (cfg.themes / ".current").read_text(encoding="utf-8").strip() if (cfg.themes / ".current").exists() else None
    if cfg.themes.is_dir():
        presets = preset_files()
        for d in sorted(x for x in cfg.themes.iterdir() if x.is_dir() and not x.name.startswith(".")):
            mark = "*" if d.name == current else " "
            if (d / MANIFEST).exists():
                made = "theme-studio"
            elif d.name in presets:
                made = "make-themes.py (matches preset)"
            else:
                made = "hand-made"
            print(f" {mark} {d.name:<20} {made}")
    found = [t.name for t in targets_mod.select("auto")]
    print(f"\nDetected targets: {', '.join(found) or 'none'}")


def cmd_preview(args, cfg):
    p, images, notes = palette_from_args(args, cfg)
    show_fixes(notes)
    out = render(p, cfg.cache / f"{p.name}.png", images, cfg)
    print(f"Preview: {out}")
    if not args.no_open and not open_image(out):
        print("(no image viewer found, open the file above yourself)")


def load_theme(cfg, name):
    """The Palette of a theme in the themes folder.

    Themes Theme Studio made have palette.json. Hand-made ones (from before it, like
    rei-ayanami) don't, but their Noctalia palette JSON holds every role and all 16
    terminal colours, so the palette is rebuilt from that. Raises ValueError if neither exists."""
    folder = cfg.themes / name
    pj = folder / "palette.json"
    if pj.exists():
        return Palette.load(pj)
    toml = folder / "noctalia.toml"
    m = re.search(r'custom_palette\s*=\s*"([^"]+)"', toml.read_text(encoding="utf-8")) if toml.exists() else None
    src = cfg.noctalia_palettes / f"{m.group(1)}.json" if m else None
    if not src or not src.exists():
        raise ValueError(f"'{name}' has no palette.json and no Noctalia palette to read its colours from")
    data = json.loads(src.read_text(encoding="utf-8"))
    d, term = data["dark"], data["dark"]["terminal"]
    from .core.palette import ANSI
    return Palette(
        name=name, title=name.replace("-", " ").title(), palette=m.group(1),
        note=f"Imported from the Noctalia palette {m.group(1)}",
        primary=d["mPrimary"], secondary=d["mSecondary"], tertiary=d["mTertiary"], error=d["mError"],
        surface=d["mSurface"], variant=d["mSurfaceVariant"], hover=d["mHover"], outline=d["mOutline"],
        shadow=d["mShadow"], on_surface=d["mOnSurface"], on_variant=d["mOnSurfaceVariant"],
        normal=[term["normal"][c] for c in ANSI], bright=[term["bright"][c] for c in ANSI], dark=True)


def write_theme(p, cfg, selected, images, force, plan=None):
    folder, plan = plan if plan else plan_for(p, cfg, selected, images)
    written = []
    for path, text in plan.items():
        if path.exists() and not force:
            print(f"  skip (exists): {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)
        print(f"  wrote: {path}")
    # Wallpapers: wp1 = main monitor, wp2 = second (reuses wp1 if only one image)
    if images:
        new_wp1 = False
        for target, src in (("wp1.png", images[0]), ("wp2.png", images[min(1, len(images) - 1)])):
            dest = folder / target
            if dest.exists() and Path(src).resolve() == dest.resolve():
                continue   # an opened theme's own wallpaper: already in place
            if dest.exists() and not force:
                print(f"  skip (exists): {dest}")
                continue
            Image.open(src).save(dest, "PNG")
            written.append(dest)
            print(f"  wrote: {dest}")
            new_wp1 = new_wp1 or target == "wp1.png"
        dest = folder / "preview.png"
        if new_wp1 or not dest.exists():
            shutil.copyfile(folder / "wp1.png", dest)
            written.append(dest)
            print(f"  wrote: {dest}")
    # Manifest, so 'remove' knows exactly what this tool created
    manifest = folder / MANIFEST
    old = json.loads(manifest.read_text(encoding="utf-8")).get("files", []) if manifest.exists() else []
    files = sorted(set(old) | {str(w) for w in written})
    if files:
        manifest.write_text(json.dumps({"name": p.name, "files": files}, indent=2) + "\n", encoding="utf-8")
    missing = [f for f in ("wp1.png", "wp2.png", "preview.png") if not (folder / f).exists()]
    if missing:
        print(f"  still needs: {', '.join(missing)}")
    return written


def cmd_make(args, cfg):
    selected = targets_mod.select(args.targets or cfg.targets)
    if not selected:
        sys.exit("No targets detected. Pass --targets hyprland,kitty,noctalia (or 'all').")
    print(f"Targets: {', '.join(t.name for t in selected)}")

    if args.all_presets:
        palettes = [Palette.load(f) for f in preset_files().values()]
        print(f"{len(palettes)} presets -> {cfg.themes} (existing files are skipped unless --force)")
        if not ask("Write them?", args.yes):
            print("Nothing written.")
            return
        for p in palettes:
            print(f"{p.title}  ->  {cfg.themes / p.name}")
            write_theme(p, cfg, selected, [], args.force)
        return

    p, images, notes = palette_from_args(args, cfg)
    show_fixes(notes)
    folder, plan = plan_for(p, cfg, selected, images)
    exists = folder.exists() and any(folder.iterdir())
    if exists and not args.force:
        sys.exit(f"Theme '{p.name}' already exists in {folder}. Pick another --name, or use --force.")

    if not args.yes or args.preview:
        out = render(p, cfg.cache / f"{p.name}.png", images, cfg)
        print(f"Preview: {out}")
        if not args.no_open:
            open_image(out)

    print("\nWill write:")
    for path in list(plan) + ([folder / "wp1.png", folder / "wp2.png", folder / "preview.png"] if images else []):
        print(f"  {'overwrite' if path.exists() else 'new':<9} {path}")
    if not ask(f"\nCreate this theme ({p.name})?", args.yes):
        print("Nothing written.")
        return
    write_theme(p, cfg, selected, images, args.force, (folder, plan))
    if args.apply:
        print()
        apply_theme(p.name, cfg, selected, args.yes)
    else:
        print(f"\nDone. Switch to it with: theme-studio apply {p.name}")


def cmd_check(args, cfg):
    if args.preset:
        p = load_preset(args.preset)
    elif args.palette:
        p = Palette.load(args.palette)
    elif args.name:
        f = cfg.themes / args.name / "palette.json"
        if f.exists():
            p = Palette.load(f)
        elif args.name in preset_files():
            p = load_preset(args.name)
        else:
            sys.exit(f"'{args.name}' has no palette.json (hand-made themes can't be checked yet).")
    else:
        sys.exit("Give a theme name, --preset or --palette.")
    rows = report(p, text_min=cfg.text_min, accent_min=cfg.accent_min)
    print(f"{p.title}")
    for label, fg, bg, ratio, minimum, ok in rows:
        print(f"  {'ok  ' if ok else 'LOW '} {label:<18} {fg:>11} on {bg:<8} {ratio:5.2f}  (min {minimum:g})")
    bad = sum(not r[5] for r in rows)
    print(f"\n{len(rows) - bad}/{len(rows)} pass" + (". 'make --fix' adjusts the low ones." if bad else ""))
    sys.exit(1 if bad else 0)


def cmd_remove(args, cfg):
    folder = cfg.themes / args.name
    if not folder.is_dir():
        sys.exit(f"No theme '{args.name}' in {cfg.themes}")
    current = cfg.themes / ".current"
    if current.exists() and current.read_text(encoding="utf-8").strip() == args.name:
        sys.exit(f"'{args.name}' is the active theme. Switch to another one first.")
    manifest = folder / MANIFEST
    extra = []
    if manifest.exists():
        # Files this tool wrote outside the theme folder (e.g. the Noctalia palette JSON)
        extra = [Path(f) for f in json.loads(manifest.read_text(encoding="utf-8"))["files"]
                 if not Path(f).is_relative_to(folder) and Path(f).exists()]
    else:
        print(f"Warning: '{args.name}' was not made by theme-studio.")
    print("Will delete:")
    print(f"  {folder}/  ({sum(1 for _ in folder.rglob('*'))} files)")
    for f in extra:
        print(f"  {f}")
    if not ask(f"Remove theme '{args.name}'?", args.yes):
        print("Nothing removed.")
        return
    shutil.rmtree(folder)
    for f in extra:
        f.unlink()
    print("Removed.")


def apply_actions(name, cfg, selected):
    """(actions, session) that would make theme `name` active. Raises SystemExit with a reason."""
    folder = cfg.themes / name
    if not folder.is_dir():
        sys.exit(f"No theme '{name}' in {cfg.themes}")
    s = Session(cfg.data)
    actions = []
    handled = set()
    if cfg.apply_command:
        cmd = cfg.apply_command.replace("{name}", name)
        handled = set(cfg.command_handles)
        actions.append(Action(f"run your switcher: {cmd}",
                              lambda: subprocess.run(os.path.expanduser(cmd), shell=True, check=False)))
    rest = [t for t in selected if t.name not in handled]
    if rest:
        pj = folder / "palette.json"
        if not pj.exists():
            sys.exit(f"'{name}' has no palette.json, so only your switcher can apply it "
                     f"(targets left: {', '.join(t.name for t in rest)}).")
        p = Palette.load(pj)
        for t in rest:
            for path, text in t.plan(p, cfg, folder).items():   # fill in files made before this target existed
                if not path.exists():
                    actions.append(Action(f"write missing {path.name}", lambda path=path, text=text: path.write_text(text, encoding="utf-8")))
            actions += t.apply(p, cfg, folder, s)
    if not cfg.apply_command:
        actions.append(Action(f"remember {name} as the active theme",
                              lambda: (cfg.themes / ".current").write_text(name + "\n", encoding="utf-8")))
    return actions, s


def run_actions(actions, s, cfg):
    failed = 0
    for a in actions:
        try:
            a.run()
        except Exception as e:  # keep going: one app failing shouldn't block the rest
            failed += 1
            print(f"  failed: {a.describe}: {e}")
    s.save()
    print("Done." if not failed else f"Done, with {failed} failure(s).")
    if s.backed_up:
        print(f"Backups: {cfg.data / 'backups' / s.stamp}")
    return failed


def apply_theme(name, cfg, selected, yes):
    actions, s = apply_actions(name, cfg, selected)
    if not actions:
        print("Nothing to do: no targets selected.")
        return
    print(f"Applying '{name}':")
    for a in actions:
        print(f"  {'*' if a.touches_user_file else '-'} {a.describe}")
    if any(a.touches_user_file for a in actions):
        print("  (* changes one of your own config files; a backup is made first, 'theme-studio unhook' undoes it)")
    if not ask("Go ahead?", yes):
        print("Nothing changed.")
        return
    run_actions(actions, s, cfg)


def cmd_apply(args, cfg):
    selected = targets_mod.select(args.targets or cfg.targets)
    apply_theme(args.name, cfg, selected, args.yes)


def unhook_plan(s):
    """What unhook will undo, one line each (shared by the CLI and the window)."""
    lines = [f"remove line '{h['line']}' from {h['file']}" for h in s.state["hooks"]]
    lines += [f"delete {f}" for f in s.state["owned"] if Path(f).exists()]
    lines += [f"restore {e['key']}={e['old'] if e['old'] is not None else '(unset)'} in {e['file']}"
              for e in s.state["ini"]]
    lines += [f"restore registry value {e['key']}\\{e['name']}" for e in s.state.get("reg", [])]
    lines += [f"switch back to your {e['what']}" for e in s.state["restore"]]
    return lines


def unhook_run(s):
    """Undo everything apply changed. Returns the backup folder, or None if nothing was backed up."""
    from .targets.konsole import set_ini_key
    # Order matters: apps like Hyprland reload the moment a config file changes.
    # 1. lines and settings in the user's own files (nothing points at our files any more)
    s.unhook(set_ini_key, run_restore=False)
    # 2. then Theme Studio's own files
    for f in [Path(f) for f in s.state["owned"] if Path(f).exists()]:
        f.unlink()
    # 3. then live settings and reloads, against the finished state
    s.run_restore()
    s.state["owned"] = []
    s.save()
    return s.data / "backups" / s.stamp if s.backed_up else None


def cmd_unhook(args, cfg):
    s = Session(cfg.data)
    lines = unhook_plan(s)
    if not lines:
        print("Nothing to undo: theme-studio hasn't changed any of your configs.")
        return
    print("Will undo:")
    for line in lines:
        print(f"  {line}")
    if not ask("Undo all of this?", args.yes):
        print("Nothing changed.")
        return
    backups = unhook_run(s)
    print("Done. Your configs are back to how they were.")
    if backups:
        print(f"Backups: {backups}")


def cmd_backend(args, cfg):
    b = cfg.backend
    print(f"kind={b.kind}  url={b.url}  model={b.model}" + (f"  key from ${b.api_key_env}" if b.api_key_env else ""))
    try:
        print(llm.test(b))
    except llm.BackendError as e:
        sys.exit(f"Not working: {e}")


def cmd_init(args, cfg):
    path = config_mod.config_path()
    if path.exists() and not args.force:
        sys.exit(f"{path} already exists (use --force to overwrite).")
    text = config_mod.example(cfg)
    print(text)
    if ask(f"Write this to {path}?", args.yes):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print("Written.")


# ---------------------------------------------------------------- argparse

def main(argv=None):
    config_mod.platform.utf8_console()
    ap = argparse.ArgumentParser(prog="theme-studio", description="Make desktop themes from images or presets.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list presets, installed themes and detected targets")

    def inputs(sp):
        src = sp.add_mutually_exclusive_group()
        src.add_argument("--image", nargs="+", metavar="IMG", help="wallpaper(s): first = main monitor")
        src.add_argument("--preset", help="a bundled preset, see 'list'")
        src.add_argument("--palette", help="a palette.json file")
        sp.add_argument("--prompt", help="describe the theme; needs a model (see 'theme-studio backend')")
        sp.add_argument("--ai", action="store_true", help="with --image: let the model assign roles (off by default; rules are faster and as good)")
        sp.add_argument("--name", help="theme folder name (default: from the image file name or prompt)")
        sp.add_argument("--title", help="display title")
        sp.add_argument("--light", action="store_true", help="make a light theme (pale background, dark text)")
        sp.add_argument("--accent", metavar="HEX", help="force the main accent colour, e.g. '#ff8a3d'")
        sp.add_argument("--no-fix", action="store_true", help="don't auto-fix contrast on generated themes")
        sp.add_argument("--fix", action="store_true", help="also auto-fix contrast on presets")
        sp.add_argument("--no-open", action="store_true", help="don't open the preview image")

    sp = sub.add_parser("preview", help="render a preview, write nothing to your themes")
    inputs(sp)

    sp = sub.add_parser("make", help="preview, ask, then write the theme")
    inputs(sp)
    sp.add_argument("--all-presets", action="store_true", help="write every preset (skips existing files)")
    sp.add_argument("--targets", help="comma list, 'auto' or 'all' (default from config: auto)")
    sp.add_argument("--yes", "-y", action="store_true", help="don't ask, just write")
    sp.add_argument("--preview", action="store_true", help="render the preview even with --yes")
    sp.add_argument("--force", action="store_true", help="overwrite existing files")
    sp.add_argument("--apply", action="store_true", help="switch to the theme right after creating it")

    sp = sub.add_parser("check", help="contrast report for a theme or preset")
    sp.add_argument("name", nargs="?")
    sp.add_argument("--preset")
    sp.add_argument("--palette")

    sp = sub.add_parser("remove", help="delete a theme (asks first)")
    sp.add_argument("name")
    sp.add_argument("--yes", "-y", action="store_true")

    sp = sub.add_parser("apply", help="switch to a theme")
    sp.add_argument("name")
    sp.add_argument("--targets", help="comma list, 'auto' or 'all'")
    sp.add_argument("--yes", "-y", action="store_true")

    sp = sub.add_parser("unhook", help="undo every change 'apply' made to your configs")
    sp.add_argument("--yes", "-y", action="store_true")

    sub.add_parser("backend", help="show and test the model backend")
    sub.add_parser("gui", help="open the Theme Studio window")

    sp = sub.add_parser("init", help="write a starter ~/.config/theme-studio/config.toml")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--yes", "-y", action="store_true")

    args = ap.parse_args(argv)
    if args.cmd == "gui":
        from .gui.app import main as gui_main
        return gui_main()
    cfg = config_mod.load()
    {"list": cmd_list, "preview": cmd_preview, "make": cmd_make,
     "check": cmd_check, "remove": cmd_remove, "apply": cmd_apply, "unhook": cmd_unhook,
     "backend": cmd_backend, "init": cmd_init}[args.cmd](args, cfg)


if __name__ == "__main__":
    main()
