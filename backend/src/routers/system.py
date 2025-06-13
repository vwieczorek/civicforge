"""
System operations router (feature flags, health checks)
"""

from fastapi import APIRouter, Depends
from typing import Dict

from ..auth import require_auth
from ..feature_flags import feature_flags

router = APIRouter(tags=["system"])


@router.get("/feature-flags", response_model=Dict[str, bool])
async def get_feature_flags(
    _: str = Depends(require_auth)
) -> Dict[str, bool]:
    """Get current feature flag status (admin/debugging endpoint)"""
    return feature_flags.get_all_flags()