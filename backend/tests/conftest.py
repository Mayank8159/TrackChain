# Global pytest fixtures and environment configuration for TrackChain test suite.

import os
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-testing-purposes-only-32bytes"
