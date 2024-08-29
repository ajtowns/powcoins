
# powcoins

Tool to obtain coins sent to PoW-faucet addresses on the Bitcoin signet network.

PoW-faucet addresses are:

    tb1pruektj90gg8nysa7yuk07w7ucwlywrf4p02lq3sz49f05xd00djscyt2fw (10 block delay)
    tb1pffsyra2t3nut94yvdae9evz3feg7tel843pfcv76vt5cwewavtesl3gsph (4 block delay)
    tb1pf2v25yk7m8mv203pvjusmk2a8r6tu8p59nhvwux86ck3s3pp0nkqt30dvt (1 block delay)

and are secured via an `OP_CAT` construction that requires a
combination of a CSV-delay and proof-of-work, such that the sooner
you attempt to spend the funds, the more proof-of-work you have to
provide. More details can be found in [Delving Bitcoin post on the
topic](https://delvingbitcoin.org/t/proof-of-work-based-signet-faucet/937).

## Usage

In order to claim coins you need to first run a Bitcoin
Signet node in order to find what coins are available to
be claimed. You can do this by running either [Bitcoin
Core](https://bitcoincore.org/en/releases/) or [Bitcoin
Inquisition](https://github.com/bitcoin-inquisition/bitcoin/releases),
or other node software compatible with bitcoin-cli.

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
$ ./powcoins claim --relay-peer=inquisition.bitcoin-signet.net --max-diff=30 $ADDR
```

If your local Bitcoin signet node is running the Inquisition code
and accepts `OP_CAT` spends, then you can remove the `--relay-peer`
argument to have your transaction submitted locally via `bitcoin-cli`,
and relayed in the usual manner instead.

Depending on your `PATH`, it may be necessary to set `--cli` as above,
and also to specify the location of the `bitcoin-util` command with the
`--grind="bitcoin-util grind"` option.

Because `bitcoin-util grind` is a CPU miner, the `--max-diff` figure is
provided to avoid wasting energy if the only available coins have high
difficulty. Each increment of max-diff (eg changing 30 to 31) will double
the amount of work it may take to obtain a coin.
