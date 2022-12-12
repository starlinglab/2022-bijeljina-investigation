Create `.env` in this directory and define the following:

```
BITCOIN_NODE_URL="http://<username>:<password>@<ip_address>:<port>"
C2PATOOL_PATH="c2patool/<c2patool_binary>"
```

Then populate the `archives` and `archive-manifests` folders with data from a collection. For example:

```
$ scp starling-prod-integrity:/mnt/integrity_store/starling/internal/starling-lab/bijeljina-investigation-haviv-scans/action-archive/*.zip assets/default/archives
$ scp starling-prod-integrity:/mnt/integrity_store/starling/shared/starling-lab/bijeljina-investigation-haviv-scans/action-archive/*.json assets/default/archive-manifests
```

If there are custom thumbnail files, add them to `c2pa_1_src` with file name matched to the asset for C2PA injection and extension `.thumb`. For example, `P204.thumb`.

Then run `python3 generate_assets.py`.

The script will take archives and metadata from `archives` and `archive-manifests`, and create:

1. `c2pa_1_src`: intermediate files for C2PA injection
2. `c2pa_1_out`: C2PA-injected assets and C2PA manifests as JSON files
3. `layer3_out`: data backing the Layer 3 UI

Inspect what is in `c2pa_1_out`, then copy the results over to the repository root's `assets`, `manifests`, and `layer3` folders.