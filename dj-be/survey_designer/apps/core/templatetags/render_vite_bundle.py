import json
from pathlib import Path

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


def load_json_from_dist(json_filename="manifest.json"):
    manifest_file_path = Path(settings.VITE_APP_DIR, "dist", ".vite", json_filename)
    if not manifest_file_path.exists():
        raise FileNotFoundError(f"Vite manifest not found at: {manifest_file_path}")
    with open(manifest_file_path) as f:
        return json.load(f)


def find_vite_entry(manifest):
    for key, entry in manifest.items():
        if entry.get("isEntry"):
            return entry
    raise ValueError("No entry point with isEntry=True found in manifest.")


@register.simple_tag
def render_vite_bundle():
    manifest = load_json_from_dist()
    entry = manifest.get("index.html") or find_vite_entry(manifest)  # Fallback
    # Dynamic imports
    dynamic_scripts = ""
    for dyn_import in entry.get("dynamicImports", []):
        dyn_entry = manifest.get(dyn_import)
        if dyn_entry:
            dynamic_scripts += (
                f'<script type="module" src="/static/{dyn_entry["file"]}"></script>\n'
            )

    # Main bundle
    main_script = f'<script type="module" src="/static/{entry["file"]}"></script>'

    # CSS
    css_links = ""
    for css_file in entry.get("css", []):
        css_links += f'<link rel="stylesheet" href="/static/{css_file}" />\n'

    return mark_safe(dynamic_scripts + main_script + "\n" + css_links)
