"""
CLI Command Extensions
"""

import os
from unittest import TestCase
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# pylint: disable=unused-import
from asgi import app  # noqa: F401
from service.models import db  # noqa: E402
from service.common.cli_commands import db_create  # noqa: E402

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)


class TestCLI(TestCase):
    """CLI Command Tests"""

    def setUp(self):
        self.runner = CliRunner()

    @patch("service.common.cli_commands.db")
    def test_db_create(self, db_mock):
        """It should call the db-create command"""
        db_mock.return_value = MagicMock()
        with patch.dict(os.environ, {}, clear=True):
            result = self.runner.invoke(db_create)
            self.assertEqual(result.exit_code, 0)

    def test_db_create_initializes_engine(self):
        """It should build the tables when no engine exists yet"""
        db.init_engine(DATABASE_URI)
        result = self.runner.invoke(db_create)
        self.assertEqual(result.exit_code, 0)
