"""Write audit entries.  Every member calls this for changes to prices, plans,
discounts and record states.

Usage:
    from app.services.audit import record_audit

    record_audit(db, actor=user, entity_type="plan", entity_id=plan.id,
                 action="update", changes='{"price": ["500.00", "600.00"]}')
"""

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.auth.audit_log import AuditLog
from app.models.auth.user import User


def record_audit(
    db: Session,
    *,
    actor: User | None,
    entity_type: str,
    entity_id: int,
    action: str,
    changes: dict[str, Any] | str | None = None,
) -> AuditLog:
    """Append an immutable audit entry.  Flushes but does not commit."""
    if isinstance(changes, dict):
        changes = json.dumps(changes, default=str)
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=changes,
    )
    db.add(entry)
    db.flush()
    return entry
