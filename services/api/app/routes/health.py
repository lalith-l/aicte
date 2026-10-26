"""Health check (public). Dashboard footer reads published head hash from here."""

from fastapi import APIRouter

from packages.audit.chain import list_published_heads

router = APIRouter()


@router.get("/health")
def health():
    heads = list_published_heads()
    latest = heads[-1] if heads else None
    return {
        "status": "ok",
        "synthetic_data": True,
        "label": "AICTE Validation Prototype — all data is synthetic",
        "sandbox": "OS-level sandbox, reduced isolation",
        "published_head": latest,
    }
