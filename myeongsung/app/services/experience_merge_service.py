import json
import math
import os
import re
from difflib import SequenceMatcher
from typing import Any, Iterable, List, Optional, Sequence
from pydantic import BaseModel

from app.schemas.resume_dto import (
    MergeCandidate,
    MergeCheckResponse,
    MergeCheckResult,
    MergeExperiencePayload,
    Step2ExtractedExperience,
)


DEFAULT_MERGE_THRESHOLD = 0.86
LOW_CONFIDENCE_MERGE_THRESHOLD = 0.75
NAME_SIMILARITY_THRESHOLD = 0.9
KEY_FIELD_MATCH_THRESHOLD = 2
URL_PATTERN = re.compile(r"https?://[^\s\])}>\"']+")
SPEC_TYPES = {"어학", "자격증", "수상", "수강과목", "교육 이수", "LANGUAGE", "LICENSE", "AWARD", "COURSE", "EDUCATION"}
SPEC_FIELD_KEYS = {
    "어학": ("exam_name", "score", "exam_date", "expiration_date"),
    "LANGUAGE": ("exam_name", "score", "exam_date", "expiration_date"),
    "자격증": ("certificate_name", "organization", "acquisition_date", "expiration_date"),
    "LICENSE": ("certificate_name", "organization", "acquisition_date", "expiration_date"),
    "수상": ("award_name", "organization", "award_date", "award_grade"),
    "AWARD": ("award_name", "organization", "award_date", "award_grade"),
    "수강과목": ("course_name", "semester", "credit", "grade", "major"),
    "COURSE": ("course_name", "semester", "credit", "grade", "major"),
    "교육 이수": ("education_name", "organization", "period", "completion_status"),
    "EDUCATION": ("education_name", "organization", "period", "completion_status"),
}
NARRATIVE_KEY_FIELDS = (
    "project_name",
    "activity_name",
    "competition_name",
    "organization",
    "period",
    "role",
)


def _merge_threshold(threshold: Optional[float] = None) -> float:
    if threshold is not None:
        return threshold
    raw_value = os.getenv("MERGE_SIMILARITY_THRESHOLD")
    if not raw_value:
        return DEFAULT_MERGE_THRESHOLD
    try:
        return float(raw_value)
    except ValueError:
        return DEFAULT_MERGE_THRESHOLD


def _embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def _as_dict(value: Any) -> dict:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {}


def _compact_json(value: Any) -> str:
    if value is None or value == {} or value == []:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[\s_\-·./()]+", "", str(value).casefold())


def _text_similarity(left: Any, right: Any) -> float:
    left_value = _normalize_text(left)
    right_value = _normalize_text(right)
    if not left_value or not right_value:
        return 0.0
    return SequenceMatcher(None, left_value, right_value).ratio()


def _first_present(data: dict, keys: Iterable[str]) -> str:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _experience_type(data: dict) -> str:
    return _first_present(data, ("experience_type", "experienceType"))


def _experience_group(data: dict) -> str:
    return _first_present(data, ("experience_group", "experienceGroup"))


def _is_spec_experience(data: dict) -> bool:
    group = _experience_group(data).replace(" ", "")
    experience_type = _experience_type(data)
    return group in {"스펙·증빙형", "스펙증빙형", "SPEC"} or experience_type in SPEC_TYPES


def _structured_info(data: dict) -> dict:
    info = {}
    attributes = data.get("attributes")
    if isinstance(attributes, dict):
        info.update(attributes)
    basic_info = data.get("basic_info") or data.get("basicInfo")
    if isinstance(basic_info, dict):
        info.update(basic_info)
    return info


def _all_text_values(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values = []
        for child in value.values():
            values.extend(_all_text_values(child))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(_all_text_values(child))
        return values
    return [str(value)]


def _extract_urls(data: dict) -> set[str]:
    values = [
        _first_present(data, ("document_content", "experience_content", "documentContent", "experienceContent")),
        *_all_text_values(_structured_info(data)),
        *_all_text_values(data.get("related_links")),
        *_all_text_values(data.get("links")),
    ]
    urls = set()
    for value in values:
        urls.update(URL_PATTERN.findall(value))
    return {url.rstrip(".,") for url in urls}


def _structured_parts(info: dict, keys: Iterable[str]) -> List[str]:
    parts = []
    for key in keys:
        value = info.get(key)
        if value is not None and str(value).strip():
            parts.append(f"{key}: {str(value).strip()}")
    return parts


def _spec_embedding_text(data: dict) -> str:
    title = _first_present(data, ("title", "experience_name"))
    experience_type = _experience_type(data)
    info = _structured_info(data)
    field_keys = SPEC_FIELD_KEYS.get(experience_type, ())
    structured_parts = _structured_parts(info, field_keys)
    fallback_body = _first_present(data, ("document_content", "experience_content", "documentContent", "experienceContent"))

    identity = [
        title,
        experience_type,
        *structured_parts,
    ]
    if not structured_parts and fallback_body:
        identity.append(fallback_body)

    weighted_identity = [part for part in identity if part]
    primary_identity = weighted_identity[:2]
    return "\n".join([*primary_identity, *weighted_identity])


def _narrative_embedding_text(data: dict) -> str:
    title = _first_present(data, ("title", "experience_name"))
    body = _first_present(data, ("document_content", "experience_content", "documentContent", "experienceContent"))
    keywords = data.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = [str(keywords)]

    parts = [
        title,
        _experience_group(data),
        _experience_type(data),
        " ".join(str(keyword) for keyword in keywords if str(keyword).strip()),
        _compact_json(_structured_info(data)),
        body,
    ]
    return "\n".join(part for part in parts if part)


def build_embedding_text(experience: Any) -> str:
    data = _as_dict(experience)
    if _is_spec_experience(data):
        return _spec_embedding_text(data)
    return _narrative_embedding_text(data)


def _embedding_client() -> Any:
    from openai import OpenAI

    return OpenAI(api_key=os.getenv("OPENAI_API_KEY") or None)


def _embed_texts(texts: Sequence[str], client: Optional[Any] = None) -> List[List[float]]:
    if not texts:
        return []
    openai_client = client or _embedding_client()
    response = openai_client.embeddings.create(model=_embedding_model(), input=list(texts))
    return [item.embedding for item in response.data]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _payload_title(experience: Any) -> Optional[str]:
    data = _as_dict(experience)
    return _first_present(data, ("title", "experience_name")) or None


def _payload_id(experience: Any) -> Optional[str]:
    data = _as_dict(experience)
    value = data.get("id")
    return str(value) if value is not None else None


def _candidate_from_payload(experience: Any, similarity: float) -> MergeCandidate:
    data = _as_dict(experience)
    return MergeCandidate(
        id=_payload_id(data),
        title=_payload_title(data),
        experience_group=_first_present(data, ("experience_group", "experienceGroup")) or None,
        experience_type=_first_present(data, ("experience_type", "experienceType")) or None,
        similarity=similarity,
    )


def _title_similarity(target_data: dict, candidate_data: dict) -> float:
    return _text_similarity(_payload_title(target_data), _payload_title(candidate_data))


def _same_url_exists(target_data: dict, candidate_data: dict) -> bool:
    target_urls = _extract_urls(target_data)
    candidate_urls = _extract_urls(candidate_data)
    return bool(target_urls and candidate_urls and target_urls.intersection(candidate_urls))


def _field_matches(target_data: dict, candidate_data: dict, fields: Iterable[str]) -> int:
    target_info = _structured_info(target_data)
    candidate_info = _structured_info(candidate_data)
    matches = 0
    for field in fields:
        target_value = target_info.get(field)
        candidate_value = candidate_info.get(field)
        if target_value is None or candidate_value is None:
            continue
        if _text_similarity(target_value, candidate_value) >= 0.85:
            matches += 1
    return matches


def _spec_field_matches(target_data: dict, candidate_data: dict) -> int:
    experience_type = _experience_type(target_data) or _experience_type(candidate_data)
    return _field_matches(target_data, candidate_data, SPEC_FIELD_KEYS.get(experience_type, ()))


def _narrative_field_matches(target_data: dict, candidate_data: dict) -> int:
    return _field_matches(target_data, candidate_data, NARRATIVE_KEY_FIELDS)


def _rule_based_merge(target: Any, candidate: Any, similarity: float, threshold: float) -> bool:
    target_data = _as_dict(target)
    candidate_data = _as_dict(candidate)

    if similarity >= threshold:
        return True
    if _same_url_exists(target_data, candidate_data):
        return True

    title_similarity = _title_similarity(target_data, candidate_data)
    if _is_spec_experience(target_data):
        return title_similarity >= NAME_SIMILARITY_THRESHOLD and _spec_field_matches(target_data, candidate_data) >= 1

    narrative_matches = _narrative_field_matches(target_data, candidate_data)
    if title_similarity >= NAME_SIMILARITY_THRESHOLD and narrative_matches >= 1:
        return True
    return similarity >= LOW_CONFIDENCE_MERGE_THRESHOLD and narrative_matches >= KEY_FIELD_MATCH_THRESHOLD


def _is_comparable(target: Any, candidate: Any) -> bool:
    target_data = _as_dict(target)
    candidate_data = _as_dict(candidate)
    target_is_spec = _is_spec_experience(target_data)
    candidate_is_spec = _is_spec_experience(candidate_data)

    if target_is_spec != candidate_is_spec:
        return False
    if target_is_spec and candidate_is_spec:
        target_type = _experience_type(target_data)
        candidate_type = _experience_type(candidate_data)
        return not target_type or not candidate_type or target_type == candidate_type
    return True


def _empty_result(target: Any, index: int) -> MergeCheckResult:
    return MergeCheckResult(
        target_index=index,
        target_id=_payload_id(target),
        needs_merge=False,
        merge_candidate_id=None,
        similarity=None,
        candidate=None,
    )


def check_merge_candidates(
    targets: List[Any],
    existing_experiences: List[Any],
    threshold: Optional[float] = None,
    top_k: int = 1,
    embedding_client: Optional[Any] = None,
) -> MergeCheckResponse:
    effective_threshold = _merge_threshold(threshold)

    if not targets:
        return MergeCheckResponse(results=[])
    if not existing_experiences:
        return MergeCheckResponse(results=[_empty_result(target, index) for index, target in enumerate(targets)])

    target_texts = [build_embedding_text(target) for target in targets]
    existing_texts = [build_embedding_text(experience) for experience in existing_experiences]
    embeddings = _embed_texts([*target_texts, *existing_texts], client=embedding_client)
    target_embeddings = embeddings[: len(targets)]
    existing_embeddings = embeddings[len(targets):]

    results: List[MergeCheckResult] = []
    for target_index, target_embedding in enumerate(target_embeddings):
        scored_candidates = [
            (_cosine_similarity(target_embedding, existing_embedding), existing_experiences[existing_index])
            for existing_index, existing_embedding in enumerate(existing_embeddings)
            if _is_comparable(targets[target_index], existing_experiences[existing_index])
        ]
        if not scored_candidates:
            results.append(_empty_result(targets[target_index], target_index))
            continue
        scored_candidates.sort(key=lambda item: item[0], reverse=True)
        best_similarity, best_candidate = scored_candidates[0]
        needs_merge = _rule_based_merge(
            targets[target_index],
            best_candidate,
            best_similarity,
            effective_threshold,
        )
        candidate = _candidate_from_payload(best_candidate, best_similarity) if needs_merge else None
        results.append(
            MergeCheckResult(
                target_index=target_index,
                target_id=_payload_id(targets[target_index]),
                needs_merge=needs_merge,
                merge_candidate_id=candidate.id if candidate else None,
                similarity=best_similarity,
                candidate=candidate,
            )
        )

    return MergeCheckResponse(results=results)


def apply_merge_results_to_step2(
    step2_experiences: List[Step2ExtractedExperience],
    existing_experiences: List[MergeExperiencePayload],
    threshold: Optional[float] = None,
) -> List[Step2ExtractedExperience]:
    if not step2_experiences or not existing_experiences:
        return step2_experiences

    merge_response = check_merge_candidates(
        targets=step2_experiences,
        existing_experiences=existing_experiences,
        threshold=threshold,
        top_k=1,
    )
    results_by_index = {result.target_index: result for result in merge_response.results}
    for index, experience in enumerate(step2_experiences):
        result = results_by_index.get(index)
        if not result:
            continue
        experience.needs_merge = result.needs_merge
        experience.merge_candidate_id = result.merge_candidate_id
        experience.merge_similarity = result.similarity

    return step2_experiences


def apply_sequential_merge_results_to_step2(
    step2_experiences: List[dict],
    existing_experiences: List[MergeExperiencePayload],
    threshold: Optional[float] = None,
    embedding_client: Optional[Any] = None,
) -> List[dict]:
    accepted_candidates: List[Any] = list(existing_experiences)

    for index, experience in enumerate(step2_experiences):
        merge_response = check_merge_candidates(
            targets=[experience],
            existing_experiences=accepted_candidates,
            threshold=threshold,
            top_k=1,
            embedding_client=embedding_client,
        )
        result = merge_response.results[0]
        experience["needs_merge"] = result.needs_merge
        experience["merge_candidate_id"] = result.merge_candidate_id
        experience["merge_similarity"] = result.similarity

        if not result.needs_merge:
            accepted_candidate = dict(experience)
            accepted_candidate["id"] = f"batch:{index}"
            accepted_candidates.append(accepted_candidate)

    return step2_experiences
