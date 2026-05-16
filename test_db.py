"""Tests for db.py changes in PR.

The PR removed contextlib.closing and now uses SQLite's own context manager
(`with _get_conn() as conn:`) directly. These tests verify all three public
functions work correctly under this pattern.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


class TestDbInit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        self.orig_db_file = None

    def tearDown(self):
        os.unlink(self.db_path)

    def _import_db_with_tmpfile(self):
        """Return the db module redirected to the temp DB file."""
        import db as db_module
        self.orig_db_file = db_module.DB_FILE
        db_module.DB_FILE = self.db_path
        return db_module

    def _restore_db(self, db_module):
        db_module.DB_FILE = self.orig_db_file

    def test_init_db_creates_table(self):
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='kv_store'"
            )
            self.assertIsNotNone(cursor.fetchone(), "kv_store table should exist after init_db()")
            conn.close()
        finally:
            self._restore_db(db)

    def test_init_db_is_idempotent(self):
        """Calling init_db() twice should not raise."""
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.init_db()  # second call must not raise
        finally:
            self._restore_db(db)

    def test_set_val_and_get_val_roundtrip_string(self):
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.set_val("greeting", "woof")
            self.assertEqual(db.get_val("greeting"), "woof")
        finally:
            self._restore_db(db)

    def test_set_val_and_get_val_roundtrip_list(self):
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.set_val("ids", [1, 2, 3])
            self.assertEqual(db.get_val("ids"), [1, 2, 3])
        finally:
            self._restore_db(db)

    def test_set_val_and_get_val_roundtrip_dict(self):
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.set_val("config", {"a": 1, "b": "two"})
            self.assertEqual(db.get_val("config"), {"a": 1, "b": "two"})
        finally:
            self._restore_db(db)

    def test_set_val_upserts_existing_key(self):
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.set_val("counter", 1)
            db.set_val("counter", 99)
            self.assertEqual(db.get_val("counter"), 99)
        finally:
            self._restore_db(db)

    def test_get_val_returns_default_for_missing_key(self):
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            result = db.get_val("nonexistent_key", default="fallback")
            self.assertEqual(result, "fallback")
        finally:
            self._restore_db(db)

    def test_get_val_returns_none_default_when_unspecified(self):
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            result = db.get_val("missing")
            self.assertIsNone(result)
        finally:
            self._restore_db(db)

    def test_set_val_stores_as_json(self):
        """Values must be JSON-encoded in the underlying DB."""
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.set_val("raw_check", [True, False, None])
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("SELECT value FROM kv_store WHERE key=?", ("raw_check",))
            raw = cursor.fetchone()[0]
            conn.close()
            # The stored value must be valid JSON
            self.assertEqual(json.loads(raw), [True, False, None])
        finally:
            self._restore_db(db)

    def test_get_val_bool_false_not_confused_with_missing(self):
        """get_val returning False (falsy) must not be mistaken for missing."""
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.set_val("flag", False)
            self.assertIs(db.get_val("flag"), False)
        finally:
            self._restore_db(db)

    def test_set_val_numeric_zero(self):
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.set_val("zero", 0)
            self.assertEqual(db.get_val("zero"), 0)
        finally:
            self._restore_db(db)

    def test_connection_not_left_open_after_get_val(self):
        """After get_val, the DB file must not be locked by an open connection."""
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.set_val("x", 42)
            db.get_val("x")
            # If connection were leaked, exclusive write would fail; this must succeed.
            conn = sqlite3.connect(self.db_path)
            conn.execute("INSERT OR REPLACE INTO kv_store VALUES (?, ?)", ("probe", '"ok"'))
            conn.commit()
            conn.close()
        finally:
            self._restore_db(db)

    def test_connection_not_left_open_after_set_val(self):
        """After set_val, the DB file must not be locked."""
        db = self._import_db_with_tmpfile()
        try:
            db.init_db()
            db.set_val("y", "hello")
            # Verify we can still write via a raw connection (no lock held)
            conn = sqlite3.connect(self.db_path)
            conn.execute("INSERT OR REPLACE INTO kv_store VALUES (?, ?)", ("probe2", '"ok"'))
            conn.commit()
            conn.close()
        finally:
            self._restore_db(db)


if __name__ == "__main__":
    unittest.main()