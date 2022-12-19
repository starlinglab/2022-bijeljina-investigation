# # 2022 Bijeljina Investigation: Asset Processing

Create `.env` in this directory and define the following:

```
BITCOIN_NODE_URL="http://<username>:<password>@<ip_address>:<port>"
C2PATOOL_PATH="c2patool/<c2patool_binary>"
```

Copy X.509 document signing certificate and private key for C2PA signing:

- `./key/starling-lab-bijeljina-investigation.cert.pem`: certificate used for C2PA signing
- `./key/starling-lab-bijeljina-investigation.key.pem`: private key for C2PA signing (do not commit this file)

Then populate the following input folders:

- `./in/archives/<sha256(archive).zip>`: unencrypted zip of archives
- `./in/archive_manifests/<sha256(input_bundle).json>`: archive manifests of primary assets with a `data_id` shown in Layer 3 UI
- `./in/archives_related/<sha256(archive).zip>`: unencrypted zip of related asset archives
- `./in/archive_manifests_related/<sha256(input_bundle).json>`: archive manifests of related assets where primary assets are derived from
- `./in/c2pa_thumbs/<data_id>.png`: custom thumbnails used for C2PA Claim 1 injection of selected assets
- `./in/zk_redacted/<data_id>.png`: ZK redaction outputs to be used for C2PA Claim 2 injection of selected assets

Generate `./asset_info_ext.json` from the asset spreadsheet containing editorial and other external info.

Then run `python3 generate_assets.py c2pa` and find generated assets at `./out`:

- `./out/c2pa_1_src/`: intermediate files for C2PA Claim 1 injection
- `./out/c2pa_1_out/`: C2PA assets with Claim 1 and C2PA manifests as JSON files
- `./out/c2pa_2_zk_src/`: intermediate files for C2PA Claim 2 injection (ZK-redacted assets only)
- `./out/c2pa_2_zk_out/`: C2PA assets with Claim 2 and C2PA manifests as JSON files (ZK-redacted assets only)

Before generating the data backing the Layer 3 UI, place the final C2PA assets that are to be published (e.g. after processing edits) in `./in/c2pa_publish`, then run `python3 generate_assets.py layer3` to find generated files at `./out/layer3_out/`.