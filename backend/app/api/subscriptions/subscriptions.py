"""Subscription endpoints: create (incl. from a template), edit, read, lifecycle
transitions and the history timeline.

Reads are scoped: customers see only their own subscriptions. Lifecycle actions are
staff/admin here; customer self-service lives in the portal (Member 4).
"""

from collections.abc import Callable

from fastapi import APIRouter, HTTPException, status

from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import CurrentPrincipal, Principal, StaffOrAdmin
from app.models.auth import User
from app.models.subscriptions import Subscription
from app.schemas.subscriptions import (
    GenericTransitionRequest,
    SubscriptionCreate,
    SubscriptionDetail,
    SubscriptionFromTemplate,
    SubscriptionHistoryRead,
    SubscriptionRead,
    SubscriptionUpdate,
    TransitionRequest,
)
from app.services import subscriptions as sub_service
from app.services.subscriptions import SubscriptionLookupError, TransitionError

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _visible_or_404(db: DbSession, subscription_id: int, principal: Principal) -> Subscription:
    sub = sub_service.get_subscription(db, subscription_id)
    if sub is None or (principal.is_customer and sub.customer_id != principal.customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    return sub


@router.post("", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(body: SubscriptionCreate, db: DbSession, user: StaffOrAdmin) -> Subscription:
    try:
        sub = sub_service.create_subscription(db, body, actor=user)
    except SubscriptionLookupError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/from-template", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_from_template(body: SubscriptionFromTemplate, db: DbSession, user: StaffOrAdmin) -> Subscription:
    try:
        sub = sub_service.create_from_template(db, body, actor=user)
    except SubscriptionLookupError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(sub)
    return sub


@router.get("", response_model=Page[SubscriptionRead])
def list_subscriptions(db: DbSession, params: PaginationDep, principal: CurrentPrincipal) -> Page[SubscriptionRead]:
    query = principal.scope(sub_service.list_subscriptions(db), Subscription.customer_id)
    return paginate(db, query, params)


@router.get("/{subscription_id}", response_model=SubscriptionDetail)
def get_subscription(subscription_id: int, db: DbSession, principal: CurrentPrincipal) -> Subscription:
    return _visible_or_404(db, subscription_id, principal)


@router.patch("/{subscription_id}", response_model=SubscriptionRead)
def update_subscription(subscription_id: int, body: SubscriptionUpdate, db: DbSession, user: StaffOrAdmin) -> Subscription:
    sub = sub_service.get_subscription(db, subscription_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    try:
        sub = sub_service.update_subscription(db, sub, body, actor=user)
    except TransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SubscriptionLookupError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/{subscription_id}/history", response_model=Page[SubscriptionHistoryRead])
def subscription_history(
    subscription_id: int, db: DbSession, params: PaginationDep, principal: CurrentPrincipal
) -> Page[SubscriptionHistoryRead]:
    _visible_or_404(db, subscription_id, principal)
    return paginate(db, sub_service.history_query(db, subscription_id), params)


# --- Lifecycle actions ---------------------------------------------------------------

def _run_action(
    action: Callable[..., Subscription],
    subscription_id: int,
    body: TransitionRequest,
    db: DbSession,
    user: User,
) -> Subscription:
    sub = sub_service.get_subscription(db, subscription_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    try:
        sub = action(db, sub, actor=user, note=body.note)
    except TransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/{subscription_id}/submit", response_model=SubscriptionRead)
def submit(subscription_id: int, db: DbSession, user: StaffOrAdmin, body: TransitionRequest = TransitionRequest()):
    return _run_action(sub_service.submit, subscription_id, body, db, user)


@router.post("/{subscription_id}/confirm", response_model=SubscriptionRead)
def confirm(subscription_id: int, db: DbSession, user: StaffOrAdmin, body: TransitionRequest = TransitionRequest()):
    return _run_action(sub_service.confirm, subscription_id, body, db, user)


@router.post("/{subscription_id}/activate", response_model=SubscriptionRead)
def activate(subscription_id: int, db: DbSession, user: StaffOrAdmin, body: TransitionRequest = TransitionRequest()):
    return _run_action(sub_service.activate, subscription_id, body, db, user)


@router.post("/{subscription_id}/pause", response_model=SubscriptionRead)
def pause(subscription_id: int, db: DbSession, user: StaffOrAdmin, body: TransitionRequest = TransitionRequest()):
    return _run_action(sub_service.pause, subscription_id, body, db, user)


@router.post("/{subscription_id}/resume", response_model=SubscriptionRead)
def resume(subscription_id: int, db: DbSession, user: StaffOrAdmin, body: TransitionRequest = TransitionRequest()):
    return _run_action(sub_service.resume, subscription_id, body, db, user)


@router.post("/{subscription_id}/close", response_model=SubscriptionRead)
def close(subscription_id: int, db: DbSession, user: StaffOrAdmin, body: TransitionRequest = TransitionRequest()):
    return _run_action(sub_service.close, subscription_id, body, db, user)


@router.post("/{subscription_id}/renew", response_model=SubscriptionRead)
def renew(subscription_id: int, db: DbSession, user: StaffOrAdmin, body: TransitionRequest = TransitionRequest()):
    return _run_action(sub_service.renew, subscription_id, body, db, user)


@router.post("/{subscription_id}/transition", response_model=SubscriptionRead)
def transition(subscription_id: int, body: GenericTransitionRequest, db: DbSession, user: StaffOrAdmin) -> Subscription:
    sub = sub_service.get_subscription(db, subscription_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    try:
        sub = sub_service.transition(db, sub, body.to_status, actor=user, note=body.note)
    except TransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(sub)
    return sub
