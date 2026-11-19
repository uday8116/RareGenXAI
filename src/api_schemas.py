"""Typed contracts for the local-only research API (Pydantic v2)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Status = Literal["confirmed_present", "suspected_present", "confirmed_absent", "unknown"]
Method = Literal["overlap", "semantic", "tfidf", "logistic", "random_forest", "xgboost", "mlp"]


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hpo_id: str = Field(pattern=r"^HP:\d{7}$", description="HPO ID; known alternate IDs are canonicalized")
    status: Status


class RankRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observations: list[Observation] = Field(min_length=1, max_length=20)
    method: Method = "overlap"
    top_k: int = Field(default=5, ge=1, le=20)
    candidates: int = Field(default=40, ge=1, le=100)
    quality: bool = Field(default=True, description="Evidence weighting for ontology baselines")

    @model_validator(mode="after")
    def validate_observations(self):
        if len({o.hpo_id for o in self.observations}) != len(self.observations):
            raise ValueError("Each HPO ID may appear only once")
        if not any(o.status in ("confirmed_present", "suspected_present") for o in self.observations):
            raise ValueError("At least one present or suspected phenotype is required")
        return self


class Phenotype(BaseModel):
    hpo_id: str
    name: str
    definition: str = ""
    is_obsolete: int = 0


class PhenotypeMatch(BaseModel):
    hpo_id: str
    name: str
    is_obsolete: int = 0


class DiseaseMatch(BaseModel):
    disease_id: str
    name: str


class DiseaseAnnotation(BaseModel):
    hpo_id: str
    hpo_name: str
    is_negated: int
    frequency: str
    evidence_code: str
    reference_id: str
    onset: str
    sex: str
    modifier: str
    aspect: str
    biocuration: str


class DiseaseDetail(DiseaseMatch):
    phenotypes: list[DiseaseAnnotation]


class SourceProvenance(BaseModel):
    filename: str
    source_url: str
    sha256: str
    byte_count: int


class KnowledgeStats(BaseModel):
    counts: dict[str, int]
    schema_version: str
    sources: list[SourceProvenance]


class ModelStatus(BaseModel):
    status: Literal["available", "missing", "incompatible"]
    methods: list[str]
    model_sha256: str | None = None
    profile_sha256: str | None = None
    manifest_schema: int | None = None
    warning: str = "Research model; ranking scores are NOT disease probabilities"


class Evidence(BaseModel):
    hpo_id: str
    status: Status
    match: float | None = None
    contribution: float | None = None


class RankedDisease(BaseModel):
    disease_id: str
    disease_name: str
    score: float
    matched_hpo: list[str] = Field(default_factory=list)
    retrieval_similarity: float | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    features: dict[str, float] | None = None


class RankResponse(BaseModel):
    method: Method
    requested_count: int
    results: list[RankedDisease]
    explanation_type: Literal["per_phenotype_score_contributions", "matched_terms_and_feature_values"]
    model_sha256: str | None = None
    disclaimer: str = (
        "Research-only candidate prioritization. Scores are not calibrated "
        "disease probabilities and must not be used for diagnosis or treatment."
    )
