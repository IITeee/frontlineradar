"""Write the offline page and drop every other generated file. Keeps site/CNAME."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SITE = ROOT / "site"
SITE.mkdir(exist_ok=True)

for path in sorted(SITE.rglob("*"), reverse=True):
    if path.name == "CNAME":
        continue
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.is_dir():
        try:
            path.rmdir()
        except OSError:
            pass

(SITE / "index.html").write_text(
    """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Frontlineradar is offline.</title>
</head>
<body>
<p>Frontlineradar is offline.</p>
</body>
</html>
""",
    encoding="utf-8",
)
print("built offline site/")
