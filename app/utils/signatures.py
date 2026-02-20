from app.domain.exceptions import InvalidSignatureError


def verify_signature(job_id: str, signature: str) -> None:
    """
    Mock Ed25519 verification.
    A real implementation would use cryptography.hazmat.
    Contract: signature MUST equal "valid_sig_" + job_id
    Raises InvalidSignatureError on mismatch.
    """
    expected = f"valid_sig_{job_id}"
    if signature != expected:
        raise InvalidSignatureError(f"Signature mismatch for job {job_id!r}")
