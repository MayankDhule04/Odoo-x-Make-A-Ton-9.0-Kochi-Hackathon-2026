"""Subscription endpoints (Member 2): quotations, subscriptions, lifecycle transitions,
proration and the discount simulator."""

from fastapi import APIRouter

router = APIRouter(tags=["subscriptions"])
