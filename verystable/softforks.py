import struct

from .core import script, messages


def activate_bip345_vault():
    """
    Patches in script changes necessary for use of BIP-345 (OP_VAULT).
    """
    script.OP_VAULT = script.CScriptOp(0xbb)
    script.OP_VAULT_RECOVER = script.CScriptOp(0xbc)

    script.OPCODE_NAMES[script.OP_VAULT] = 'OP_VAULT'
    script.OPCODE_NAMES[script.OP_VAULT_RECOVER] = 'OP_VAULT_RECOVER'


def activate_bip119_ctv():
    script.OP_CHECKTEMPLATEVERIFY = script.CScriptOp(0xb3)
    script.OPCODE_NAMES[script.OP_CHECKTEMPLATEVERIFY] = 'OP_CHECKTEMPLATEVERIFY'

    messages.CTransaction.get_standard_template_hash = _get_standard_template_hash


def _get_standard_template_hash(self, nIn):
    r = b""
    r += struct.pack("<i", self.nVersion)
    r += struct.pack("<I", self.nLockTime)
    if any(inp.scriptSig for inp in self.vin):
        r += messages.sha256(
            b"".join(messages.ser_string(inp.scriptSig) for inp in self.vin))
    r += struct.pack("<I", len(self.vin))
    r += messages.sha256(b"".join(struct.pack("<I", inp.nSequence) for inp in self.vin))
    r += struct.pack("<I", len(self.vout))
    r += messages.sha256(b"".join(out.serialize() for out in self.vout))
    r += struct.pack("<I", nIn)
    return messages.sha256(r)
