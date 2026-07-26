from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "infra"
    / "terraform"
    / "functions"
    / "pre_token_generation.py"
)
SPEC = importlib.util.spec_from_file_location("pre_token_generation", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load Cognito pre-token function.")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PreTokenGenerationTests(unittest.TestCase):
    def test_organization_attribute_is_added_to_access_token(self) -> None:
        event = {
            "request": {
                "userAttributes": {
                    "custom:organization_id": "80ef391a-a90c-4218-bf03-58a4f55d819d"
                }
            },
            "response": {},
        }

        result = MODULE.handler(event, None)

        claims = result["response"]["claimsAndScopeOverrideDetails"]
        self.assertEqual(
            claims["accessTokenGeneration"]["claimsToAddOrOverride"][
                "custom:organization_id"
            ],
            "80ef391a-a90c-4218-bf03-58a4f55d819d",
        )

    def test_missing_organization_attribute_does_not_forge_claim(self) -> None:
        event = {"request": {"userAttributes": {}}, "response": {}}

        result = MODULE.handler(event, None)

        self.assertNotIn("claimsAndScopeOverrideDetails", result["response"])


if __name__ == "__main__":
    unittest.main()
