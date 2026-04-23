import os
import tempfile
from src.services.edit_service import EditService
from src.services.catalog_service import CatalogService
from src.data.staging_repository import StagingRepository

class TestDeleteOriginalSource:
    def test_valid_id_and_existing_file_deletes_and_clears(self, populated_db):
        """When the file exists on disk, it is deleted and the origin mapping is cleared."""
        # Setup real file
        fd, temp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        assert os.path.exists(temp_path)

        # Setup mapping
        repo = StagingRepository(populated_db)
        repo.set_origin(1, temp_path)

        # Instantiate service (using EditService directly for unit testing)
        service = EditService(populated_db, None)

        # Execute
        result = service.delete_original_source(1)

        # Assert
        assert result is True, "Expected delete_original_source to return True on success"
        assert not os.path.exists(temp_path), "Expected file to be deleted from disk"
        assert repo.get_origin(1) is None, "Expected origin mapping to be cleared"

    def test_valid_id_missing_file_clears_origin(self, populated_db):
        """When the file is already gone from disk, the method returns False but still clears the mapping."""
        temp_path = "/fake/does_not_exist_xyz.mp3"
        repo = StagingRepository(populated_db)
        repo.set_origin(2, temp_path)

        service = EditService(populated_db, None)

        result = service.delete_original_source(2)

        assert result is False, "Expected False because file was missing"
        assert repo.get_origin(2) is None, "Expected origin mapping to be cleared anyway"

    def test_missing_origin_returns_false(self, empty_db):
        """When there is no origin mapping for the song, returns False safely."""
        service = EditService(empty_db, None)
        result = service.delete_original_source(777)
        assert result is False


class TestStagingCleanupCatalogPassthrough:
    def test_delete_original_source_passthrough(self, populated_db):
        """CatalogService.delete_original_source delegates to EditService."""
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        repo = StagingRepository(populated_db)
        repo.set_origin(3, temp_path)

        service = CatalogService(populated_db)
        result = service.delete_original_source(3)

        assert result is True
        assert not os.path.exists(temp_path)
        assert repo.get_origin(3) is None

    def test_get_staging_origin_passthrough(self, populated_db):
        """CatalogService.get_staging_origin delegates to StagingRepository."""
        path = "/fake/origin/test.mp3"
        repo = StagingRepository(populated_db)
        repo.set_origin(4, path)

        service = CatalogService(populated_db)
        result = service.get_staging_origin(4)

        assert result == path
