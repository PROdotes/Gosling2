
import pytest
import tempfile
import os
from src.core import yellberus
from src.core.yellberus import FIELDS

class TestLaw002CompletenessValidity:
    """
    LAW 002: COMPLETENESS VALIDITY
    
    This test suite enforces the Immutable Laws of Song Metadata Completeness.
    It protects against regression in the 'Done' gate logic, ensuring that
    Status=Done is only granted when specific conditions are strictly met.
    
    Any failure here indicates a CRITICAL REGRESSION in the application logic.
    DO NOT MODIFY THIS FILE TO MAKE TESTS PASS. FIX THE APPLICATION CODE.
    """

    def test_law_genre_is_strictly_required(self):
        """
        LAW: A Song CANNOT be 'Complete' (Ready) without at least one GENRE tag.
        This protects against the bug where empty tag lists bypassed validation.
        """
        # 1. Setup row data mimicking a Song object state
        # Order MUST match yellberus.FIELDS
        # We need to construct a valid row, but vary the tags field
        
        # Helper to build a row dict
        def make_row(tags_val):
            row = []
            for f in FIELDS:
                if f.name == 'tags':
                    row.append(tags_val)
                elif f.name == 'is_active':
                    row.append(True)
                elif f.name == 'recording_year':
                    row.append(2024)
                elif f.name in ('title', 'path', 'source', 'file_id'):
                    row.append("Mock Value")
                elif f.name == 'duration':
                    row.append(180)
                elif f.field_type == yellberus.FieldType.LIST and f.required:
                    row.append(["Mock List Item"]) # Satisfy performers, album, etc
                elif f.required:
                    row.append("Mock Required")
                else:
                    row.append(None)
            return row

        # Scenario A: No Tags (None)
        row_none = make_row(None)
        missing_none = yellberus.check_completeness(row_none)
        assert 'Genre' in missing_none, "VIOLATION: Validation passed with None tags (should fail due to missing Genre)"

        # Scenario B: Empty List
        row_empty = make_row([])
        missing_empty = yellberus.check_completeness(row_empty)
        assert 'Genre' in missing_empty, "VIOLATION: Validation passed with Empty Tag List (should fail due to missing Genre)"

        # Scenario C: Non-Genre Tag
        row_other = make_row(["Mood:Happy"])
        missing_other = yellberus.check_completeness(row_other)
        assert 'Genre' in missing_other, "VIOLATION: Validation passed with non-Genre tags (should fail due to missing Genre)"

        # Scenario D: Valid Genre Tag
        row_valid = make_row(["Genre:Pop", "Mood:Happy"])
        missing_valid = yellberus.check_completeness(row_valid)
        assert 'Genre' not in missing_valid, "VIOLATION: Validation FAILED despite presence of Genre:Pop"

    def test_law_composer_publisher_strictness(self):
        """
        LAW: Composers and Publishers are STRICTLY REQUIRED.
        This prevents regression to 'optional' status.
        """
        # 1. Check Field Definitions directly
        composer_def = yellberus.get_field('composers')
        assert composer_def.required is True, "VIOLATION: Composers field must be REQUIRED"
        
    def test_law_all_required_fields_enforced(self):
        """
        LAW: If ANY required field is missing, validation MUST fail.
        This iterates through every field marked 'required=True' in the registry
        and proves that removing it causes validation failure.
        """
        # 1. Create a "Perfect" Row (Base State)
        perfect_row = []
        for f in FIELDS:
            if f.name == 'tags':
                perfect_row.append(["Genre:Pop"]) # Satisfies Genre requirement
            elif f.field_type == yellberus.FieldType.LIST:
                perfect_row.append(["Item 1"])
            elif f.field_type == yellberus.FieldType.INTEGER:
                perfect_row.append(2024)
            elif f.field_type == yellberus.FieldType.BOOLEAN:
                perfect_row.append(True)
            elif f.field_type == yellberus.FieldType.DURATION:
                perfect_row.append(180)
            else:
                perfect_row.append("Valid String")
        
        # Verify Perfect Row passes
        assert len(yellberus.check_completeness(perfect_row)) == 0, "Setup Error: Perfect row should pass validation"

        # 2. Sabotage Loop: Test each required field individually
        for i, field in enumerate(FIELDS):
            if not field.required:
                continue

            # Sabotage this field
            bad_row = list(perfect_row) # Shallow copy
            
            # Set to "Empty" value based on type to trigger failure
            if field.field_type == yellberus.FieldType.LIST:
                bad_row[i] = []
            elif field.field_type in (yellberus.FieldType.INTEGER, yellberus.FieldType.DURATION, yellberus.FieldType.REAL):
                bad_row[i] = None
            else:
                bad_row[i] = "" # Empty string

            # Run Validation
            missing = yellberus.check_completeness(bad_row)
            
            # Assert
            assert field.name in missing, f"VIOLATION: Required field '{field.name}' was missing but validation passed! The System is essentially hallucinating data."
