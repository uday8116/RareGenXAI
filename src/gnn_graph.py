"""Construct a typed HPO/disease graph for future graph neural network training.

This module builds graph inputs; it does not train or claim a GNN.
"""
import json
from pathlib import Path


def build_graph(profiles, parents):
    """Return deterministic node IDs and typed directed edges.

    Disease-to-phenotype associations are represented in both directions.
    HPO parent-child links are represented in both directions.
    """
    disease_ids = sorted(k for k, terms in profiles.items() if terms)
    phenotype_ids = sorted(set().union(*(set(v) for v in profiles.values())) |
                           set(parents) | set().union(*(set(v) for v in parents.values())))
    nodes = [("disease", d) for d in disease_ids] + [("phenotype", h) for h in phenotype_ids]
    index = {node: i for i, node in enumerate(nodes)}
    edges = set()
    for disease in disease_ids:
        for phenotype in profiles[disease]:
            a, b = index[("disease", disease)], index[("phenotype", phenotype)]
            edges.add((a, b, "disease_has_phenotype"))
            edges.add((b, a, "phenotype_of_disease"))
    for child, ancestors in parents.items():
        for parent in ancestors:
            a, b = index[("phenotype", child)], index[("phenotype", parent)]
            if a != b:
                edges.add((a, b, "is_a_parent"))
                edges.add((b, a, "has_child"))
    return {"nodes": [{"type": kind, "id": name} for kind, name in nodes],
            "edges": [{"source": a, "target": b, "relation": relation}
                      for a, b, relation in sorted(edges)]}


def main():
    from src.data import load_ontology
    from src.ranking import ontology_parents
    data = json.loads(Path("data/processed/profiles.json").read_text())
    graph = build_graph(data["profiles"], ontology_parents(load_ontology()))
    output = Path("data/processed/hpo_disease_graph.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph))
    print(f"Exported {len(graph['nodes'])} nodes and {len(graph['edges'])} directed typed edges to {output}")
    print("Graph input only; no GNN training or evaluation performed.")


if __name__ == "__main__":
    main()
