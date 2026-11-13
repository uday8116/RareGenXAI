"""Experimental HPO graph neural network reranker (PyTorch optional dependency).

GraphSAGE-style neighborhood aggregation over HPO is-a links. Disease embeddings
are pooled from their annotated HPO terms. Trained only on synthetic queries.
No patient-derived training labels and no claim of clinical validity.
"""
import random
import numpy as np
from src.ml import RareGenML, synthetic_observations


def _torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise ImportError("Install optional GNN dependency: pip install torch") from exc
    return torch, nn


class HPOGraphReranker:
    def __init__(self, profiles, parents, labels=None, hidden=32, seed=42):
        torch, nn = _torch()
        torch.manual_seed(seed)
        self.torch = torch
        self.ml = RareGenML(profiles, labels)
        self.ids = self.ml.ids
        self.labels = labels or {}
        self.terms = sorted(set().union(*(self.ml.profiles[d] for d in self.ids)) |
                            set(parents) | set().union(*(set(p) for p in parents.values())))
        self.term_idx = {t: i for i, t in enumerate(self.terms)}
        # Undirected HPO edges, including self loops; normalized mean aggregation.
        pairs = {(i, i) for i in range(len(self.terms))}
        for child, ps in parents.items():
            for parent in ps:
                if child in self.term_idx and parent in self.term_idx:
                    a, b = self.term_idx[child], self.term_idx[parent]
                    pairs.update(((a, b), (b, a)))
        source, target = zip(*sorted(pairs))
        self.src = torch.tensor(source, dtype=torch.long)
        self.dst = torch.tensor(target, dtype=torch.long)
        self.degree = torch.bincount(self.dst, minlength=len(self.terms)).clamp(min=1).float().unsqueeze(1)
        self.disease_terms = {d: torch.tensor([self.term_idx[t] for t in sorted(self.ml.profiles[d])],
                                              dtype=torch.long) for d in self.ids}
        class Network(nn.Module):
            def __init__(self, n, width):
                super().__init__()
                self.emb = nn.Embedding(n, width)
                self.self1 = nn.Linear(width, width)
                self.neigh1 = nn.Linear(width, width)
                self.self2 = nn.Linear(width, width)
                self.neigh2 = nn.Linear(width, width)
                self.head = nn.Sequential(nn.Linear(width * 3 + 7, width),
                                          nn.ReLU(), nn.Linear(width, 1))
            def forward(self, src, dst, degree):
                x = self.emb.weight
                agg = torch.zeros_like(x).index_add(0, dst, x[src]) / degree
                x = torch.relu(self.self1(x) + self.neigh1(agg))
                agg = torch.zeros_like(x).index_add(0, dst, x[src]) / degree
                return torch.relu(self.self2(x) + self.neigh2(agg))
        self.network = Network(len(self.terms), hidden)
        self.trained = False

    def _query(self, observations, embeddings):
        present = [(t, 1.0 if s == "confirmed_present" else 0.4)
                   for t, s in observations if s in ("confirmed_present", "suspected_present")
                   and t in self.term_idx]
        if not present:
            return None
        indices = self.torch.tensor([self.term_idx[t] for t, _ in present])
        weights = self.torch.tensor([w for _, w in present]).unsqueeze(1)
        return (embeddings[indices] * weights).sum(0) / weights.sum()

    def _scores(self, observations, candidates, embeddings):
        torch = self.torch
        query = self._query(observations, embeddings)
        if query is None:
            return None
        disease_vectors = torch.stack([embeddings[self.disease_terms[d]].mean(0) for d, _ in candidates])
        q = query.unsqueeze(0).expand_as(disease_vectors)
        features = torch.tensor(np.stack([self.ml.features(observations, d, sim)
                                          for d, sim in candidates]), dtype=torch.float32)
        return self.network.head(torch.cat((q, disease_vectors, q * disease_vectors, features), dim=1)).squeeze(1)

    def fit(self, seed=42, train_diseases=100, queries_per_disease=2,
            candidates=20, epochs=4, lr=0.003):
        torch = self.torch
        rng = random.Random(seed)
        eligible = [d for d in self.ids if len(self.ml.profiles[d]) >= 4]
        rng.shuffle(eligible)
        training = eligible[:train_diseases]
        examples = []
        for disease in training:
            for _ in range(queries_per_disease):
                obs = synthetic_observations(disease, self.ml.profiles, rng)
                found = dict(self.ml.retrieve(obs, k=candidates))
                # Force true disease only during synthetic training, never evaluation.
                found.setdefault(disease, self.ml._tfidf_for(obs, disease))
                pairs = list(found.items())
                target = next(i for i, (d, _) in enumerate(pairs) if d == disease)
                examples.append((obs, pairs, target))
        if not examples:
            raise ValueError("No eligible synthetic training examples")
        optimizer = torch.optim.Adam(self.network.parameters(), lr=lr)
        losses = []
        for _ in range(epochs):
            rng.shuffle(examples)
            total = 0.0
            for obs, pairs, target in examples:
                optimizer.zero_grad()
                embeddings = self.network(self.src, self.dst, self.degree)
                scores = self._scores(obs, pairs, embeddings)
                loss = torch.nn.functional.cross_entropy(scores.unsqueeze(0), torch.tensor([target]))
                loss.backward()
                optimizer.step()
                total += loss.item()
            losses.append(total / len(examples))
        self.trained = True
        return {"training_diseases": len(training), "training_queries": len(examples),
                "epoch_losses": losses, "training_kind": "synthetic_HPO_annotation_queries"}

    def rank(self, observations, k=40, top_k=5):
        if not self.trained:
            raise ValueError("GNN is not trained")
        candidates = self.ml.retrieve(observations, k=k)
        if not candidates:
            return []
        with self.torch.no_grad():
            embeddings = self.network(self.src, self.dst, self.degree)
            scores = self._scores(observations, candidates, embeddings).tolist()
        rows = [{"disease_id": d, "disease_name": self.labels.get(d, d),
                 "score": float(s)} for (d, _), s in zip(candidates, scores)]
        rows.sort(key=lambda r: (-r["score"], r["disease_id"]))
        return rows[:top_k] if top_k is not None else rows
