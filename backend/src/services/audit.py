"""
Immutable audit logging service for Indian Railways safety and compliance (tc.v1 SOTA).
Records all critical actions (device registration, defect creation, session lifecycle, media access).
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.db.models import AuditLog
from src.db.session import SessionLocal
from src.services.observability import logger, get_current_request_id


class AuditService:
    """Immutable audit trail manager for RDSO / railway safety compliance."""

    @staticmethod
    def log_sync(
        actor_type: str,
        actor_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[AuditLog]:
        """Synchronously record an audit event to the database and structured log."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            audit = AuditLog(
                actor_type=actor_type,
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(audit)
            db.commit()
            db.refresh(audit)

            logger.info(
                f"audit_event: {action}",
                extra={
                    "audit_id": audit.id,
                    "actor_type": actor_type,
                    "actor_id": actor_id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "details": details or {},
                },
            )
            return audit
        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to write audit log: {exc}", exc_info=True)
            return None
        finally:
            if close_db:
                db.close()

    @classmethod
    async def log(
        cls,
        actor_type: str,
        actor_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[AuditLog]:
        """Asynchronously record an audit event."""
        return cls.log_sync(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            db=db,
        )


audit_service = AuditService()
