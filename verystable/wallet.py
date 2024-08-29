import time
import secrets
import typing as t
from dataclasses import dataclass, field
from functools import cached_property

from . import core
from .rpc import BitcoinRPC, JSONRPCError
from .core.script import CScript, taproot_construct
from .core.messages import COutPoint, CTxOut, CTxIn

import logging

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Outpoint:
    txid: str
    n: int

    def __str__(self) -> str:
        return f"{self.txid}:{self.n}"

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, o) -> bool:
        return self.__dict__ == getattr(o, '__dict__', {})


def btc_to_sats(btc) -> int:
    return int(btc * core.messages.COIN)


def txid_to_int(txid: str) -> int:
    return int.from_bytes(bytes.fromhex(txid), byteorder="big")


@dataclass(frozen=True)
class Utxo:
    outpoint: Outpoint
    address: str
    value_sats: int
    height: int

    @cached_property
    def scriptPubKey(self) -> CScript:
        return core.address.address_to_scriptpubkey(self.address)

    @cached_property
    def coutpoint(self) -> COutPoint:
        return COutPoint(txid_to_int(self.outpoint.txid), self.outpoint.n)

    @cached_property
    def output(self) -> CTxOut:
        return CTxOut(nValue=self.value_sats, scriptPubKey=self.scriptPubKey)

    @cached_property
    def as_txin(self) -> CTxIn:
        return CTxIn(self.coutpoint)

    @property
    def outpoint_str(self) -> str:
        return str(self.outpoint)

    def __hash__(self) -> int:
        return hash(str(self.outpoint))

@dataclass
class Spend:
    spent_utxo: Utxo
    height: int
    tx: dict

    def __repr__(self) -> str:
        return (
            f"Spend(amt={self.spent_utxo.value_sats} "
            f"from_addr={self.spent_utxo.address}, height={self.height})")


def get_confs_for_txid(
        rpc: BitcoinRPC, target_txid: str, min_height: int = 0) -> int | None:
    """Return the number of confirmations for a transaction."""
    height = rpc.getblockcount()
    found_height = None
    while min_height is None or height >= min_height:
        blk = rpc.getblock(rpc.getblockhash(height), 1)
        height -= 1

        for txid in blk["tx"]:
            if txid == target_txid:
                found_height = blk["height"]

    if found_height is None:
        return None

    return rpc.getblockcount() - found_height + 1


def get_relevant_blocks(
    rpc: BitcoinRPC,
    addrs: t.Iterable[str],
    startheight: int = 0,
    max_wait_secs: int = 5,
) -> list[tuple[int, dict]]:
    """
    Given some addresses, return height/block pairs with relevant activity.
    """
    scanarg = [f"addr({addr})" for addr in addrs]

    def wait_for_scan_end(to_wait_secs: int = max_wait_secs):
        while (status := rpc.scanblocks("status")) and to_wait_secs >= 0:
            log.info("scanblocks in progress: %s", status)
            to_wait_secs -= 1
            time.sleep(1)

    wait_for_scan_end()

    def scanblocks() -> dict:
        return rpc._call("scanblocks", "start", scanarg, startheight, timeout=10_000)

    try:
        got = scanblocks()
    except JSONRPCError as e:
        if e.code == -8:
            # scan already in progress
            wait_for_scan_end()
            try:
                got = scanblocks()
            except JSONRPCError as e:
                log.exception("scanblocks call busy for too long")
        raise

    assert "relevant_blocks" in got

    heights_and_blocks = []
    for hash in set(got["relevant_blocks"]):
        block = rpc.getblock(hash, 2)
        heights_and_blocks.append((block["height"], block))

    return heights_and_blocks


def get_addr_history(
    rpc: BitcoinRPC,
    addr_watchlist: t.Iterable[str],
) -> tuple[set[Utxo], list[Spend]]:
    """
    Return all outstanding UTXOs associated with a set of addresses, and their spend
    history.
    """
    utxos: set[Utxo] = set()
    spent: list[Spend] = []
    heights_and_blocks = get_relevant_blocks(rpc, addr_watchlist)
    outpoint_to_utxo: dict[Outpoint, Utxo] = {}
    txids_to_watch: set[str] = set()

    for height, block in sorted(heights_and_blocks):
        for tx in block["tx"]:
            # Detect new utxos
            for vout in tx["vout"]:
                if (addr := vout.get("scriptPubKey",
                                     {}).get("address")) and (addr in addr_watchlist):
                    op = Outpoint(tx["txid"], vout["n"])
                    utxo = Utxo(op, addr, btc_to_sats(vout["value"]), height)
                    outpoint_to_utxo[op] = utxo
                    txids_to_watch.add(tx["txid"])
                    utxos.add(utxo)
                    log.info("found utxo (%s): %s", addr, utxo)

            # Detect spends
            for vin in filter(lambda vin: "txid" in vin, tx["vin"]):
                spent_txid = vin["txid"]
                if spent_txid not in txids_to_watch:
                    continue

                op = Outpoint(spent_txid, vin.get("vout"))

                if not (spent_utxo := outpoint_to_utxo.get(op)):
                    continue

                log.info("found spend of utxo %s", spent_utxo)
                spent.append(Spend(spent_utxo, height, tx))
                utxos.remove(spent_utxo)
                outpoint_to_utxo.pop(op)

    return utxos, spent


@dataclass
class SingleAddressWallet:
    """
    World's worst P2TR single-address wallet.
    Doesn't track history, just gives you UTXOs. Possibly good for fee management.
    """

    rpc: BitcoinRPC

    # Users of this class are responsible for tracking/persisting locked UTXOs
    # across program restarts.
    locked_utxos: set[Outpoint]

    seed: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    utxos: list[Utxo] = field(default_factory=list)

    def __post_init__(self):
        self.key = core.key.ECKey()
        self.key.set(self.seed, compressed=True)
        self.pubkey = self.key.get_pubkey().get_bytes()[1:]
        self.privkey = self.key.get_bytes()
        self.tr_info = taproot_construct(self.pubkey)
        self.fee_addr = core.address.output_key_to_p2tr(self.tr_info.output_pubkey)
        self.fee_spk = core.address.address_to_scriptpubkey(self.fee_addr)

    def rescan(self):
        """Use scantxoutset to recompute UTXOs. Probably pretty slow on mainnet."""
        self.utxos = []

        res = self.rpc.scantxoutset("start", [f"addr({self.fee_addr})"])
        if not (unspents := res.get("unspents")):
            log.warning("couldn't find any fee outputs")
            return

        for unspent in unspents:
            op = Outpoint(unspent["txid"], unspent["vout"])
            self.utxos.append(
                Utxo(
                    op,
                    self.fee_addr,
                    btc_to_sats(unspent["amount"]),
                    height=unspent['height'],
                ))

    def sign_msg(self, msg: bytes) -> bytes:
        """Sign a message with the fee wallet's private key."""
        return core.key.sign_schnorr(
            core.key.tweak_add_privkey(self.privkey, self.tr_info.tweak), msg)

    def get_utxo(self) -> Utxo:
        """Return a UTXO that is mature and not currently locked."""
        self.rescan()
        utxos = [u for u in list(self.utxos) if u.outpoint not in self.locked_utxos]

        if not utxos:
            raise RuntimeError(
                "Fee wallet empty! Add coins with "
                f"`bitcoin-cli -regtest generatetoaddress 20 {self.fee_addr}`")

        height = self.rpc.getblockcount()
        utxos.sort(key=lambda u: u.height)
        if (height - self.utxos[0].height) < 100:
            raise RuntimeError(
                "No mature coins available; call `-generate` a few times. ")

        utxo = utxos.pop(0)
        self.locked_utxos.add(utxo.outpoint)
        return utxo
