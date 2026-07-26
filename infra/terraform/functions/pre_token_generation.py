from __future__ import annotations

from typing import Any


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Copy the immutable tenant attribute into the signed access token."""
    user_attributes = event.get("request", {}).get("userAttributes", {})
    organization_id = user_attributes.get("custom:organization_id")
    if not organization_id:
        return event

    response = event.setdefault("response", {})
    response["claimsAndScopeOverrideDetails"] = {
        "accessTokenGeneration": {
            "claimsToAddOrOverride": {
                "custom:organization_id": organization_id,
            }
        }
    }
    return event
