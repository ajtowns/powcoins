import io

from . import core
from .core import key, script
from .core.script import CScript, CScriptNum


class CTransaction(core.messages.CTransaction):
    def pformat(self) -> str:
        s = f"CTransaction: (nVersion={self.nVersion})\n"
        s += "  vin:\n"
        for i, inp in enumerate(self.vin):
            s += f"    - [{i}] {inp}\n"
        s += "  vout:\n"
        for i, out in enumerate(self.vout):
            s += f"    - [{i}] {out}\n"

        s += "  witnesses:\n"
        for i, wit in enumerate(self.wit.vtxinwit):
            s += f"    - [{i}]\n"
            for j, item in enumerate(wit.scriptWitness.stack):
                if isinstance(item, bytes):
                    scriptstr = repr(CScript([item]))
                elif isinstance(item, (CScript, CScriptNum)):
                    scriptstr = repr(item)
                else:
                    raise NotImplementedError

                s += f"      - [{i}.{j}] {scriptstr}\n"

        s += f"  nLockTime: {self.nLockTime}\n"

        return s

    def pprint(self) -> None:
        print(self.pformat())

    @classmethod
    def fromhex(cls, h: str) -> "CTransaction":
        tx = cls()
        tx.deserialize(io.BytesIO(bytes.fromhex(h)))
        return tx

    def tohex(self) -> str:
        return self.serialize().hex()


__TaprootInfo = core.script.TaprootInfo

class TaprootInfo(__TaprootInfo):
    @property
    def p2tr_address(self) -> str:
        return core.address.output_key_to_p2tr(self.output_pubkey)

    def controlblock_for_script_spend(self, script_name: str) -> bytes:
        leaf = self.leaves[script_name]
        return (
            bytes([leaf.version + self.negflag])
            + self.internal_pubkey
            + leaf.merklebranch
        )


core.script.TaprootInfo = TaprootInfo  # type: ignore


def taproot_from_privkey(pk: key.ECKey, scripts=None) -> script.TaprootInfo:
    x_only, _ = key.compute_xonly_pubkey(pk.get_bytes())
    return script.taproot_construct(x_only, scripts=scripts)


def cscript_bytes_to_int(vch: bytes) -> int:
    """
    A port of CScriptNum.set_vch.
    """
    if len(vch) == 0:
        return 0
    s = 0
    for i, a in enumerate(vch):
        s |= a << (8 * i)
    if vch[-1] & 0x80:
        return -(s & ~(0x80 << (8 * (len(vch) - 1))))
    return s
