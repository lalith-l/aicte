"""Unit tests for Phase 4: PAN masking, external head hash, and crypto shredding."""
import pytest
from packages.audit.pan_masking import mask_pan, permissioned_pan_reveal


def test_pan_masking():
    assert mask_pan("ABCDE1234F") == "•••••1234F"
    assert mask_pan("") == ""
    assert mask_pan(None) == ""


def test_permissioned_pan_reveal_role_guard():
    # institution_user cannot reveal PAN
    with pytest.raises(PermissionError):
        permissioned_pan_reveal(
            pan_plaintext="ABCDE1234F",
            document_id="doc-1",
            actor_id="user-inst",
            actor_role="institution_user",
            justification="Checking pan",
        )

    # scrutiny_officer can reveal with justification
    revealed = permissioned_pan_reveal(
        pan_plaintext="ABCDE1234F",
        document_id="doc-1",
        actor_id="user-officer",
        actor_role="scrutiny_officer",
        justification="Verifying identity discrepancy against affidavit",
    )
    assert revealed == "ABCDE1234F"


def test_permissioned_pan_reveal_requires_justification():
    with pytest.raises(ValueError):
        permissioned_pan_reveal(
            pan_plaintext="ABCDE1234F",
            document_id="doc-1",
            actor_id="user-officer",
            actor_role="scrutiny_officer",
            justification="  ",  # blank
        )
