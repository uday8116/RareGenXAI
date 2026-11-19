"""CPU-friendly TF-IDF disease retrieval and trained candidate re-ranking.

Training examples come from HPO disease annotations, NOT clinical patients.
Classifier output is an uncalibrated ranking signal, NOT a diagnostic probability.
"""
import csv
import hashlib
import random
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier

STATUSES = {"confirmed_present", "suspected_present", "confirmed_absent", "unknown"}
FEATURES = ["tfidf", "confirmed_recall", "suspected_recall", "disease_coverage",
            "absent_fraction", "positive_count", "disease_size"]


def synthetic_observations(disease, profiles, rng, missing=0.25):
    """Simulate observations from disease annotations; no patient-level cases."""
    selected = rng.sample(sorted(profiles[disease]), min(8, len(profiles[disease])))
    present = [term for term in selected if rng.random() >= missing]
    if not present:
        present = [rng.choice(selected)]
    observations = [(term, "suspected_present" if rng.random() < 0.3 else "confirmed_present")
                    for term in present]
    # Simulated NOT-observed term, never claimed to be clinically confirmed.
    if rng.random() < 0.4:
        other = rng.choice(sorted(k for k in profiles if k != disease))
        negatives = sorted(profiles[other] - profiles[disease])
        if negatives:
            observations.append((rng.choice(negatives), "confirmed_absent"))
    return observations


class RareGenML:
    """Sparse HPO TF-IDF retrieval, logistic regression and random-forest reranking."""

    def __init__(self, profiles, labels=None):
        self.ids = sorted(k for k, terms in profiles.items() if terms)
        self.profiles = {k: set(profiles[k]) for k in self.ids}
        self.labels = labels or {}
        self.vectorizer = TfidfVectorizer(token_pattern=r"(?u)\bHP_\d+\b", lowercase=False,
                                          norm="l2", sublinear_tf=True)
        docs = [" ".join(term.replace(":", "_") for term in sorted(self.profiles[k])) for k in self.ids]
        self.matrix = self.vectorizer.fit_transform(docs)
        self.index = {name: idx for idx, name in enumerate(self.ids)}
        self.models = {}

    @staticmethod
    def _validate(observations):
        for term, status in observations:
            if status not in STATUSES or not term.startswith("HP:"):
                raise ValueError(f"Invalid observation: {term}, {status}")

    def retrieve(self, observations, k=40):
        self._validate(observations)
        positive = [term for term, status in observations if status in ("confirmed_present", "suspected_present")]
        if not positive:
            return []
        if not isinstance(k, int) or k < 1:
            raise ValueError("Retrieval candidate limit k must be positive")
        query = self.vectorizer.transform([" ".join(term.replace(":", "_") for term in positive)])
        similarities = (self.matrix @ query.T).toarray().reshape(-1)
        if not np.any(similarities > 0):
            return []
        count = min(k, len(self.ids))
        indices = np.argpartition(-similarities, count - 1)[:count]
        ordered = sorted(indices, key=lambda i: (-float(similarities[i]), self.ids[i]))
        return [(self.ids[i], float(similarities[i])) for i in ordered]

    def features(self, observations, disease, similarity):
        profile = self.profiles[disease]
        confirmed = [term for term, status in observations if status == "confirmed_present"]
        suspected = [term for term, status in observations if status == "suspected_present"]
        absent = [term for term, status in observations if status == "confirmed_absent"]
        positives = confirmed + suspected
        return np.array([similarity,
                sum(t in profile for t in confirmed) / max(1, len(confirmed)),
                sum(t in profile for t in suspected) / max(1, len(suspected)),
                sum(t in profile for t in positives) / max(1, len(profile)),
                sum(t in profile for t in absent) / max(1, len(absent)),
                len(positives) / 8.0, min(len(profile), 100) / 100.0], dtype=np.float64)

    def _fit(self, x, y, seed):
        if len(set(y)) != 2:
            raise ValueError("Training needs positive and negative candidate pairs")
        self.models["logistic"] = LogisticRegression(max_iter=600, class_weight="balanced", random_state=seed)
        self.models["random_forest"] = RandomForestClassifier(
            n_estimators=80, max_depth=9, min_samples_leaf=2, n_jobs=1,
            class_weight="balanced_subsample", random_state=seed)
        self.models["xgboost"] = XGBClassifier(n_estimators=80, max_depth=4, learning_rate=0.07, subsample=0.85, colsample_bytree=0.9, objective="binary:logistic", eval_metric="logloss", n_jobs=1, random_state=seed)
        self.models["mlp"] = MLPClassifier(hidden_layer_sizes=(32, 16), activation="relu", alpha=0.01, max_iter=350, early_stopping=False, random_state=seed)
        for model in self.models.values():
            model.fit(x, y)

    def train(self, seed=42, train_diseases=200, test_diseases=60, queries_per_disease=2,
              candidates=25):
        """Hold out entire disease IDs for testing; knowledge base remains available.

        Training candidate pairs can include the ground truth explicitly. Held-out
        evaluation NEVER forces the correct disease into the candidate shortlist.
        """
        if any(not isinstance(value, int) or value < 1 for value in
               (train_diseases, test_diseases, queries_per_disease, candidates)):
            raise ValueError("Training sizes and candidate count must be positive integers")
        rng = random.Random(seed)
        eligible = sorted(k for k in self.ids if len(self.profiles[k]) >= 4)
        rng.shuffle(eligible)
        if len(eligible) < 4:
            raise ValueError("At least four diseases with >=4 phenotypes are required")
        test_count = min(test_diseases, max(1, len(eligible) // 4))
        train_count = min(train_diseases, len(eligible) - test_count)
        training = eligible[:train_count]
        heldout = eligible[train_count:train_count + test_count]
        x, y = [], []
        for disease in training:
            for _ in range(queries_per_disease):
                observations = synthetic_observations(disease, self.profiles, rng)
                candidates_by_id = dict(self.retrieve(observations, k=candidates))
                if disease not in candidates_by_id:
                    candidates_by_id[disease] = self._tfidf_for(observations, disease)
                for candidate_id, score in candidates_by_id.items():
                    x.append(self.features(observations, candidate_id, score))
                    y.append(int(candidate_id == disease))
        features_matrix = np.stack(x).astype(np.float64, copy=False)
        target_labels = np.array(y, dtype=np.int8)
        training_input_sha256 = hashlib.sha256(
            features_matrix.tobytes(order="C") + target_labels.tobytes(order="C")
        ).hexdigest()
        self._fit(features_matrix, target_labels.astype(np.int64), seed)
        details = []
        for disease in heldout:
            for missing in (0.0, 0.2, 0.4, 0.6):
                observations = synthetic_observations(disease, self.profiles, rng, missing=missing)
                for method in ("tfidf", "logistic", "random_forest", "xgboost", "mlp"):
                    rows = self.rank(observations, model=method, k=candidates)
                    position = next((i for i, row in enumerate(rows, 1) if row["disease_id"] == disease), None)
                    details.append({"disease": disease, "missing_rate": missing, "method": method,
                                    "rank": position or 0, "top1": int(position == 1),
                                    "top5": int(position is not None and position <= 5),
                                    "mrr": (1 / position if position else 0),
                                    "retrieved": int(position is not None)})
        summary = []
        for missing in (0.0, 0.2, 0.4, 0.6):
            for method in ("tfidf", "logistic", "random_forest", "xgboost", "mlp"):
                subset = [row for row in details if row["method"] == method and row["missing_rate"] == missing]
                summary.append({"method": method, "missing_rate": missing, "n": len(subset),
                                "top1": float(np.mean([v["top1"] for v in subset])),
                                "top5": float(np.mean([v["top5"] for v in subset])),
                                "mrr": float(np.mean([v["mrr"] for v in subset])),
                                "candidate_recall": float(np.mean([v["retrieved"] for v in subset]))})
        metadata = {"seed": seed, "train_diseases": len(training), "heldout_diseases": len(heldout),
                    "queries_per_disease": queries_per_disease, "candidates": candidates,
                    "features": FEATURES, "training_pairs": len(y),
                    "training_feature_matrix_sha256": training_input_sha256,
                    "train_disease_ids": sorted(training),
                    "heldout_disease_ids": sorted(heldout),
                    "validation_kind": "synthetic_disease_disjoint_not_patient_level",
                    "test_truth_never_forced_into_retrieval": True}
        return details, summary, metadata

    def _tfidf_for(self, observations, disease):
        terms = [term for term, status in observations if status in ("confirmed_present", "suspected_present")]
        query = self.vectorizer.transform([" ".join(t.replace(":", "_") for t in terms)])
        return float((self.matrix[self.index[disease]] @ query.T).toarray()[0, 0])

    def rank(self, observations, model="tfidf", k=40, top_k=None):
        if model not in ("tfidf", "logistic", "random_forest", "xgboost", "mlp"):
            raise ValueError("Unknown ML model: " + model)
        found = self.retrieve(observations, k=k)
        if not found:
            return []
        if model == "tfidf":
            scores = [similarity for _, similarity in found]
        else:
            if model not in self.models:
                raise ValueError("Model not trained; run python -m src.train_ml first")
            features = np.stack([self.features(observations, candidate, similarity)
                                 for candidate, similarity in found])
            scores = self.models[model].predict_proba(features)[:, 1]
        rows = [{"disease_id": candidate, "disease_name": self.labels.get(candidate, candidate),
                 "score": round(float(value), 6), "retrieval_similarity": round(similarity, 6),
                 "matched_hpo": sorted(set(term for term, status in observations
                                        if status in ("confirmed_present", "suspected_present")
                                        and term in self.profiles[candidate]))}
                for (candidate, similarity), value in zip(found, scores)]
        rows.sort(key=lambda item: (-item["score"], item["disease_id"]))
        return rows[:top_k] if top_k is not None else rows

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path, compress=3)


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
