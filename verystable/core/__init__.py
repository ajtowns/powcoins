# This should be kept up to date with the contents of the upstream Core
# library.

import types

from . import (
    address,
    authproxy,
    bdb,
    blocktools,
    coverage,
    descriptors,
    key,
    messages,
    muhash,
    netutil,
    p2p,
    script,
    script_util,
    segwit_addr,
    siphash,
    socks5,
    test_node,
    util,
    wallet,
    wallet_util,
)

def __BLOWUP(*args, **kwargs):
    """Try our best to prevent people from losing money."""
    raise RuntimeError("This usage should not be generating key material!!")

key.generate_privkey = __BLOWUP
key.ECKey.generate = types.MethodType(__BLOWUP, key.ECKey)  # type: ignore
