"""Ed25519 primitives for the ledgers. Pure Python on `cryptography`; key storage lives in keystore.py."""

import base64
import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

_RAW = serialization.Encoding.Raw


def _b64(data: bytes) -> str:
	return base64.b64encode(data).decode("ascii")


def key_id_for(public_b64: str) -> str:
	"""Short, stable identifier for a public key: first 16 hex chars of sha256(raw key)."""
	return hashlib.sha256(base64.b64decode(public_b64)).hexdigest()[:16]


def generate_keypair() -> tuple[str, str, str]:
	"""Return (private_b64, public_b64, key_id)."""
	private = Ed25519PrivateKey.generate()
	private_b64 = _b64(
		private.private_bytes(_RAW, serialization.PrivateFormat.Raw, serialization.NoEncryption())
	)
	public_b64 = public_from_private(private_b64)
	return private_b64, public_b64, key_id_for(public_b64)


def public_from_private(private_b64: str) -> str:
	private = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_b64))
	return _b64(private.public_key().public_bytes(_RAW, serialization.PublicFormat.Raw))


def sign(private_b64: str, message: str) -> str:
	private = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_b64))
	return _b64(private.sign(message.encode("utf-8")))


def verify(public_b64: str, message: str, signature_b64: str) -> bool:
	try:
		public = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64))
		public.verify(base64.b64decode(signature_b64), message.encode("utf-8"))
		return True
	except (InvalidSignature, ValueError, TypeError):
		return False
