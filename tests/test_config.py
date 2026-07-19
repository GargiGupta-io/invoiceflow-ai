from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import make_url

from app.config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_describe_local_postgresql_runtime(self) -> None:
        settings = Settings(_env_file=None)

        self.assertEqual(settings.app_env, "development")
        self.assertEqual(settings.database_pool_size, 5)
        self.assertEqual(settings.database_max_overflow, 5)
        self.assertTrue(settings.sqlalchemy_database_url.startswith("postgresql+psycopg://"))

    def test_environment_values_override_defaults(self) -> None:
        environment = {
            "APP_ENV": "test",
            "DATABASE_URL": "postgresql+psycopg://test_user:test_password@db:5432/test_db",
            "DATABASE_POOL_SIZE": "8",
            "DATABASE_ECHO": "true",
        }

        with patch.dict("os.environ", environment, clear=False):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.app_env, "test")
        self.assertEqual(settings.database_pool_size, 8)
        self.assertTrue(settings.database_echo)
        self.assertIn("test_db", settings.sqlalchemy_database_url)

    def test_managed_database_secret_builds_url_from_components(self) -> None:
        settings = Settings(
            _env_file=None,
            database_url="",
            database_host="private-db.internal",
            database_port=5432,
            database_name="invoiceflow",
            database_user="invoiceflow_app",
            database_password="p@ss word/with:symbols",
        )

        url = make_url(settings.sqlalchemy_database_url)
        self.assertEqual(url.drivername, "postgresql+psycopg")
        self.assertEqual(url.username, "invoiceflow_app")
        self.assertEqual(url.password, "p@ss word/with:symbols")
        self.assertEqual(url.host, "private-db.internal")
        self.assertEqual(url.port, 5432)
        self.assertEqual(url.database, "invoiceflow")

    def test_partial_database_components_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                database_url="",
                database_host="private-db.internal",
                database_name="invoiceflow",
            )

    def test_sensitive_values_are_masked_in_settings_representation(self) -> None:
        settings = Settings(
            _env_file=None,
            database_url="postgresql+psycopg://private_user:private_password@db:5432/invoiceflow",
            database_password="private-component-password",
            openai_api_key="private-api-key",
        )

        representation = repr(settings)
        self.assertNotIn("private_password", representation)
        self.assertNotIn("private-component-password", representation)
        self.assertNotIn("private-api-key", representation)
        self.assertIn("**********", representation)

    def test_invalid_pool_size_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, database_pool_size=0)

    def test_browser_auth_configuration_requires_complete_https_settings(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, auth_browser_domain="https://login.example.com")

        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                auth_issuer="https://issuer.example.com/pool",
                auth_client_id="browser-client",
                auth_browser_domain="http://login.example.com",
                auth_redirect_uri="https://app.example.com/reviewer/callback",
                auth_logout_uri="https://app.example.com/reviewer/",
            )

    def test_browser_auth_allows_https_and_local_development_callbacks(self) -> None:
        production = Settings(
            _env_file=None,
            auth_issuer="https://issuer.example.com/pool",
            auth_client_id="browser-client",
            auth_browser_domain="https://login.example.com",
            auth_redirect_uri="https://app.example.com/reviewer/callback",
            auth_logout_uri="https://app.example.com/reviewer/",
        )
        local = Settings(
            _env_file=None,
            auth_issuer="https://issuer.example.com/pool",
            auth_client_id="browser-client",
            auth_browser_domain="https://login.example.com",
            auth_redirect_uri="http://localhost:5173/reviewer/callback",
            auth_logout_uri="http://127.0.0.1:5173/reviewer/",
        )

        self.assertTrue(production.auth_browser_configured)
        self.assertTrue(local.auth_browser_configured)

    def test_presigned_url_lifetime_is_capped_at_five_minutes(self) -> None:
        self.assertEqual(Settings(_env_file=None).s3_presigned_url_ttl_seconds, 300)
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, s3_presigned_url_ttl_seconds=301)

    def test_sqs_configuration_requires_a_queue_url(self) -> None:
        self.assertFalse(Settings(_env_file=None).sqs_configured)
        self.assertTrue(
            Settings(
                _env_file=None,
                sqs_queue_url="https://sqs.ap-south-1.amazonaws.com/123456789012/invoiceflow",
            ).sqs_configured
        )

    def test_worker_queue_timings_are_bounded(self) -> None:
        settings = Settings(_env_file=None)
        self.assertEqual(settings.sqs_wait_time_seconds, 20)
        self.assertEqual(settings.sqs_visibility_timeout_seconds, 120)
        self.assertEqual(settings.sqs_visibility_heartbeat_seconds, 30)
        self.assertEqual(settings.sqs_retry_base_delay_seconds, 30)
        self.assertEqual(settings.sqs_retry_max_delay_seconds, 900)
        self.assertEqual(settings.sqs_redrive_max_receive_count, 4)
        self.assertEqual(settings.worker_stale_job_seconds, 3600)
        self.assertEqual(settings.worker_extractor_mode, "heuristic")
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, sqs_wait_time_seconds=21)
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, sqs_visibility_timeout_seconds=29)

    def test_worker_retry_settings_reject_unsafe_relationships(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                sqs_visibility_timeout_seconds=120,
                sqs_visibility_heartbeat_seconds=120,
            )
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                sqs_retry_base_delay_seconds=901,
                sqs_retry_max_delay_seconds=900,
            )
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                sqs_visibility_timeout_seconds=120,
                worker_stale_job_seconds=120,
            )

    def test_retention_settings_are_bounded(self) -> None:
        settings = Settings(_env_file=None)
        self.assertEqual(settings.document_retention_days, 90)
        self.assertEqual(settings.retention_delete_batch_size, 100)
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, document_retention_days=0)
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, retention_delete_batch_size=1001)


if __name__ == "__main__":
    unittest.main()
