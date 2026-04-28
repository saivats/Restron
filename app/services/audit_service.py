from sqlalchemy.orm import Session

from app.models import models


def write_audit_log(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | str | None,
    restaurant_id: int | None,
    user: models.User | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> None:
    db.add(
        models.AuditLog(
            restaurant_id=restaurant_id,
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            before_state=before_state,
            after_state=after_state,
        )
    )
