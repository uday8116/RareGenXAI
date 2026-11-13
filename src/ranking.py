"""Deterministic, auditable HPO similarity and evidence-quality ranking.

Scores are relative ranking scores, NOT probabilities of diagnosis.
Unknown observations are ignored. Suspected positive findings have lower weight.
The absence penalty applies only to explicitly confirmed-absent findings.
"""
from collections import Counter
import math

def ancestors(term, parents):
    """Return a term and all ancestors, with cycle protection."""
    seen, pending = set(), [term]
    while pending:
        node = pending.pop()
        if node not in seen:
            seen.add(node)
            pending.extend(parents.get(node, ()))
    return seen

def ontology_parents(ontology):
    """Extract direct is-a parents from pronto ontology."""
    result = {}
    for term in ontology.terms():
        result[term.id] = {p.id for p in term.superclasses(distance=1, with_self=False)}
    return result

def information_content(profiles, parents):
    """Smoothed disease-frequency IC of each term (including ancestors)."""
    counts = Counter()
    n = len(profiles)
    for terms in profiles.values():
        expanded = set()
        for term in terms:
            expanded.update(ancestors(term, parents))
        counts.update(expanded)
    return {t: -math.log((c + 1) / (n + 1)) for t, c in counts.items()}

def semantic_similarity(a, b, parents, ic):
    common = ancestors(a, parents) & ancestors(b, parents)
    mica = max((ic.get(t, 0.0) for t in common), default=0.0)
    denom = max(ic.get(a, 0.0), ic.get(b, 0.0), 1e-9)
    return min(1.0, mica / denom)

def similarity_to_profile(term, disease_terms, parents, ic, method="semantic"):
    if not disease_terms:
        return 0.0
    if method == "overlap":
        return float(term in disease_terms)
    return max(semantic_similarity(term, candidate, parents, ic) for candidate in disease_terms)

WEIGHTS = {"confirmed_present": 1.0, "suspected_present": 0.4, "confirmed_absent": -0.6, "unknown": 0.0}

def rank(observations, profiles, parents, ic, labels=None, method="semantic", quality=True, top_k=5):
    """observations: list of (HPO ID, observation status).

    Baseline quality=False ignores negative/unknown and weights all positive equally.
    Score = weighted sum of per-finding matches divided by positive evidence weight.
    """
    labels = labels or {}
    allowed = set(WEIGHTS)
    for term, status in observations:
        if status not in allowed:
            raise ValueError(f"Unknown observation status: {status}")
        if not term.startswith("HP:"):
            raise ValueError(f"Invalid HPO ID: {term}")
    denominator = sum((abs(WEIGHTS[s]) if quality else 1.0)
                      for _, s in observations if s != "unknown" and (quality or s.endswith("present")))
    if denominator == 0:
        return []
    results = []
    for disease, disease_terms in profiles.items():
        evidence = []
        for term, status in observations:
            weight = WEIGHTS[status] if quality else (1.0 if status.endswith("present") else 0.0)
            if not weight:
                continue
            match = similarity_to_profile(term, disease_terms, parents, ic, method)
            contribution = weight * match / denominator
            evidence.append({"hpo_id": term, "status": status, "match": round(match, 4),
                             "contribution": round(contribution, 6)})
        score = sum(e["contribution"] for e in evidence)
        results.append({"disease_id": disease, "disease_name": labels.get(disease, disease),
                        "score": round(score, 6), "evidence": evidence})
    results.sort(key=lambda r: (-r["score"], r["disease_id"]))
    return results[:top_k]
