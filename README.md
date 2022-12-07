# 2022-bijeljina-investigation

This repository contains files to be included in the microsite.

- `assets` contains C2PA-injected assets
- `certs` contains X.509 document signing certificates for C2PA signing
- `manifests` contains C2PA manifests as text files

## Block explorers

- `OPENTIMESTAMPS`: https://www.blockchain.com/explorer/blocks/btc/`registrationRecords:openTimestamps:block`
- `NUMBERS`: https://mainnet.num.network/tx/`registrationRecords:numbersProtocol:tx`
- `AVALANCHE`: https://snowtrace.io/tx/`registrationRecords:numbersProtocolAvalanche:tx`
- `ISCN`: https://app.like.co/view/`URL_ENCODE(registrationRecords:iscn:iscnId)`
    - e.g. https://app.like.co/view/iscn:%2F%2Flikecoin-chain%2FzKklHgZMfKXzgJ0sdq6PDhitKKcQdpG7TpQ056r_foc%2F1
- `IPFS`: https://ipfs.io/ipfs/`storageRecords:ipfsCid`
- `FILECOIN`: https://filecoin.tools/`storageRecords:filecoin:pieceCid`
- `STORJ`: https://link.storjshare.io/s/`URL_ENCODE(storageRecords:storj:path)`
    - e.g. https://link.storjshare.io/s/jwwlss3g44lwvp5etxkxcn6oo6ya/newdemo/Big%20Buck%20Bunny%20Demo.mp4