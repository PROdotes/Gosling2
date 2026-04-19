from src.engine.config import ProcessingStatus


class TestProcessingStatusEnum:
    def test_reviewed_value(self):
        assert ProcessingStatus.REVIEWED == 0
        assert ProcessingStatus.REVIEWED.name == "REVIEWED"

    def test_needs_review_value(self):
        assert ProcessingStatus.NEEDS_REVIEW == 1
        assert ProcessingStatus.NEEDS_REVIEW.name == "NEEDS_REVIEW"

    def test_pending_enrichment_value(self):
        assert ProcessingStatus.PENDING_ENRICHMENT == 2
        assert ProcessingStatus.PENDING_ENRICHMENT.name == "PENDING_ENRICHMENT"

    def test_converting_value(self):
        assert ProcessingStatus.CONVERTING == 3
        assert ProcessingStatus.CONVERTING.name == "CONVERTING"

    def test_is_int_subclass(self):
        assert isinstance(ProcessingStatus.REVIEWED, int)
        assert isinstance(ProcessingStatus.CONVERTING, int)

    def test_comparison_with_bare_int(self):
        assert ProcessingStatus.REVIEWED == 0
        assert ProcessingStatus.NEEDS_REVIEW != 0
        assert ProcessingStatus.PENDING_ENRICHMENT == 2
        assert ProcessingStatus.CONVERTING == 3

    def test_iteration_covers_all(self):
        assert len(list(ProcessingStatus)) == 4
