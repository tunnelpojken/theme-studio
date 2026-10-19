"""Text prompt (+ optional image colours) -> Palette, using a language model.

Two backends, one request each:
  ollama  native /api/chat with a JSON schema in `format` (the reply is forced
          into the palette shape) and keep_alive so the model unloads after
  api     any OpenAI-compatible /chat/completions endpoint (OpenAI, OpenRouter,
          llama.cpp server, LM Studio, Ollama's /v1 ...) with json_schema output

The model only picks the mood: four accents and a background tint. Small local
models are good at "orange haze and teal -> these colours" but bad at building a
consistent 27-colour structure, so the code builds the rest (background layers,
text, terminal colours) with the same rules as image themes.
No extra dependencies: plain urllib.
"""
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request

from ..core.palette import Palette

HEX = {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"}
PICKS = {
    "primary": "the main accent: window borders, selected items. Vivid, bright enough to glow on a dark background",
    "secondary": "a second accent, a clearly different hue from primary",
    "tertiary": "a third accent, used sparingly",
    "error": "error colour, must read as alarming (a red or red-orange)",
    "background": "a very dark colour that sets the mood, tinted (e.g. deep teal-black), not plain grey",
}
SCHEMA = {
    "type": "object",
    "properties": {"colours": {"type": "string"}, "title": {"type": "string"}, "note": {"type": "string"},
                   **{k: HEX for k in PICKS}},
    "required": ["colours", "title", "note", *PICKS],
    "additionalProperties": False,
}

SYSTEM = """You pick colours for a dark Linux desktop theme.
Reply with ONE JSON object and nothing else. Every colour is "#rrggbb".

Fields, in this order:
- colours: first, name the subject's real, recognisable colours in plain words, most important
  first, e.g. "deep purple, lime green, orange". Think about what the subject actually looks like.
- title: 1 to 3 words naming the theme
- note: one short line describing the look
{picks}

Then pick the hex values to match the colours you named. Colours named in the user's idea
must be used as the accents. Choose colours that fit the idea;
the rest of the theme (panels, text, terminal colours) is built from yours automatically."""


class BackendError(RuntimeError):
    pass


def system_prompt():
    return SYSTEM.format(picks="\n".join(f"- {k}: {v}" for k, v in PICKS.items()))


def user_prompt(prompt, hints):
    parts = []
    if prompt:
        parts.append(f"Theme idea: {prompt}")
    if hints:
        listed = ", ".join(f"{h} ({share:.0%})" for h, share in hints[:12])
        parts.append("Colours from the user's wallpaper, most common first: " + listed +
                     ". Pick the accents and background from these (you may brighten accents), "
                     "so the theme matches the wallpaper.")
    return "\n\n".join(parts)


def api_key(b):
    if b.api_key_env:
        key = os.environ.get(b.api_key_env)
        if key:
            return key
    if shutil.which("secret-tool"):  # GNOME keyring / KWallet via libsecret
        try:
            key = subprocess.run(["secret-tool", "lookup", "service", "theme-studio"],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
            if key:
                return key
        except (OSError, subprocess.SubprocessError):
            pass
    return None


def _post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise BackendError(f"{e.code} from {url}: {detail}") from None
    except urllib.error.URLError as e:
        raise BackendError(f"can't reach {url} ({e.reason}). Is the server running?") from None
    except TimeoutError:
        raise BackendError(f"{url} took longer than {timeout}s") from None


def _get(url, headers, timeout=10):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise BackendError(f"{e.code} from {url}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise BackendError(f"can't reach {url} ({getattr(e, 'reason', e)})") from None


def ollama_base(b):
    return re.sub(r"/v1/?$", "", b.url.rstrip("/"))


def chat(b, messages, schema=None):
    """One model call. Returns the reply text."""
    schema = schema or SCHEMA
    if b.kind == "ollama":
        body = {"model": b.model, "messages": messages, "stream": False, "format": schema,
                "keep_alive": b.keep_alive, "options": {"temperature": b.temperature}, "think": False}
        try:
            data = _post(ollama_base(b) + "/api/chat", body, {}, b.timeout)
        except BackendError as e:
            if "think" not in str(e).lower():
                raise
            body.pop("think")   # older Ollama, or a model without a thinking switch
            data = _post(ollama_base(b) + "/api/chat", body, {}, b.timeout)
        return data.get("message", {}).get("content", "")
    if b.kind == "api":
        key = api_key(b)
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        url = b.url.rstrip("/") + "/chat/completions"
        body = {"model": b.model, "messages": messages, "temperature": b.temperature,
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": "palette", "schema": schema, "strict": True}}}
        try:
            data = _post(url, body, headers, b.timeout)
        except BackendError as e:
            if not str(e).startswith("400"):
                raise
            body["response_format"] = {"type": "json_object"}   # servers without json_schema
            data = _post(url, body, headers, b.timeout)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise BackendError(f"unexpected reply from {url}: {str(data)[:200]}") from None
    raise BackendError('no model configured. Set [backend] kind = "ollama" or "api" '
                       "in ~/.config/theme-studio/config.toml (see `theme-studio init`).")


def parse(text):
    """The first JSON object in the reply (tolerates code fences and thinking text)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in the reply")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj


def snap_to_image(picks, hints, prompt):
    """Give each model accent the nearest colour family that is really in the wallpaper.

    Families are the image's vivid colours grouped by hue (within 30°), strongest first.
    primary, secondary, tertiary are matched in that order to the nearest family still
    free (within 60°), else the strongest free one; when the families run out, the
    image's light tone (parchment, bone, silver) is used once. Returns (picks, notes).
    """
    from ..core.color import from_oklch, hue_distance, lift_chroma, lift_hue, to_oklch
    from ..core.colornames import named_hues

    asked = [h for _w, h in named_hues(prompt)]
    vivid = sorted(((to_oklch(h), sh) for h, sh in hints if to_oklch(h)[1] > 0.05 and 0.25 < to_oklch(h)[0] < 0.95),
                   key=lambda x: -(x[1] ** 0.5) * x[0][1])
    families = []
    for (L, C, H), sh in vivid:
        if not any(hue_distance(H, f[2]) <= 30 for f in families):
            families.append((L, C, H))
    light = [to_oklch(h) for h, sh in hints if to_oklch(h)[0] > 0.62 and sh > 0.01]
    light_used = False
    picks, notes, free = dict(picks), [], list(families)

    for role in ("primary", "secondary", "tertiary"):
        L, C, H = to_oklch(picks[role])
        if C >= 0.04 and any(hue_distance(H, a) <= 25 for a in asked):   # the user asked for this hue
            free = [f for f in free if hue_distance(f[2], H) > 30]
            continue
        near = min(free, key=lambda f: hue_distance(f[2], H)) if free else None
        if near and C >= 0.06 and hue_distance(near[2], H) <= 30:          # already a wallpaper colour
            free.remove(near)
            continue
        if near is None and not light_used and light:
            lL, lC, lH = max(light, key=lambda x: x[1])
            new = from_oklch(min(max(lL, 0.78), 0.88), min(max(lC, 0.03), 0.07), lH)
            light_used = True
        elif near is not None:
            fam = near if hue_distance(near[2], H) <= 60 and C >= 0.04 else free[0]
            free.remove(fam)
            L2 = min(max(fam[0], 0.62), 0.82)
            new = from_oklch(L2, lift_chroma(fam[0], L2, fam[2], max(fam[1], 0.1)), lift_hue(fam[0], L2, fam[2], fam[1]))
        else:
            continue
        notes.append(f"{role} {picks[role]} -> {new} (matched to the wallpaper)")
        picks[role] = new
    return picks, notes


PICK_SYSTEM = """You are art-directing a dark Linux desktop theme made from the user's wallpaper.
The colours below were measured from the wallpaper. You do NOT invent colours: you choose from
the list by letter. Reply with ONE JSON object and nothing else.

Fields, in this order:
- thinking: one sentence on what the picture shows and which colour should lead
- title: 1 to 3 words naming the theme
- note: one short line describing the look
- primary: letter of the main accent (window borders, selection): the colour the picture is about
- secondary: letter of a second accent, a different colour from primary
- tertiary: letter of a third accent, different from both
- background: letter whose hue faintly tints the dark background, or "neutral" for plain black

A, B, C are a balanced default; reorder or swap them when the picture calls for it."""


def pick_schema(letters):
    pick = {"type": "string", "enum": letters}
    return {
        "type": "object",
        "properties": {"thinking": {"type": "string"}, "title": {"type": "string"}, "note": {"type": "string"},
                       "primary": pick, "secondary": pick, "tertiary": pick,
                       "background": {"type": "string", "enum": letters + ["neutral"]}},
        "required": ["thinking", "title", "note", "primary", "secondary", "tertiary", "background"],
        "additionalProperties": False,
    }


def generate_from_image(b, name, prompt, hints, on_status=print):
    """MAGI with a wallpaper: the model assigns roles from the wallpaper's own colours,
    so the result always shares its colours with the no-AI theme."""
    from ..core.color import to_oklch
    from ..core.colornames import honour
    from .rules import build, candidates, describe

    menu = candidates(hints)
    letters = [chr(65 + i) for i in range(len(menu))]
    listing = "\n".join(f"{l}: {c}  {describe(c)}" for l, c in zip(letters, menu))
    user = f"Colours from the wallpaper:\n{listing}"
    if prompt:
        user = f"Theme idea: {prompt}\n\n" + user
    messages = [{"role": "system", "content": PICK_SYSTEM}, {"role": "user", "content": user}]
    schema = pick_schema(letters)
    last_error = None
    for attempt in (1, 2):
        on_status(f"Asking {b.model} ({b.kind})" + (" again" if attempt == 2 else "") + "...")
        reply = chat(b, messages, schema)
        try:
            data = parse(reply)
            idx = {}
            for role in ("primary", "secondary", "tertiary"):
                v = str(data.get(role, "")).strip().upper()[:1]
                if v not in letters:
                    raise ValueError(f"{role} must be one of {', '.join(letters)}")
                idx[role] = letters.index(v)
            if len(set(idx.values())) < 3:      # same colour twice: fill from the default order
                used, order = [], []
                for role in ("primary", "secondary", "tertiary"):
                    i = idx[role] if idx[role] not in used else next(j for j in range(len(menu)) if j not in used)
                    used.append(i)
                    idx[role] = i
            picks = {r: menu[i] for r, i in idx.items()}
            if data.get("thinking"):
                on_status(f"  MAGI: {str(data['thinking'])[:110]}")
            on_status("  roles: " + ", ".join(f"{r} {letters[i]} {describe(menu[i])}" for r, i in idx.items()))
            # Colours the user named in the directive still win
            picks, notes = honour(picks, prompt or "")
            for n in notes:
                on_status(f"  colour fix: {n}")
            bg = str(data.get("background", "neutral")).strip().upper()[:1]
            bg_hue = to_oklch(menu[letters.index(bg)])[2] if bg in letters else None
            title = str(data.get("title") or name.replace("-", " ").title())
            title = title.split(" - ")[0].split(":")[0].strip()[:32]
            p = build(hints, name, title=title, note=str(data.get("note") or "")[:120],
                      accent=picks["primary"], bg_hue=bg_hue)
            return Palette.from_dict({**p.__dict__, "secondary": picks["secondary"], "tertiary": picks["tertiary"]})
        except (ValueError, TypeError, AttributeError, StopIteration) as e:
            last_error = e
            messages += [{"role": "assistant", "content": reply[:4000]},
                         {"role": "user", "content": f"That reply was not usable: {e}. Reply again with only the JSON object."}]
    raise BackendError(f"the model's reply wasn't usable twice ({last_error})")


def generate(b, name, prompt=None, hints=None, on_status=print):
    """Ask the model for the mood colours, then build a full Palette from them."""
    from .rules import build

    if hints:
        return generate_from_image(b, name, prompt, hints, on_status)

    messages = [{"role": "system", "content": system_prompt()},
                {"role": "user", "content": user_prompt(prompt, hints)}]
    last_error = None
    for attempt in (1, 2):
        on_status(f"Asking {b.model} ({b.kind})" + (" again" if attempt == 2 else "") + "...")
        reply = chat(b, messages)
        try:
            data = parse(reply)
            picks = {k: str(data.get(k, "")).lower() for k in PICKS}
            bad = [k for k, v in picks.items() if not re.fullmatch(r"#[0-9a-f]{6}", v)]
            if bad:
                raise ValueError(f"these fields need a #rrggbb colour: {', '.join(bad)}")
            from ..core.color import from_oklch, hue_distance, lift_chroma, lift_hue, to_oklch
            from ..core.colornames import apply as apply_words, wants_black
            roles = ("primary", "secondary", "tertiary")
            words = str(data.get("colours", ""))
            if words:
                on_status(f"  model's colours: {words[:80]}")
            # 1. Colours YOU named define the accents, in the order you wrote them, and are
            #    locked: nothing below may change them.
            picks, notes, locked = apply_words(picks, prompt or "")
            # 2. The model's own colour words fill only the roles you left open.
            free = [r for r in roles if r not in locked]
            picks, more, _ = apply_words(picks, words, roles=free)
            notes += more
            # 3. Open accents too dark to stand out: lift them (browns go copper, not pink).
            for role in free:
                L, C, H = to_oklch(picks[role])
                if L < 0.55:
                    new = from_oklch(0.66, lift_chroma(L, 0.66, H, max(C, 0.08)), lift_hue(L, 0.66, H, C))
                    notes.append(f"{role} {picks[role]} -> {new} (too dark to stand out)")
                    picks[role] = new
            # 4. Open accents must differ from the others (neutrals like steel don't clash).
            for role, turn in (("secondary", 60), ("tertiary", -120)):
                if role in locked:
                    continue
                L, C, H = to_oklch(picks[role])
                others = [to_oklch(picks[r]) for r in roles if r != role]
                if C < 0.04 or all(o[1] < 0.04 or hue_distance(H, o[2]) >= 35 or abs(L - o[0]) >= 0.12
                                   for o in others):
                    continue
                new = from_oklch(min(max(L, 0.68), 0.82), max(C, 0.1), (to_oklch(picks["primary"])[2] + turn) % 360)
                notes.append(f"{role} {picks[role]} -> {new} (too close to the other accents)")
                picks[role] = new
            # 5. Error has to read as an error, and stand apart from a red accent.
            # Errors are always a true red (hue 27); only a red accent pushes them to red-orange.
            eL, eC, eH = to_oklch(picks["error"])
            new_e = from_oklch(min(max(eL, 0.6), 0.72), max(eC, 0.17), 27)
            if hue_distance(eH, 27) > 30 or eC < 0.11 or not 0.55 <= eL <= 0.8:
                notes.append(f"error {picks['error']} -> {new_e} (errors need to look like errors)")
            picks["error"] = new_e
            eH = 27
            for role in roles:
                L, C, H = to_oklch(picks[role])
                if C > 0.06 and hue_distance(H, eH) < 15:
                    if role in locked:      # your red stays; the error colour moves instead
                        picks["error"] = from_oklch(0.70, 0.18, 42)
                        notes.append(f"error -> {picks['error']} (your {role} is red, so errors go red-orange)")
                    else:
                        new_c = from_oklch(max(L, 0.78), C, 90)
                        notes.append(f"{role} {picks[role]} -> {new_c} (was the same as the error colour)")
                        picks[role] = new_c
                    break
            if wants_black(prompt):
                picks["background"] = "#0b0b0c"
            for n in notes:
                on_status(f"  colour fix: {n}")
            title = str(data.get("title") or name.replace("-", " ").title())
            title = title.split(" - ")[0].split(":")[0].strip()[:32]   # "Blade Runner - Orange..." -> "Blade Runner"
            note = str(data.get("note") or prompt or "")[:120]
            # Same builder as image themes: the background sets the surface tint, the
            # accents steer the terminal colours. Shares only rank them.
            colours = [(picks["background"], 0.55), (picks["primary"], 0.2),
                       (picks["secondary"], 0.15), (picks["tertiary"], 0.1)]
            p = build(colours, name, title=title, note=note, accent=picks["primary"])
            return Palette.from_dict({**p.__dict__, "secondary": picks["secondary"],
                                      "tertiary": picks["tertiary"], "error": picks["error"]})
        except (ValueError, TypeError, AttributeError) as e:
            last_error = e
            messages += [{"role": "assistant", "content": reply[:4000]},
                         {"role": "user", "content": f"That reply was not usable: {e}. "
                                                     "Reply again with only the corrected JSON object."}]
    raise BackendError(f"the model's reply wasn't usable twice ({last_error})")


def test(b):
    """Check the backend is reachable and the model exists. Returns a status line."""
    if b.kind == "ollama":
        tags = _get(ollama_base(b) + "/api/tags", {})
        names = [m.get("name", "") for m in tags.get("models", [])]
        want = b.model if ":" in b.model else b.model + ":latest"
        if want not in names and b.model not in names:
            raise BackendError(f"Ollama is running but '{b.model}' isn't pulled. Run: ollama pull {b.model}")
        return f"Ollama at {ollama_base(b)} is up, model {b.model} is available."
    if b.kind == "api":
        key = api_key(b)
        if not key:
            note = f"${b.api_key_env} is empty" if b.api_key_env else "no api_key_env set"
            raise BackendError(f"no API key ({note}).")
        _get(b.url.rstrip("/") + "/models", {"Authorization": f"Bearer {key}"})
        return f"API at {b.url} answered; model set to {b.model}."
    raise BackendError('backend kind is "none" (image themes still work without a model).')
