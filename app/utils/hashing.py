import hashlib
import json


def hash_inputs(
    target_domain: str,
    my_product_usp: str,
    ideal_customer_profile: str,
) -> str:
    """
    Deterministic SHA-256 of canonical job input fields.
    separators=(',', ':') eliminates whitespace variation.
    """
    canonical_payload = {
        'target_domain': target_domain,
        'my_product_usp': my_product_usp,
        'ideal_customer_profile': ideal_customer_profile,
    }
    canonical = json.dumps(canonical_payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
