# Idempotent request deduplication service (tc.v1 SOTA).

import json
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from src.db.models import IngestionKey


def check_idempotency(
    db: Session,
    idempotency_key: Optional[str],
    entity_type: str,
) -> Optional[Dict[str, Any]]:
    """Check if an idempotency key was previously processed and return cached response if found."""
    if not idempotency_key:
        return None

    record = (
        db.query(IngestionKey)
        .filter(
            IngestionKey.idempotency_key == idempotency_key,
            IngestionKey.entity_type == entity_type,
        )
        .first()
    )
    if record and record.response_payload:
        return record.response_payload
    return None


def record_idempotency(
    db: Session,
    idempotency_key: Optional[str],
    entity_type: str,
    entity_id: Optional[str],
    response_payload: Dict[str, Any],
):
    """Store idempotency key and response payload after successful insertion."""
    if not idempotency_key:
        return

    try:
        key_record = IngestionKey(
            idempotency_key=idempotency_key,
            entity_type=entity_type,
            entity_id=entity_id,
            response_payload=response_payload,
        )
        db.add(key_record)
        db.commit()
    except Exception:
        db.rollback()
