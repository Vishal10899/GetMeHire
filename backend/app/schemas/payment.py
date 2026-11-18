from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal

class CheckoutRequest(BaseModel):
    target_job_id: int
    resume_version_id: Optional[int] = None
    idempotency_key: Optional[str] = None

class OrderResponse(BaseModel):
    id: int
    user_id: int
    target_job_id: Optional[int] = None
    resume_version_id: Optional[int] = None
    amount: float
    currency: str
    status: str
    provider: str
    transaction_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EntitlementResponse(BaseModel):
    id: int
    user_id: int
    order_id: Optional[int] = None
    target_job_id: Optional[int] = None
    resume_version_id: Optional[int] = None
    entitlement_type: str
    is_active: bool
    granted_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CheckoutResponse(BaseModel):
    order: OrderResponse
    entitlement: Optional[EntitlementResponse] = None
    message: str
    is_unlocked: bool = True

class EntitlementCheckResponse(BaseModel):
    is_entitled: bool
    has_entitlement: bool = False
    entitlement: Optional[EntitlementResponse] = None
    target_job_id: Optional[int] = None
    message: str
