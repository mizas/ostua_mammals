#!/usr/bin/env python3
# make_mosaic_debug.py
# Versión robusta que imprime diagnóstico y genera el mosaic (lightbox opcional).

import argparse
import csv
import html
from pathlib import Path
import sys
import gzip, io

TEMPLATE_HEAD = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Mosaico de imágenes</title>
<style>
:root{--gap:8px}
body{font-family:system-ui, -apple-system, "Segoe UI", Roboto, Arial; margin:12px; background:#f7f7f7; color:#111}
.container{max-width:1200px;margin:0 auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:var(--gap)}
.card{position:relative;overflow:hidden;border-radius:6px;height:0;padding-bottom:75%;background:#ddd;box-shadow:0 1px 4px rgba(0,0,0,0.06)}
.card img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;transition:transform .35s ease}
.card:hover img{transform:scale(1.06)}
.caption{position:absolute;left:6px;right:6px;bottom:6px;font-size:12px;background:rgba(0,0,0,0.45);color:#fff;padding:4px 6px;border-radius:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lightbox-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;z-index:9999;padding:20px;visibility:hidden;opacity:0;transition:opacity .2s}
.lightbox-overlay.visible{visibility:visible;opacity:1}
.lightbox-content{max-width:100%;max-height:100%;text-align:center}
.lightbox-content img{max-width:100%;max-height:80vh;box-shadow:0 8px 30px rgba(0,0,0,0.6)}
.lightbox-caption{color:#fff;margin-top:10px;font-size:14px}
.lightbox-close{position:absolute;top:12px;right:18px;color:#fff;font-size:28px;cursor:pointer}
@media (max-width:420px){.caption{font-size:10px}}
</style>
</head>
<body>
<div class="container">
<h1>Mosaico de imágenes</h1>
<div class="grid">
"""

TEMPLATE_FOOT = """
</div> <!-- .grid -->
</div> <!-- .container -->
{lightbox_html}
{lightbox_js}
</body>
</html>
"""

LIGHTBOX_HTML = """
<div id="lightbox" class="lightbox-overlay" tabindex="-1" role="dialog" aria-hidden="true">
  <div class="lightbox-close" id="lightbox-close" aria-label="Cerrar">&times;</div>
  <div class="lightbox-content">
    <img id="lightbox-img" src="" alt="">
    <div class="lightbox-caption" id="lightbox-caption"></div>
  </div>
</div>
"""

LIGHTBOX_JS = """
<script>
(function(){
  const overlay = document.getElementById('lightbox');
  const img = document.getElementById('lightbox-img');
  const caption = document.getElementById('lightbox-caption');
  const closeBtn = document.getElementById('lightbox-close');

  function show(src, text){
    img.src = src;
    img.alt = text || '';
    caption.textContent = text || '';
    overlay.classList.add('visible');
    overlay.focus();
  }
  function hide(){
    overlay.classList.remove('visible');
    setTimeout(()=>{ img.src = ''; }, 200);
  }

  document.addEventListener('click', function(e){
    const t = e.target.closest('[data-lightbox]');
    if(t){
      e.preventDefault();
      show(t.getAttribute('href'), t.getAttribute('data-caption'));
    }
  }, false);

  overlay.addEventListener('click', function(e){
    if(e.target === overlay || e.target === closeBtn) hide();
  });

  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape') hide();
  });
})();
</script>
"""

def detect_column(reader_fieldnames, preferred):
    if preferred and preferred in reader_fieldnames:
        return preferred
    return reader_fieldnames[0] if reader_fieldnames else None

def open_text_maybe_gzip(path):
    p = Path(path)
    try:
        with p.open('rb') as fh:
            head = fh.read(2)
    except Exception:
        head = b''
    if p.suffix == '.gz' or head == b'\x1f\x8b':
        # open gzip as text
        return io.TextIOWrapper(gzip.open(p, 'rb'), encoding='utf-8', errors='replace', newline='')
    return p.open('r', encoding='utf-8', errors='replace', newline='')

def main():
    p = argparse.ArgumentParser(description="Genera un mosaico HTML desde CSV con rutas de imágenes. (debug)")
    p.add_argument("csvfile", help="CSV de entrada con rutas de imágenes")
    p.add_argument("-o", "--output", default="mosaic.html", help="HTML de salida (por defecto mosaic.html)")
    p.add_argument("--col", default="filepath", help="Nombre de la columna con las rutas (por defecto 'filepath')")
    p.add_argument("--lightbox", action="store_true", help="Activar lightbox (clic para ver ampliada)")
    args = p.parse_args()

    csvpath = Path(args.csvfile)

    if not csvpath.exists():
        print("Error: CSV no encontrado:", csvpath, file=sys.stderr)
        sys.exit(2)

    # --- generar nombre del HTML igual al base del CSV ---
    # Solo si el usuario NO especificó -o/--output explícitamente
    if args.output == "mosaic.html" or args.output is None:
        base = csvpath.name

        # quitar .gz si viene comprimido
        if base.lower().endswith(".gz"):
            base = base[:-3]

        # quitar .csv si lo tiene
        if base.lower().endswith(".csv"):
            base = base[:-4]

        # construir nombre final en el mismo directorio
        args.output = str(csvpath.parent / f"{base}.html")

    print(f"DEBUG: HTML de salida --> {args.output}", file=sys.stderr)



    # ---- read robustly ----
    rows = []
    with open_text_maybe_gzip(csvpath) as fh:
        reader = csv.DictReader(fh)
        print("DEBUG: fieldnames read by DictReader:", reader.fieldnames, file=sys.stderr)
        if reader.fieldnames:
            # normalize
            fn = [c.strip() for c in reader.fieldnames]
            col = detect_column(fn, args.col)
            print(f"DEBUG: using column -> {col}", file=sys.stderr)
            # rewind not possible for DictReader, so iterate directly
            fh.seek(0)
            # If header looks like a single junk header (e.g. 'x'), fallback to simple reader
            if len(fn) == 1 and fn[0].lower() in ("", "x"):
                fh.seek(0)
                for r in csv.reader(fh):
                    if not r: continue
                    val = r[0].strip().strip('"')
                    if val: rows.append(val)
            else:
                # skip header row by creating DictReader again from current fh
                fh.seek(0)
                reader2 = csv.DictReader(fh)
                for r in reader2:
                    val = (r.get(col) or "").strip().strip('"')
                    if val: rows.append(val)
        else:
            fh.seek(0)
            for r in csv.reader(fh):
                if not r: continue
                val = r[0].strip().strip('"')
                if val: rows.append(val)

    print(f"DEBUG: rutas encontradas = {len(rows)}", file=sys.stderr)
    if len(rows) > 0:
        print("DEBUG: primeras 10 rutas:", file=sys.stderr)
        for i,rr in enumerate(rows[:10], start=1):
            print(i, rr, file=sys.stderr)
    else:
        print("No se encontraron rutas válidas en el CSV.", file=sys.stderr)
        sys.exit(3)

    # ---- build HTML ----
    out = []
    out.append(TEMPLATE_HEAD)
    for path in rows:
        esc_path = html.escape(path, quote=True)
        caption = html.escape(Path(path).name)
        if args.lightbox:
            out.append(f'<a class="card" href="{esc_path}" data-lightbox data-caption="{caption}">')
            out.append(f'  <img src="{esc_path}" loading="lazy" alt="{caption}">')
            out.append(f'  <div class="caption">{caption}</div>')
            out.append('</a>')
        else:
            out.append('<div class="card">')
            out.append(f'  <img src="{esc_path}" loading="lazy" alt="{caption}">')
            out.append(f'  <div class="caption">{caption}</div>')
            out.append('</div>')

    lightbox_html = LIGHTBOX_HTML if args.lightbox else ""
    lightbox_js = LIGHTBOX_JS if args.lightbox else ""
    out.append(TEMPLATE_FOOT.format(lightbox_html=lightbox_html, lightbox_js=lightbox_js))

    out_html = "\n".join(out)
    outpath = Path(args.output)
    outpath.write_text(out_html, encoding='utf-8')
    print("Generado:", outpath.resolve())

if __name__ == "__main__":
    main()
