from src.gnn_graph import build_graph


def test_graph_has_bidirectional_typed_edges():
    graph = build_graph({"D1": {"HP:0000002"}}, {"HP:0000002": {"HP:0000001"}})
    nodes = {(n["type"], n["id"]): i for i, n in enumerate(graph["nodes"])}
    edges = {(e["source"], e["target"], e["relation"]) for e in graph["edges"]}
    d = nodes[("disease", "D1")]
    child = nodes[("phenotype", "HP:0000002")]
    parent = nodes[("phenotype", "HP:0000001")]
    assert (d, child, "disease_has_phenotype") in edges
    assert (child, d, "phenotype_of_disease") in edges
    assert (child, parent, "is_a_parent") in edges
    assert (parent, child, "has_child") in edges


def test_graph_deterministic_and_no_self_parent_edges():
    profiles = {"D2": {"HP:0000003"}, "D1": {"HP:0000002"}}
    parents = {"HP:0000002": {"HP:0000002", "HP:0000001"}}
    assert build_graph(profiles, parents) == build_graph(profiles, parents)
    assert all(e["source"] != e["target"] for e in build_graph(profiles, parents)["edges"])
