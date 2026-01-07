
import pytest
from unittest.mock import MagicMock, patch
from src.core.audit_logger import AuditLogger
from src.data.repositories.generic_repository import GenericRepository

def test_audit_unification_verification():
    """
    VERIFY: System now supports unifying batches by injecting the same ID.
    """
    mock_conn = MagicMock()
    batch_id = "my-shared-batch"
    
    a1 = AuditLogger(mock_conn, batch_id=batch_id)
    a2 = AuditLogger(mock_conn, batch_id=batch_id)
    
    assert a1.batch_id == a2.batch_id
    assert a1.batch_id == "my-shared-batch"

def test_generic_repo_batch_id_support():
    """
    VERIFY: GenericRepository now accepts and uses batch_id.
    """
    class TestRepo(GenericRepository):
        def get_by_id(self, rid): return MagicMock()
        def _insert_db(self, c, e, **k): return 1
        def _update_db(self, c, e, **k): pass
        def _delete_db(self, c, rid, **k): pass

    repo = TestRepo(table_name="Test", id_attr="id")
    entity = MagicMock()
    entity.id = 1
    entity.to_dict.return_value = {"val": 1}
    
    # This should no longer raise TypeError
    repo.update(entity, batch_id="my-custom-batch")
