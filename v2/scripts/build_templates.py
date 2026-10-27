from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
outputs = {
    "marketing.html": ("index.html", "marketing.html"),
    "platform.html": ("platform/index.html", "platform.html"),
    "search.html": ("search/index.html", "search.html"),
    "research.html": ("research/index.html", "research.html"),
    "map.html": ("map/index.html", "map.html"),
    "privacy.html": ("privacy/index.html",),
    "policy.html": ("terms/index.html", "acceptable-use/index.html"),
    "artifact.html": ("report/artifact.html",),
    "query.html": ("query/index.html",),
    "nodes.html": ("nodes/index.html",),
}
def render_static_source(name):
    text = (ROOT / "pages" / name).read_text()
    text = re.sub(r"\{\{\s*url_for\('static', filename='([^']+)'\)\s*\}\}", r"/static/\1", text)
    return (text.replace("{{ max_posts }}", "100").replace("{{ max_linked }}", "20")
            .replace("{{ report_json }}", "__REPORT_JSON__"))


def write_dossier_shell(destination, data_url):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shell = render_static_source("artifact.html")
    destination.write_text(shell.replace("__REPORT_JSON__", data_url))


for source, targets in outputs.items():
    for target in targets:
        destination = ROOT / "static" / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = render_static_source(source)
        if source == "artifact.html":
            content = content.replace("__REPORT_JSON__", "")
        if source == "policy.html":
            if "terms" in target:
                content = (content.replace("{{ title }}", "Terms of Service")
                           .replace("{{ heading }}", "Terms of Service")
                           .replace("{{ doc }}", "/static/terms.md"))
            else:
                content = (content.replace("{{ title }}", "Acceptable Use Policy")
                           .replace("{{ heading }}", "Acceptable Use Policy")
                           .replace("{{ doc }}", "/static/acceptable-use.md"))
        destination.write_text(content)

for data_file in (ROOT / "static" / "report").rglob("report.json"):
    report_dir = data_file.parent
    write_dossier_shell(report_dir / "index.html", "./report.json")
    write_dossier_shell(report_dir / "report.html", "./report.json")

natgeo_report = ROOT / "static" / "report" / "natgeo" / "report.json"
if natgeo_report.exists():
    write_dossier_shell(ROOT / "static" / "report" / "natgeo.html", "./natgeo/report.json")

# Materialize global unified stylesheet
for stylesheet in (ROOT / "styles").glob("*.css"):
    output = ROOT / "static" / stylesheet.name
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(stylesheet, output)

portal_shell = ROOT / "v2" / "portal" / "saas-shell.js"
shutil.copyfile(portal_shell, ROOT / "static" / "saas-shell.js")

privacy_source = ROOT / "docs" / "PRIVACY.md"
terms_source = ROOT / "docs" / "TERMS.md"
acceptable_use_source = ROOT / "docs" / "ACCEPTABLE_USE.md"
policy_files = [
    (privacy_source, "privacy.md"),
    (terms_source, "terms.md"),
    (acceptable_use_source, "acceptable-use.md"),
]
for source, name in policy_files:
    output = ROOT / "static" / name
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)
