# 2022 Bijeljina Investigation

This repository contains files to be included in the microsite.

- `certs` contains X.509 document signing certificates for C2PA signing
- `assets` contains C2PA-injected assets for publication
- `manifests` contains C2PA manifests of each asset as JSON files
- `layer3` contains data backing the Layer 3 UI

The files are generated following [these steps](internal/asset_processing).

## Block explorers

| Registration   | Explorer                                                                                    |
|:---------------|:--------------------------------------------------------------------------------------------|
| OpenTimestamps | `https://www.blockchain.com/explorer/blocks/btc/<registrationRecords:openTimestamps:block>` |
| Numbers        | `https://mainnet.num.network/tx/<registrationRecords:numbersProtocol:tx>`                   |
| Avalanche      | `https://snowtrace.io/tx/<registrationRecords:numbersProtocolAvalanche:tx>`                 |
| ISCN           | `https://app.like.co/view/<URL_ENCODE(registrationRecords:iscn:iscnId)>`                    |

| Preservation | Explorer                                                               |
|:-------------|:-----------------------------------------------------------------------|
| IPFS         | `https://ipfs.io/ipfs/<storageRecords:ipfsCid>`                        |
| Filecoin     | `https://filecoin.tools/<storageRecords:filecoin:pieceCid>`            |
| Storj        | `https://link.storjshare.io/s/<URL_ENCODE(storageRecords:storj:path)>` |