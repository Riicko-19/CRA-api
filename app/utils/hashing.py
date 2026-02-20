import hashlib
import json


def hash_inputs(payload: dict) -> str:
    """
    Deterministic SHA-256 of a dict.
    sort_keys=True ensures field order independence.
    separators=(',', ':') eliminates whitespace variation.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
