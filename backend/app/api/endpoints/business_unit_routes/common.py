"""Shared helpers for business unit endpoint modules."""

import logging

from app.api.utils import CRUDRouter, handle_not_found
from app.services import business_unit_service

logger = logging.getLogger(__name__)
crud = CRUDRouter()


def get_agent_service():
    """Return the shared agent service instance."""
    return business_unit_service.agent_service



def get_asset_bundle_service():
    """Return the shared asset bundle service instance."""
    return business_unit_service.asset_bundle_service
