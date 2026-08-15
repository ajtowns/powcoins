
# powcoins

Tool to obtain coins sent to PoW-faucet addresses on the Bitcoin signet network.

PoW-faucet addresses are:

 * `tb1pzczwmt4kenu8j0avnhpyefp3gph32w2syuym8p8qxs5ulxudus3sqmsj75` (10 block delay)
 * `tb1pjltmm4pj4ezm9tzgtu2yay9m3k6ceh60mv8fr9wwlhghx66a22pskuyl72` (4 block delay)
 * `tb1ppj5s6ueay0w8mme25t7xlaa32zysq73c6t8vgw2qne3z3dpezedq6phh7e` (1 block delay)

Legacy addresses supported by default include:

 * Not stratum compatible:
   * `tb1pruektj90gg8nysa7yuk07w7ucwlywrf4p02lq3sz49f05xd00djscyt2fw` (10 block delay)
   * `tb1pffsyra2t3nut94yvdae9evz3feg7tel843pfcv76vt5cwewavtesl3gsph` (4 block delay)
   * `tb1pf2v25yk7m8mv203pvjusmk2a8r6tu8p59nhvwux86ck3s3pp0nkqt30dvt` (1 block delay)
 * Not a NUMS IPK:
   * `tb1pqz9w3kxd49srhpl3s2xq8v0vgwwusw2x00eu53whhr4d6w3rl22qfe0pv2` (10 block delay)
   * `tb1ppmdy6ngwh5n0lpg8h26rdu4qrk0slan4hku939n0qp0qfamqny7q0z6muc` (4 block delay)
   * `tb1pqslu565nh7kysxuatllz4z8k2m2qmhupewczytqu7fzscakmnscsxrjf79` (1 block delay)

These are secured via an `OP_CAT` construction that requires a
combination of a CSV-delay and proof-of-work, such that the sooner
you attempt to spend the funds, the more proof-of-work you have to
provide. More details can be found in [Delving Bitcoin post on the
topic](https://delvingbitcoin.org/t/proof-of-work-based-signet-faucet/937).

## Usage

### ASIC / stratumv1

Coins may be claimed by pointing a stratumv1 compatible miner at

 * `inquisition.bitcoin-signet.net:3333`

Your username should be a valid signet address that you wish to
receive coins for.

This pool distributes rewards based on hashrate, rather than solely to
successful solvers, so should be usable independent of hashrate. Miners
whose payout is under 1000 sats, will have their payouts combined and
distributed amongst each other as a lottery.

The code used to implement this is:

 * [Bitcoin Inquisition](https://github.com/bitcoin-inquisition/bitcoin/)
   for relaying `OP_CAT` compatible spends
 * `./powcoins server` from this repository for converting unspent
   powcoins into a block-template structure and successful block solves
   back into powcoin-claiming transactions
 * [ckpool](https://bitbucket.org/ckolivas/ckpool/src/master/) for converting block-templates into sv1 work
 * `./ckpayout` from this repository for distributing the claimed coins
   to miners

### CPU mining

In order to claim coins directly, you need to first run
a Bitcoin Signet node in order to find what coins are
available to be claimed. You can do this by running either
[Bitcoin Core](https://bitcoincore.org/en/releases/) or [Bitcoin
Inquisition](https://github.com/bitcoin-inquisition/bitcoin/releases),
or other node software compatible with bitcoin-cli. Running Bitcoin
Inquisition will allow the code to skip coins that have been claimed by
other users but not confirmed in the blockchain.

Once this is running, you can setup a local watch-only wallet (by default
called "powcoins") to track these coins by running:

```
$ ./powcoins setup-wallet
```

If `bitcoin-cli` is not in your `PATH`, you can specify how it should
be invoked by adding the `--cli="bitcoin-cli -signet"` option.

Note that this requires scanning through recent blocks for available
coins, so takes a little time.

Once the wallet is running, you can then attempt to claim coins by running
a command like:

```
$ ./powcoins claim --relay-peer=inquisition.bitcoin-signet.net --max-difficulty=30 $ADDR
```

If your local Bitcoin signet node is running the Inquisition code
and accepts `OP_CAT` spends, then you can remove the `--relay-peer`
argument to have your transaction submitted locally via `bitcoin-cli`,
and relayed in the usual manner instead.

Depending on your `PATH`, it may be necessary to set `--cli` as above,
and also to specify the location of the `bitcoin-util` command with the
`--grind="bitcoin-util grind"` option.

Because `bitcoin-util grind` is a CPU miner, the `--max-difficulty` figure is
provided to avoid wasting energy if the only available coins have high
difficulty. Each increment of max-diff (eg changing 30 to 31) will double
the amount of (expected) work it takes to obtain a coin.

### Racing multiple coins

The faucet is often actively contested: a single sequential claim attempt
can lose to a competing claimant who solves and broadcasts for the same
coin first, even after your own proof-of-work succeeds. `--parallel=N`
selects N distinct available coins and grinds/relays them concurrently
instead of one at a time, so losing one race doesn't cost you the time to
attempt another:

```
$ ./powcoins claim --relay-peer=inquisition.bitcoin-signet.net --max-difficulty=30 --parallel=6 $ADDR
```

After relaying, it polls for up to `--wait-confirm` seconds (default 900;
`0` to skip) and reports, per coin, whether it confirmed or lost to a
competing spend (naming the winning txid).

A specific coin can also be targeted directly with `--utxo=<txid>:<vout>`
instead of auto-selecting; it's mutually exclusive with `--parallel`, which
uses it internally to pin each concurrent attempt to a distinct coin.
