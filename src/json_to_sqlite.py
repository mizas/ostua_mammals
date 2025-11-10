#!/usr/bin/env python3
"""
json_to_sqlite.py
Convierte archivos JSON con la estructura de 'predictions' a una base SQLite.
Uso:
  python json_to_sqlite.py input.json
"""

import json
import sqlite3
import sys
import os
from typing import List, Tuple, Optional

DB_PATH = "predictions.db"

CREATE_TABLES_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filepath TEXT NOT NULL,
  country TEXT,
  prediction TEXT,
  prediction_score REAL,
  prediction_source TEXT,
  model_version TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  image_id INTEGER NOT NULL,
  class_uuid TEXT,
  tax_class TEXT,
  tax_order TEXT,
  tax_family TEXT,
  tax_genus TEXT,
  tax_species TEXT,
  common_name TEXT,
  score REAL,
  rank_integer INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS detections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  image_id INTEGER NOT NULL,
  category TEXT,
  label TEXT,
  conf REAL,
  bbox_x REAL,
  bbox_y REAL,
  bbox_w REAL,
  bbox_h REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_images_filepath ON images(filepath);
CREATE INDEX IF NOT EXISTS idx_classifications_image ON classifications(image_id);
CREATE INDEX IF NOT EXISTS idx_detections_image ON detections(image_id);
CREATE INDEX IF NOT EXISTS idx_classifications_score ON classifications(score DESC);
"""

def parse_tax_string(s: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    # formato esperado: uuid;class;order;family;genus;species;common name
    parts = s.split(";")
    # rellenar hasta 7 elementos
    parts += [None] * (7 - len(parts))
    return tuple(parts[:7])

def insert_image_and_relations(conn: sqlite3.Connection, pred: dict):
    cur = conn.cursor()
    filepath = pred.get("filepath")
    country = pred.get("country")
    prediction = pred.get("prediction")
    prediction_score = pred.get("prediction_score")
    prediction_source = pred.get("prediction_source")
    model_version = pred.get("model_version")

    cur.execute("""
        INSERT INTO images (filepath, country, prediction, prediction_score, prediction_source, model_version)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (filepath, country, prediction, prediction_score, prediction_source, model_version))
    image_id = cur.lastrowid

    # classifications
    clas = pred.get("classifications", {})
    classes = clas.get("classes", [])
    scores = clas.get("scores", [])
    # ensure same length
    n = max(len(classes), len(scores))
    for i in range(n):
        class_str = classes[i] if i < len(classes) else None
        score = float(scores[i]) if i < len(scores) else None

        if class_str:
            uuid, tax_class, tax_order, tax_family, tax_genus, tax_species, common_name = parse_tax_string(class_str)
        else:
            uuid = tax_class = tax_order = tax_family = tax_genus = tax_species = common_name = None

        cur.execute("""
            INSERT INTO classifications (image_id, class_uuid, tax_class, tax_order, tax_family, tax_genus, tax_species, common_name, score, rank_integer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (image_id, uuid, tax_class, tax_order, tax_family, tax_genus, tax_species, common_name, score, i))

    # detections
    detections = pred.get("detections", [])
    for d in detections:
        category = d.get("category")
        label = d.get("label")
        conf = d.get("conf")
        bbox = d.get("bbox", [None, None, None, None])
        x,y,w,h = (bbox + [None]*4)[:4]
        cur.execute("""
            INSERT INTO detections (image_id, category, label, conf, bbox_x, bbox_y, bbox_w, bbox_h)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (image_id, category, label, conf, x, y, w, h))

    return image_id

def process_file(conn: sqlite3.Connection, path: str):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    preds = data.get("predictions", [])
    inserted = 0
    for p in preds:
        insert_image_and_relations(conn, p)
        inserted += 1
    conn.commit()
    return inserted

def main():
    if len(sys.argv) < 2:
        print("Uso: python json_to_sqlite.py archivo.json [otro.json ...]")
        sys.exit(1)

    files = sys.argv[1:]
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(CREATE_TABLES_SQL)

    total = 0
    for f in files:
        if not os.path.isfile(f):
            print(f"Archivo no encontrado: {f}")
            continue
        n = process_file(conn, f)
        print(f"Procesado {f}: {n} predicciones insertadas.")
        total += n

    conn.close()
    print(f"Hecho. Total de predicciones insertadas: {total}. DB: {DB_PATH}")

if __name__ == "__main__":
    main()
