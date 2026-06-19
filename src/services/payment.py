"""
Unified Payment Service for idx-trading-bot.
Provider priority: Scalev → Midtrans (fallback).
"""
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Tier pricing (in IDR)
TIER_PRICES = {
    "pro": 79900,
    "premium": 149900,
    "lifetime": 1999900,
    "whitelabel": 5000000,
}

TIER_LABELS = {
    "pro": "💎 Pro (Rp79.900/bln)",
    "premium": "👑 Premium (Rp149.900/bln)",
    "lifetime": "🌟 Lifetime (Rp1.999.900)",
    "whitelabel": "🏢 White-label (Rp5jt + Rp500rb/bln)",
}

# Provider env check
SCALEV_CLIENT_ID = os.environ.get("SCALEV_CLIENT_ID", "")
SCALEV_SIGNING_SECRET = os.environ.get("SCALEV_SIGNING_SECRET", "")
MIDTRANS_SERVER_KEY = os.environ.get("MIDTRANS_SERVER_KEY", "")
MIDTRANS_MERCHANT_ID = os.environ.get("MIDTRANS_MERCHANT_ID", "")

def _is_scalev_configured() -> bool:
    return bool(SCALEV_CLIENT_ID and SCALEV_SIGNING_SECRET)

def _is_midtrans_configured() -> bool:
    return bool(MIDTRANS_SERVER_KEY and MIDTRANS_MERCHANT_ID)

def get_available_providers() -> list[str]:
    """Returns list of configured payment providers."""
    providers = []
    if _is_scalev_configured():
        providers.append("scalev")
    if _is_midtrans_configured():
        providers.append("midtrans")
    return providers

def create_payment(
    tier: str,
    user_id: int,
    username: str = "",
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create payment transaction with automatic provider fallback.
    
    Args:
        tier: pro/premium/lifetime/whitelabel
        user_id: Telegram user ID
        username: Telegram username for reference
        provider: Force specific provider (scalev/midtrans), or None for auto
    
    Returns:
        {
            "checkout_url": str,
            "reference": str,
            "amount": int,
            "method": str (scalev/midtrans),
        }
    
    Raises:
        ValueError: Invalid tier
        RuntimeError: No payment provider configured
    """
    if tier not in TIER_PRICES:
        raise ValueError(f"Invalid tier: {tier}")
    
    amount = TIER_PRICES[tier]
    available = get_available_providers()
    
    if not available:
        raise RuntimeError("No payment provider configured (Scalev/Midtrans)")
    
    # Provider selection logic
    if provider:
        if provider not in available:
            logger.warning(f"Requested provider {provider} not configured, using fallback")
            provider = available[0]
    else:
        provider = available[0]  # Scalev first if configured
    
    # Dispatch to provider
    if provider == "scalev":
        return _create_scalev_payment(tier, user_id, username, amount)
    elif provider == "midtrans":
        return _create_midtrans_payment(tier, user_id, username, amount)
    else:
        raise RuntimeError(f"Unknown provider: {provider}")

def _create_scalev_payment(tier: str, user_id: int, username: str, amount: int) -> Dict[str, Any]:
    from src.services.scalev import build_purchase_link
    
    link = build_purchase_link(
        tier=tier,
        user_id=user_id,
        source="telegram",
        note=username or f"user_{user_id}",
    )
    
    return {
        "checkout_url": link["purchase_url"],
        "reference": link.get("reference", f"scalev_{user_id}_{tier}"),
        "amount": amount,
        "method": "scalev",
    }

def _create_midtrans_payment(tier: str, user_id: int, username: str, amount: int) -> Dict[str, Any]:
    from src.services.midtrans import create_snap_transaction
    import time
    
    order_id = f"IDX-{tier.upper()}-{user_id}-{int(time.time())}"
    user_data = {
        "user_id": user_id,
        "tier": tier,
        "username": username or f"user_{user_id}",
    }
    
    snap_token = create_snap_transaction(
        order_id=order_id,
        tier=tier,
        amount=amount,
        user_data=user_data,
    )
    
    # Midtrans Snap URL
    is_production = os.environ.get("MIDTRANS_IS_PRODUCTION", "false").lower() == "true"
    base_url = "https://app.midtrans.com/snap/v2/vtweb" if is_production else "https://app.sandbox.midtrans.com/snap/v2/vtweb"
    
    return {
        "checkout_url": f"{base_url}/{snap_token}",
        "reference": order_id,
        "amount": amount,
        "method": "midtrans",
    }
