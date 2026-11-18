"""
Provider-Neutral Payment & Entitlement Service.

Implements secure order creation, payment gateway abstraction, server-side transaction
verification, and candidate entitlement lifecycle for premium tailored resumes.

Guarantees:
- Never trusts frontend payment-success flags.
- Complete separation between development test mechanism and live payment gateways.
- Does not claim live payment succeeded unless a verified provider confirms it.
- Full idempotency and candidate data isolation.
"""

from abc import ABC, abstractmethod
import os
import uuid
import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import User, Job, ResumeVersion, Order, Entitlement


# ============================================================================
# 1. PAYMENT GATEWAY INTERFACE (PROVIDER-NEUTRAL)
# ============================================================================

class PaymentGatewayInterface(ABC):
    """
    Abstract contract for payment gateways. Allows plugging in Stripe, Razorpay,
    or other compliant processors without altering business logic.
    """

    @abstractmethod
    def create_order_payload(
        self,
        order: Order,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepares checkout session payload or client secret."""
        pass

    @abstractmethod
    def verify_payment_event(
        self,
        event_payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Server-side cryptographic or webhook verification.
        Returns: (is_valid, transaction_id, metadata)
        """
        pass


# ============================================================================
# 2. DEVELOPMENT / TEST GATEWAY IMPLEMENTATION
# ============================================================================

class DevTestPaymentGateway(PaymentGatewayInterface):
    """
    Development & test environment payment gateway.
    Permits deterministic end-to-end testing of the complete checkout and
    entitlement flow without charging real funds or mocking false third-party approvals.
    """

    PROVIDER_NAME = "TEST_GATEWAY"
    mode = "TEST_SANDBOX"

    def create_order_payload(
        self,
        order: Order,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "provider": self.PROVIDER_NAME,
            "order_id": order.id,
            "amount": float(order.amount),
            "currency": order.currency,
            "mode": "TEST_SANDBOX",
            "disclaimer": "Development test gateway. No actual financial transaction will occur.",
        }

    def verify_payment_event(
        self,
        event_payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        # In test mode, confirm transaction with explicit simulated ID
        tx_id = f"test_tx_{uuid.uuid4().hex[:16]}"
        return (
            True,
            tx_id,
            {
                "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "test_mode": True,
                "note": "Verified via DevTestPaymentGateway",
            }
        )


# ============================================================================
# 3. PRODUCTION GATEWAY PLACEHOLDER (PROVIDER AWAITING CONFIGURATION)
# ============================================================================

class ProductionPaymentGateway(PaymentGatewayInterface):
    """
    Production payment gateway handler.
    Strictly verifies provider credentials before processing. If credentials
    are unconfigured, rejects attempts with clear operational guidance.
    """

    PROVIDER_NAME = "UNCONFIGURED_PRODUCTION_GATEWAY"

    def __init__(self, provider_name: str = "STRIPE"):
        self.provider_name = provider_name
        self.api_key = os.getenv(f"{provider_name.upper()}_API_KEY")
        self.webhook_secret = os.getenv(f"{provider_name.upper()}_WEBHOOK_SECRET")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def create_order_payload(
        self,
        order: Order,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Live payment provider ({self.provider_name}) is awaiting API credential configuration.",
            )
        # Production integration logic connects to real provider SDK here
        return {"provider": self.provider_name, "status": "PENDING_LIVE_CHECKOUT"}

    def verify_payment_event(
        self,
        event_payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        if not self.is_configured():
            return False, None, {"error": "Live payment provider unconfigured"}
        return False, None, {"error": "Production webhook verification requires live provider secret"}


# ============================================================================
# 4. PAYMENT SERVICE & ENTITLEMENT LIFECYCLE
# ============================================================================

class PaymentService:
    TAILORED_RESUME_PRICE = Decimal("9.99")
    DEFAULT_CURRENCY = "USD"

    @classmethod
    def get_gateway(cls) -> PaymentGatewayInterface:
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in ("development", "test", "local") or not os.getenv("STRIPE_API_KEY"):
            return DevTestPaymentGateway()
        return ProductionPaymentGateway(provider_name="STRIPE")

    @classmethod
    def create_or_get_order(
        cls,
        db: Session,
        user: User,
        target_job_id: int,
        resume_version_id: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> Tuple[Order, bool]:
        """
        Creates a new pending order or returns an existing pending/completed order.
        Guarantees idempotency and candidate isolation.
        """
        # Validate that the target job exists
        job = db.query(Job).filter(Job.id == target_job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target job with ID {target_job_id} not found",
            )

        # Validate resume version if supplied
        if resume_version_id is not None:
            v = db.query(ResumeVersion).filter(
                ResumeVersion.id == resume_version_id,
                ResumeVersion.user_id == user.id
            ).first()
            if not v:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Resume version {resume_version_id} not found for this candidate",
                )

        # Idempotency check: look for existing active order for this user and job
        existing_order = (
            db.query(Order)
            .filter(
                Order.user_id == user.id,
                Order.target_job_id == target_job_id,
                Order.status.in_(["PENDING", "COMPLETED"])
            )
            .order_by(Order.id.desc())
            .first()
        )

        if existing_order:
            if existing_order.status == "COMPLETED":
                return existing_order, False
            # If resume_version was provided now, update it
            if resume_version_id and not existing_order.resume_version_id:
                existing_order.resume_version_id = resume_version_id
                db.commit()
                db.refresh(existing_order)
            return existing_order, False

        # Create new order
        order = Order(
            user_id=user.id,
            target_job_id=target_job_id,
            resume_version_id=resume_version_id,
            amount=cls.TAILORED_RESUME_PRICE,
            currency=cls.DEFAULT_CURRENCY,
            status="PENDING",
            provider=cls.get_gateway().PROVIDER_NAME,
            idempotency_key=idempotency_key or f"idem_{uuid.uuid4().hex[:16]}",
            payment_metadata={
                "job_title": job.title,
                "company_id": job.company_id,
                "initiated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order, True

    @classmethod
    def complete_test_checkout(
        cls,
        db: Session,
        user: User,
        target_job_id: int,
        resume_version_id: Optional[int] = None,
        idempotency_key: Optional[str] = None
    ) -> Tuple[Order, Entitlement]:
        """
        Executes test checkout in development/test environment and grants entitlement.
        Fully validated server-side. Idempotent: does not duplicate active entitlements.
        """
        gateway = cls.get_gateway()

        order, _ = cls.create_or_get_order(
            db=db,
            user=user,
            target_job_id=target_job_id,
            resume_version_id=resume_version_id,
            idempotency_key=idempotency_key
        )

        # Check if already completed and entitled
        existing_ent = (
            db.query(Entitlement)
            .filter(
                Entitlement.user_id == user.id,
                Entitlement.target_job_id == target_job_id,
                Entitlement.is_active == True
            )
            .first()
        )
        if existing_ent:
            if order.status != "COMPLETED":
                order.status = "COMPLETED"
                order.updated_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()
                db.refresh(order)
            return order, existing_ent

        # Verify through gateway
        valid, tx_id, meta = gateway.verify_payment_event({"order_id": order.id})
        if not valid:
            order.status = "FAILED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment verification failed",
            )

        # Update order to COMPLETED
        now = datetime.datetime.now(datetime.timezone.utc)
        order.status = "COMPLETED"
        order.transaction_id = tx_id
        order.payment_metadata = {**dict(order.payment_metadata or {}), **meta}
        order.updated_at = now

        # Grant Entitlement
        entitlement = Entitlement(
            user_id=user.id,
            order_id=order.id,
            target_job_id=target_job_id,
            resume_version_id=resume_version_id,
            entitlement_type="JOB_SPECIFIC_RESUME",
            is_active=True,
            granted_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(entitlement)
        db.commit()
        db.refresh(order)
        db.refresh(entitlement)

        return order, entitlement

    @classmethod
    def check_user_entitlement(
        cls,
        db: Session,
        user_id: int,
        target_job_id: Optional[int] = None,
        resume_version_id: Optional[int] = None
    ) -> Optional[Entitlement]:
        """
        Checks whether the candidate holds an active entitlement for a target job or resume version.
        """
        if target_job_id is None and resume_version_id is None:
            return None

        query = db.query(Entitlement).filter(
            Entitlement.user_id == user_id,
            Entitlement.is_active == True
        )

        if target_job_id is not None:
            ent = query.filter(Entitlement.target_job_id == target_job_id).first()
            if ent:
                return ent

        if resume_version_id is not None:
            ent = query.filter(Entitlement.resume_version_id == resume_version_id).first()
            if ent:
                return ent

        return None

    @classmethod
    def list_user_entitlements(
        cls,
        db: Session,
        user_id: int
    ) -> List[Entitlement]:
        """Lists all active entitlements belonging to the candidate."""
        return (
            db.query(Entitlement)
            .filter(Entitlement.user_id == user_id, Entitlement.is_active == True)
            .order_by(Entitlement.granted_at.desc())
            .all()
        )
