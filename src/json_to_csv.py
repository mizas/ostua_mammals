# guarda como json_to_csv.py
import json
import csv
import os
import sys
from typing import List, Dict

INPUT_JSON = sys.argv[1]
OUT_SUMMARY = "predictions_summary.csv"
OUT_CLASSES = "classifications.csv"
OUT_DETECTIONS = "detections.csv"

def split_taxonomy(class_str: str):
    """
    Espera el formato:
    "<uuid>;kingdom;phylum;class;order;family;genus;species;common name"
    Pero en tu ejemplo hay 7 campos separados por ';' (uuid + 6 taxones + common name opcional).
    Nos adaptamos: devolvemos hasta 7 columnas: id, kingdom, orden, familia, genero, especie, common_name
    Ajusta según tu formato real.
    """
    parts = class_str.split(";")
    # Rellenar hasta 9 elementos para evitar IndexError (uuid + 7 campos)
    parts += [""] * (9 - len(parts))
    return {
        "class_uuid": parts[0],
        "kingdom": parts[1],
        "tax1": parts[2],
        "tax2": parts[3],
        "tax3": parts[4],
        "tax4": parts[5],
        "tax5": parts[6],
        "common_name": parts[7] if len(parts) > 7 else ""
    }

def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Asegurar directorio de salida
    os.makedirs(".", exist_ok=True)

    # Preparar archivos CSV
    with open(OUT_SUMMARY, "w", newline="", encoding="utf-8") as sum_f, \
         open(OUT_CLASSES, "w", newline="", encoding="utf-8") as cls_f, \
         open(OUT_DETECTIONS, "w", newline="", encoding="utf-8") as det_f:

        sum_writer = csv.DictWriter(sum_f, fieldnames=[
            "filepath", "country", "model_version",
            "prediction", "prediction_score", "prediction_source",
            "top_class", "top_score", "second_class", "second_score",
            "num_classes", "num_detections",
            "detection_label", "detection_conf",
            "bbox_x", "bbox_y", "bbox_w", "bbox_h"
        ])
        sum_writer.writeheader()

        cls_writer = csv.DictWriter(cls_f, fieldnames=[
            "filepath", "country", "model_version",
            "class_rank", "class_uuid",
            "kingdom", "tax1", "tax2", "tax3", "tax4", "tax5",
            "common_name", "score"
        ])
        cls_writer.writeheader()

        det_writer = csv.DictWriter(det_f, fieldnames=[
            "filepath", "country", "model_version",
            "detection_index", "category", "label", "conf",
            "bbox_x", "bbox_y", "bbox_w", "bbox_h"
        ])
        det_writer.writeheader()

        for pred in data.get("predictions", []):
            filepath = pred.get("filepath", "")
            country = pred.get("country", "")
            model_version = pred.get("model_version", "")
            prediction = pred.get("prediction", "")
            prediction_score = pred.get("prediction_score", "")
            prediction_source = pred.get("prediction_source", "")

            # clases y scores
            classes = pred.get("classifications", {}).get("classes", [])
            scores = pred.get("classifications", {}).get("scores", [])
            num_classes = max(len(classes), len(scores))

            # Top / second
            top_class = classes[0] if len(classes) > 0 else ""
            top_score = scores[0] if len(scores) > 0 else ""
            second_class = classes[1] if len(classes) > 1 else ""
            second_score = scores[1] if len(scores) > 1 else ""

            # detecciones (tomamos la primera si existe para el summary)
            detections = pred.get("detections", [])
            num_detections = len(detections)
            det0 = detections[0] if num_detections > 0 else {}
            detection_label = det0.get("label", "")
            detection_conf = det0.get("conf", "")
            bbox = det0.get("bbox", ["", "", "", ""])
            # Asegurar 4 valores bbox
            bbox += [""] * (4 - len(bbox))

            # Escribir summary
            sum_writer.writerow({
                "filepath": filepath,
                "country": country,
                "model_version": model_version,
                "prediction": prediction,
                "prediction_score": prediction_score,
                "prediction_source": prediction_source,
                "top_class": top_class,
                "top_score": top_score,
                "second_class": second_class,
                "second_score": second_score,
                "num_classes": num_classes,
                "num_detections": num_detections,
                "detection_label": detection_label,
                "detection_conf": detection_conf,
                "bbox_x": bbox[0],
                "bbox_y": bbox[1],
                "bbox_w": bbox[2],
                "bbox_h": bbox[3]
            })

            # Escribir todas las clases en classifications.csv
            for i, cls in enumerate(classes):
                tax = split_taxonomy(cls)
                score = scores[i] if i < len(scores) else ""
                cls_writer.writerow({
                    "filepath": filepath,
                    "country": country,
                    "model_version": model_version,
                    "class_rank": i+1,
                    "class_uuid": tax.get("class_uuid", ""),
                    "kingdom": tax.get("kingdom", ""),
                    "tax1": tax.get("tax1", ""),
                    "tax2": tax.get("tax2", ""),
                    "tax3": tax.get("tax3", ""),
                    "tax4": tax.get("tax4", ""),
                    "tax5": tax.get("tax5", ""),
                    "common_name": tax.get("common_name", ""),
                    "score": score
                })

            # Escribir detecciones en detections.csv
            for i, d in enumerate(detections):
                bbox = d.get("bbox", ["", "", "", ""])
                bbox += [""] * (4 - len(bbox))
                det_writer.writerow({
                    "filepath": filepath,
                    "country": country,
                    "model_version": model_version,
                    "detection_index": i+1,
                    "category": d.get("category", ""),
                    "label": d.get("label", ""),
                    "conf": d.get("conf", ""),
                    "bbox_x": bbox[0],
                    "bbox_y": bbox[1],
                    "bbox_w": bbox[2],
                    "bbox_h": bbox[3]
                })

    print("CSV generados:")
    print(" -", OUT_SUMMARY)
    print(" -", OUT_CLASSES)
    print(" -", OUT_DETECTIONS)

if __name__ == "__main__":
    main()
