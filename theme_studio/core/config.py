"""Settings from ~/.config/theme-studio/config.toml, with sensible defaults.

`theme-studio init` writes a commented config for this machine.
"""
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import platform

PACKAGE = Path(__file__).resolve().parent.parent

# Targets an existing switch.sh already takes care of
SWITCH_SH_HANDLES = ["hyprland", "kitty", "noctalia", "wallpaper"]


def _expand(p):
    return Path(p).expanduser()


@dataclass
class Backend:
    kind: str = "none"                        # "none" | "ollama" | "api"
    url: str = "http://localhost:11434"
    model: str = "qwen3:8b"
    api_key_env: str = ""
    keep_alive: str = "0"                     # Ollama: unload the model right after (frees VRAM)
    temperature: float = 0.8
    timeout: int = 180


@dataclass
class Config:
    themes: Path
    noctalia_palettes: Path
    noctalia_template: Path
    targets: object = "auto"
    text_min: float = 7.0
    accent_min: float = 4.5
    backend: Backend = field(default_factory=Backend)
    apply_command: str = ""                   # e.g. "~/.config/themes/switch.sh {name}"
    command_handles: list = field(default_factory=list)
    # Clearing Lua's module cache first makes a Hyprland reload read the new theme
    hypr_lua_include: str = 'package.loaded["theme-studio"] = nil; require("theme-studio")'

    @property
    def cache(self):
        return platform.cache_dir()

    @property
    def data(self):
        return platform.data_dir()


def config_path():
    return platform.config_dir() / "config.toml"


def load():
    home = Path.home()
    data = {}
    if config_path().exists():
        data = tomllib.loads(config_path().read_text(encoding="utf-8"))
    paths = data.get("paths", {})

    # Existing ~/.config/themes setups (switch.sh style) are used as-is;
    # everyone else gets a folder owned by the app.
    themes = _expand(paths.get("themes", platform.default_themes_dir()))

    template = paths.get("noctalia_template")
    if template:
        template = _expand(template)
    elif (themes / "rei-ayanami/noctalia.toml").exists():
        template = themes / "rei-ayanami/noctalia.toml"
    else:
        template = PACKAGE / "templates/noctalia.toml"

    b = data.get("backend", {})
    backend = Backend(**{k: v for k, v in b.items() if k in Backend.__dataclass_fields__})

    # Apply: a user's own switcher (switch.sh) runs first if there is one
    apply = data.get("apply", {})
    switch = themes / "switch.sh"
    has_switch = switch.exists() and not platform.IS_WINDOWS
    command = apply.get("command", f"{switch} {{name}}" if has_switch else "")
    handles = apply.get("command_handles", SWITCH_SH_HANDLES if command else [])

    contrast = data.get("contrast", {})
    return Config(
        themes=themes,
        noctalia_palettes=_expand(paths.get("noctalia_palettes", home / ".config/noctalia/palettes")),
        noctalia_template=template,
        targets=data.get("targets", {}).get("enabled", "auto"),
        text_min=float(contrast.get("text_min", 7.0)),
        accent_min=float(contrast.get("accent_min", 4.5)),
        backend=backend,
        apply_command=command,
        command_handles=list(handles),
        hypr_lua_include=data.get("hyprland", {}).get("lua_include", 'package.loaded["theme-studio"] = nil; require("theme-studio")'),
    )


def example(cfg):
    """A commented config.toml describing this machine, for `theme-studio init`."""
    ollama = shutil.which("ollama") is not None
    lines = [
        "# theme-studio config. Delete a line to use the default.",
        "",
        "[paths]",
        f'themes = "{cfg.themes}"',
        f'noctalia_palettes = "{cfg.noctalia_palettes}"',
        f'noctalia_template = "{cfg.noctalia_template}"',
        "",
        "[targets]",
        'enabled = "auto"        # or a list, e.g. ["hyprland", "kitty", "fish"]',
        "",
        "[backend]",
        f'kind = "{"ollama" if ollama else "none"}"          # "none" | "ollama" | "api"',
        'url = "http://localhost:11434"     # Ollama, or an OpenAI-compatible base URL ending in /v1',
        'model = "qwen3:8b"',
        'api_key_env = ""                    # env var holding the key, for kind = "api"',
        'keep_alive = "0"                    # Ollama: unload the model after each theme',
        "",
        "[apply]",
        f'command = "{cfg.apply_command}"' + ("   # your own switcher runs first" if cfg.apply_command else ""),
        f"command_handles = {cfg.command_handles!r}".replace("'", '"'),
        "",
        "[hyprland]",
        "# Line added to hyprland.lua so it loads theme-studio.lua (Lua configs only)",
        f"lua_include = '{cfg.hypr_lua_include}'",
        "",
        "[contrast]",
        f"text_min = {cfg.text_min}",
        f"accent_min = {cfg.accent_min}",
        "",
    ]
    return "\n".join(lines)
