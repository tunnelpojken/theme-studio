"""The Palette: one theme described once, shared by every target."""
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROLES = ["primary", "secondary", "tertiary", "error",
         "surface", "variant", "hover", "outline", "shadow",
         "on_surface", "on_variant"]
ANSI = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass
class Palette:
    name: str            # folder slug, e.g. "blade-runner"
    title: str           # "Blade Runner"
    palette: str         # Noctalia palette name, e.g. "BladeRunner"
    note: str
    primary: str
    secondary: str
    tertiary: str
    error: str
    surface: str
    variant: str
    hover: str
    outline: str
    shadow: str
    on_surface: str
    on_variant: str
    normal: list = field(default_factory=list)
    bright: list = field(default_factory=list)
    dark: bool = True

    def __post_init__(self):
        problems = validate(self)
        if problems:
            raise ValueError(f"palette '{self.name}': " + "; ".join(problems))

    # Lets the ported writers keep using d["primary"] like THEME_DEFS entries
    def __getitem__(self, key):
        return getattr(self, key)

    def to_json(self):
        return json.dumps(asdict(self), indent=2) + "\n"

    @classmethod
    def from_dict(cls, d):
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))


def validate(p):
    problems = []
    for role in ROLES:
        if not HEX.match(str(getattr(p, role))):
            problems.append(f"{role} is not #rrggbb: {getattr(p, role)!r}")
    for group in ("normal", "bright"):
        colours = getattr(p, group)
        if len(colours) != 8:
            problems.append(f"{group} needs 8 colours, has {len(colours)}")
        problems += [f"{group} has bad colour {c!r}" for c in colours if not HEX.match(str(c))]
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", p.name):
        problems.append(f"name must be lowercase letters, digits and dashes: {p.name!r}")
    return problems


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "theme"


def camel(slug):
    return "".join(part.capitalize() for part in slug.split("-"))
