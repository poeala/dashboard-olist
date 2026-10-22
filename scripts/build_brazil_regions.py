"""Regenera las regiones desde br_states.geojson. Requiere Shapely solo al generar."""
import json
import sys
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely import union_all, make_valid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.brazil_regions import REGIONS


def main():
    source = json.loads((ROOT / "assets/br_states.geojson").read_text(encoding="utf-8"))
    states = {f["id"]: make_valid(shape(f["geometry"])) for f in source["features"]}
    features = []
    for code, (name, members) in REGIONS.items():
        # Cartografía de visualización: ~1 km de tolerancia, sin alterar
        # los datos ni el agrupamiento. Preserva la topología de cada región.
        geometry = union_all([states[state] for state in members]).simplify(0.01, preserve_topology=True)
        assert geometry.is_valid and not geometry.is_empty
        features.append({
            "type": "Feature", "id": code,
            "properties": {"name": name, "states": list(members)},
            "geometry": mapping(geometry),
        })
    target = ROOT / "assets/br_regions.geojson"
    target.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                 ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Generadas {len(features)} regiones: {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
