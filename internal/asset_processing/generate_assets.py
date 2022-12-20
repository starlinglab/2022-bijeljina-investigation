from datetime import datetime
from PIL import Image
import dotenv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

# Work-around for bug in PIL
from PIL import JpegImagePlugin
JpegImagePlugin._getmp = lambda x: None

# Load .env
dotenv.load_dotenv()
bitcoin_node_url = os.environ.get("BITCOIN_NODE_URL")
c2patool_path = os.environ.get("C2PATOOL_PATH")

# Paths to working directory and binaries
p_c2patool = os.path.abspath(c2patool_path)
p_assets = "assets"

# Paths to schema templates
p_c2pa_1_template = "c2pa_1_template.json"
p_c2pa_2_zk_template = "c2pa_2_zk_template.json"
p_layer3_template = "layer3_template.json"

# Paths to input files
p_asset_info_ext = "asset_info_ext.json"
p_in = os.path.join(p_assets, "in")
p_in_archives = os.path.join(p_in, "archives")
p_in_archive_manifests = os.path.join(p_in, "archive_manifests")
p_in_archives_related = os.path.join(p_in, "archives_related")
p_in_archive_manifests_related = os.path.join(p_in, "archive_manifests_related")
p_in_c2pa_thumbs = os.path.join(p_in, "c2pa_thumbs")
p_in_zk_redacted = os.path.join(p_in, "zk_redacted")
p_in_c2pa_publish = os.path.join(p_in, "c2pa_publish")

# Paths to output files
p_out = os.path.join(p_assets, "out")
p_out_c2pa_1_src = os.path.join(p_out, "c2pa_1_src")
p_out_c2pa_1_out = os.path.join(p_out, "c2pa_1_out")
p_out_c2pa_2_zk_src = os.path.join(p_out, "c2pa_2_zk_src")
p_out_c2pa_2_zk_out = os.path.join(p_out, "c2pa_2_zk_out")
p_out_layer3_out = os.path.join(p_out, "layer3_out")

class ArchiveManifests():
    path_archive_manifests = None
    internal_cache = {}

    def __init__(self, path_archive_manifests) -> None:
        self.path_archive_manifests=path_archive_manifests

    def find_by_hash(self, hash):
        if hash in self.internal_cache:
            return self.internal_cache[hash]
        res = []
        for filename in os.listdir(self.path_archive_manifests):
            if filename.endswith(".json"):
                path_manifest = os.path.join(self.path_archive_manifests, filename)
                with open(path_manifest, "r") as f:
                    manifest = f.read()
                    if manifest.find(hash) != -1:
                        v = {
                            "hash": os.path.splitext(filename)[0],
                            "path": path_manifest
                        }
                        res.append(v)
        self.internal_cache[hash] = res
        return res

    def get_manifest(self, hash):
        manifests = self.find_by_hash(hash)
        if len(manifests) == 0:
            return None
        with open(f"{manifests[0]['path']}", "r") as f:
            return json.load(f)

def _get_index_by_label(c2pa, label):
    return [i for i, o in enumerate(c2pa["assertions"]) if o["label"] == label][0]

def _fill_opentimestamps(archive_manifest, path_archives):
    result = None
    path_archive = os.path.join(path_archives, f"{archive_manifest['archive']['sha256']}.zip")
    content_hash = archive_manifest["content"]["sha256"]
    with zipfile.ZipFile(path_archive) as zf:
        for filename in zf.namelist():
            if re.match(f"proofs/{content_hash}\..*\.ots", filename):
                f = zf.read(filename)
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(f)
                    tmp.close()
                    v = subprocess.run(["ots", "--bitcoin-node", f"{bitcoin_node_url}", "verify", "-d", f"{content_hash}", tmp.name], capture_output=True)
                    os.remove(tmp.name)
                    lines = v.stderr.decode("ascii").split("\n")
                    res = lines[len(lines)-2]
                    if res:
                        res_match = re.search("^Success! Bitcoin block (\d{1,10})", res)
                        if res_match:
                            btc_block_no = res_match.group(1)
                            if btc_block_no:
                                # Insert opentimestamps registration record
                                result = archive_manifest
                                result["registrationRecords"]["openTimestamps"] = {
                                    "sha256": content_hash,
                                    "block": btc_block_no
                                }
                            else:
                                raise Exception(f"Failed opentimestamps verify: btc_block_no=None")
                        else:
                            raise Exception(f"Failed opentimestamps verify: res={res}")
                    else:
                        raise Exception("Failed opentimestamps verify: res=None")
    if result is None:
        raise Exception("Failed opentimestamps verify")
    return result

def _get_validated_signatures_from_archive(archive_manifest, path_archives):
    result = None
    path_archive = os.path.join(path_archives, f"{archive_manifest['archive']['sha256']}.zip")
    content_hash = archive_manifest["content"]["sha256"]
    with zipfile.ZipFile(path_archive) as zf:
        for filename in zf.namelist():
            if re.match(f"{content_hash}-meta-content\.json", filename):
                f = zf.read(filename)
                content_metadata = json.loads(f).get("contentMetadata")
                result = content_metadata.get("validatedSignatures", [])
    if result is None:
        raise Exception("Failed to get validatedSignatures")
    return result

def _get_authsign_from_archive(archive_manifest, path_archives):
    result = None
    path_archive = os.path.join(path_archives, f"{archive_manifest['archive']['sha256']}.zip")
    content_hash = archive_manifest["content"]["sha256"]
    with zipfile.ZipFile(path_archive) as zf:
        for filename in zf.namelist():
            if re.match(f"proofs/{content_hash}\..*\.authsign", filename):
                f = zf.read(filename)
                # sig = json.load(f)
                sig = json.loads(f.decode('unicode_escape').replace('"{', "{").replace('}"', "}")) # authsign signatures are encoded as strings due to a backend bug
                sig_provider = sig.get("software")
                sig_algo = "ecdsa-certificate-sig"
                result = {
                    "starling:provider": sig_provider,
                    "starling:algorithm": sig_algo,
                    "starling:custom": sig
                }
    if result is None:
        raise Exception("Failed to get authsign")
    return result

def _generate_c2pa_src_from_archive(archive_manifests, archive_manifests_related, asset_info_ext, path_archive):
    with open(p_c2pa_1_template, "r") as c2pa_1_template:
        c2pa_1 = json.load(c2pa_1_template)
        source_id = None
        related_asset_cid = None

        with zipfile.ZipFile(path_archive) as zf:
            content_hash = None
            ext = None

            # Prepare c2pa manifest for injection
            for filename in zf.namelist():
                if filename.endswith("-meta-content.json"):
                    f = zf.read(filename)
                    # print(json.dumps(json.loads(f), indent=2))
                    content_hash = os.path.basename(filename).split("-meta-content.json")[0]
                    content_metadata = json.loads(f).get("contentMetadata")
                    source_id = content_metadata.get("sourceId").get("value")
                    related_asset_cid = content_metadata.get("relatedAssetCid")
                    if source_id is None:
                        raise Exception("Missing sourceId")
                    info_ext = asset_info_ext.get(source_id)
                    if info_ext is None:
                        raise Exception(f"Missing assetInfoExt for {source_id}")
                    print(f"{source_id}: processing archive [ archive.path={path_archive} ] containing asset [ content.sha256={content_hash} ]")
                    
                    # Insert claim generator
                    c2pa_1["claim_generator"] = info_ext.get("claimGenerator")

                    # Insert authorship information
                    m = _get_index_by_label(c2pa_1, "stds.schema-org.CreativeWork")
                    c2pa_1["assertions"][m]["data"]["author"][0]["@type"] = content_metadata.get("author").get("@type")
                    c2pa_1["assertions"][m]["data"]["author"][0]["identifier"] = content_metadata.get("author").get("identifier")
                    c2pa_1["assertions"][m]["data"]["author"][0]["name"] = content_metadata.get("author").get("name")

                    # Insert c2pa.created actions
                    m = _get_index_by_label(c2pa_1, "c2pa.actions")
                    n = [i for i, o in enumerate(c2pa_1["assertions"][m]["data"]["actions"]) if o["action"] == "c2pa.created"][0]
                    c2pa_1["assertions"][m]["data"]["actions"][n]["when"] = info_ext.get("captureDate")

                    # Insert c2pa.converted and c2pa.resized actions for ZK redaction assets
                    if info_ext.get("redaction") == "ZK":
                        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
                        c2pa_1["assertions"][m]["data"]["actions"].append({ "action": "c2pa.converted", "when": now })
                        c2pa_1["assertions"][m]["data"]["actions"].append({ "action": "c2pa.resized", "when": now })

                    # Insert iptc metadata
                    m = _get_index_by_label(c2pa_1, "stds.iptc.photo-metadata")
                    c2pa_1["assertions"][m]["data"]["dc:creator"][0] = info_ext.get("capturedBy")
                    c2pa_1["assertions"][m]["data"]["dc:description"] = info_ext.get("captionText")
                    location = {}
                    if info_ext.get("countryCode"): location["Iptc4xmpExt:CountryCode"] = info_ext.get("countryCode")
                    if info_ext.get("countryName"): location["Iptc4xmpExt:CountryName"] = info_ext.get("countryName")
                    if info_ext.get("provinceState"): location["Iptc4xmpExt:ProvinceState"] = info_ext.get("provinceState")
                    if info_ext.get("city"): location["Iptc4xmpExt:City"] = info_ext.get("city")
                    c2pa_1["assertions"][m]["data"]["Iptc4xmpExt:LocationCreated"] = location

                    # Insert identifier
                    m = _get_index_by_label(c2pa_1, "org.starlinglab.integrity")
                    content_id_starling_capture = content_metadata.get("private", {}).get("starlingCapture", {}).get("metadata", {}).get("proof", {}).get("hash")
                    if content_id_starling_capture:
                        c2pa_1["assertions"][m]["data"]["starling:identifier"] = content_id_starling_capture
                    else:
                        c2pa_1["assertions"][m]["data"]["starling:identifier"] = content_metadata.get("sourceId").get("value")

                    # Insert signatures
                    c2pa_1["assertions"][m]["data"]["starling:signatures"] = []
                    for sig in content_metadata.get("validatedSignatures", []):
                        x = {}
                        if sig.get("provider"): x["starling:provider"] = sig.get("provider")
                        if sig.get("algorithm"): x["starling:algorithm"] = sig.get("algorithm")
                        if sig.get("publicKey"): x["starling:publicKey"] = sig.get("publicKey")
                        if sig.get("signature"): x["starling:signature"] = sig.get("signature")
                        if sig.get("authenticatedMessage"): x["starling:authenticatedMessage"] = sig.get("authenticatedMessage")
                        if sig.get("authenticatedMessageDescription"): x["starling:authenticatedMessageDescription"] = sig.get("authenticatedMessageDescription")
                        if sig.get("custom"): x["starling:custom"] = sig.get("custom")
                        c2pa_1["assertions"][m]["data"]["starling:signatures"].append(x)
                    c2pa_1["assertions"][m]["data"]["starling:signatures"].append(_get_authsign_from_archive(archive_manifests.get_manifest(content_hash), p_in_archives))

                    # Insert archive manifests
                    c2pa_1["assertions"][m]["data"]["starling:archives"] = []
                    manifest = _fill_opentimestamps(archive_manifests.get_manifest(content_hash), p_in_archives)
                    if manifest:
                        c2pa_1["assertions"][m]["data"]["starling:archives"].append(manifest)

            # Extract archived content file
            for filename in zf.namelist():
                if filename.endswith(".jpg") or filename.endswith(".png"):
                    if source_id is None:
                        raise Exception("Missing sourceId")
                    ext = os.path.basename(filename).split(".")[1]
                    with zf.open(filename) as zimg, open(os.path.join(p_out_c2pa_1_src, f"{source_id}.{ext}"), "wb") as img:
                        shutil.copyfileobj(zimg, img)

            # Insert authenticity data from related assets (only for images derived from a source such as WACZ or ProofMode)
            if related_asset_cid:
                print(f"{source_id}: appending data from related archive [ archiveEncrypted.cid={related_asset_cid} ]")
                related_manifest = _fill_opentimestamps(archive_manifests_related.get_manifest(related_asset_cid), p_in_archives_related)
                if related_manifest is None:
                    raise Exception("Missing related archive manifest")

                # Insert signatures of the source archive                
                m = _get_index_by_label(c2pa_1, "org.starlinglab.integrity")
                c2pa_1["assertions"][m]["data"]["starling:signaturesRelated"] = []
                for sig in _get_validated_signatures_from_archive(archive_manifests.get_manifest(related_asset_cid), p_in_archives_related):
                    x = {}
                    if sig.get("provider"): x["starling:provider"] = sig.get("provider")
                    if sig.get("algorithm"): x["starling:algorithm"] = sig.get("algorithm")
                    if sig.get("publicKey"): x["starling:publicKey"] = sig.get("publicKey")
                    if sig.get("signature"): x["starling:signature"] = sig.get("signature")
                    if sig.get("authenticatedMessage"): x["starling:authenticatedMessage"] = sig.get("authenticatedMessage")
                    if sig.get("authenticatedMessageDescription"): x["starling:authenticatedMessageDescription"] = sig.get("authenticatedMessageDescription")
                    if sig.get("custom"): x["starling:custom"] = sig.get("custom")
                    c2pa_1["assertions"][m]["data"]["starling:signaturesRelated"].append(x)
                c2pa_1["assertions"][m]["data"]["starling:signaturesRelated"].append(_get_authsign_from_archive(archive_manifests_related.get_manifest(related_asset_cid), p_in_archives_related))

                # Insert archive manifests of the source archive
                c2pa_1["assertions"][m]["data"]["starling:archivesRelated"] = []
                c2pa_1["assertions"][m]["data"]["starling:archivesRelated"].append(related_manifest)

            # print(json.dumps(c2pa_1, indent=2))
            with open(os.path.join(p_out_c2pa_1_src, f"{source_id}.json"), "w") as man:
                json.dump(c2pa_1, man)

def _generate_c2pa_out_from_src(archive_manifests, archive_manifests_related, asset_info_ext):
    # Generate intermediate files for c2pa injection
    for archive in os.listdir(p_in_archives):
        # if archive.endswith(".zip") and archive.startswith("e1cd2b256ffc33ea27d3f1776d3524b717000e585e79115fc93c841d6699d2b8"): # archive with Photoshop redaction asset
        # if archive.endswith(".zip") and archive.startswith("70351d224eaa94d2c4c8517c59b4c10e957cce2b01da87d269646633232cce7a"): # archive with ZK redaction asset
        if archive.endswith(".zip"):
            path_archive = os.path.join(p_in_archives, archive)
            _generate_c2pa_src_from_archive(archive_manifests, archive_manifests_related, asset_info_ext, path_archive)

    # Generate c2pa injected assets in path_c2pa_1_out
    for filename in os.listdir(p_out_c2pa_1_src):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            basename = os.path.basename(filename).split(".")[0]
            ext = os.path.basename(filename).split(".")[1]

            # Assets with one c2pa manifest
            path_out_c2pa_1 = os.path.join(p_out_c2pa_1_out, filename)
            path_out_c2pa_1_man = os.path.join(p_out_c2pa_1_out, f"{basename}-manifest.json")

            # Assets with two c2pa manifests (only for ZK redaction assets)
            path_out_c2pa_2_zk = os.path.join(p_out_c2pa_2_zk_out, filename)
            path_out_c2pa_2_zk_man = os.path.join(p_out_c2pa_2_zk_out, f"{basename}-manifest.json")

            # Inject c2pa manifests
            redaction = asset_info_ext.get(basename, {}).get("redaction")
            path_img = os.path.join(p_out_c2pa_1_src, filename)
            path_man = os.path.join(p_out_c2pa_1_src, f"{basename}.json")
            path_thumb = os.path.join(p_in_c2pa_thumbs, f"{basename}.png")
            path_zk_redacted = os.path.join(p_in_zk_redacted, f"{basename}.png")

            if redaction == "None":
                p = subprocess.run([f"{p_c2patool}", f"{path_img}", "--manifest", f"{path_man}", "--output" , f"{path_out_c2pa_1}", "--force"], capture_output=True)
                with open(path_out_c2pa_1_man, "w") as f:
                    p = subprocess.run([f"{p_c2patool}", f"{path_out_c2pa_1}", "--detailed"], stdout=f)
            elif redaction == "Photoshop":
                if os.path.isfile(path_thumb):
                    p = subprocess.run([f"{p_c2patool}", f"{path_img}", "--manifest", f"{path_man}", "--thumb", f"{path_thumb}", "--output" , f"{path_out_c2pa_1}", "--force"], capture_output=True)
                    with open(path_out_c2pa_1_man, "w") as f:
                        p = subprocess.run([f"{p_c2patool}", f"{path_out_c2pa_1}", "--detailed"], stdout=f)
                else:
                    raise Exception("Missing thumbnail for image that requires redaction")
            elif redaction == "ZK":
                if os.path.isfile(path_thumb):
                    path_img_parent = os.path.join(p_out_c2pa_2_zk_src, filename)
                    path_man_c2pa_2 = os.path.join(p_out_c2pa_2_zk_src, f"{basename}.json")

                    # Inject c2pa_1
                    p = subprocess.run([f"{p_c2patool}", f"{path_img}", "--manifest", f"{path_man}", "--thumb", f"{path_thumb}", "--output" , f"{path_img_parent}", "--force"], capture_output=True)

                    # Generate c2pa_2
                    with open(p_c2pa_2_zk_template, "r") as c2pa_2_zk_template:
                        c2pa_2 = json.load(c2pa_2_zk_template)
                        
                        # Insert c2pa.created actions
                        m = _get_index_by_label(c2pa_2, "c2pa.actions")
                        n = [i for i, o in enumerate(c2pa_2["assertions"][m]["data"]["actions"]) if o["action"] == "c2pa.edited"][0]
                        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
                        c2pa_2["assertions"][m]["data"]["actions"][n]["when"] = now
                        c2pa_2["assertions"][m]["data"]["actions"][n]["parameters"]["zkProofCid"] = asset_info_ext.get(basename, {}).get("zkProofCid")

                        # print(json.dumps(c2pa_2, indent=2))
                        with open(path_man_c2pa_2, "w") as man:
                            json.dump(c2pa_2, man)

                        # Inject c2pa_2
                        img_parent_name = f"{basename}.png" # The parent file is assumed at the same directory as the manifest and we cannot specific full path
                        p = subprocess.run([f"{p_c2patool}", f"{path_zk_redacted}", "--manifest", f"{path_man_c2pa_2}", "--parent", f"{img_parent_name}", "--output" , f"{path_out_c2pa_2_zk}", "--force"], capture_output=True)
                        with open(path_out_c2pa_2_zk_man, "w") as f:
                            p = subprocess.run([f"{p_c2patool}", f"{path_out_c2pa_2_zk}", "--detailed"], stdout=f)
                else:
                    raise Exception("Missing thumbnail for image that requires redaction")

def _generate_layer3_out_from_src(archive_manifests, archive_manifests_related, asset_info_ext):
    # Generate layer3 for assets in path_c2pa_1_src
    for filename in os.listdir(path_c2pa_1_src):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            source_id = os.path.basename(filename).split(".")[0]
            ext = os.path.basename(filename).split(".")[1]

            path_asset_img = os.path.join(path_c2pa_1_src, f"{source_id}.{ext}")
            path_asset_info = os.path.join(path_c2pa_1_src, f"{source_id}.json")
            with open(path_asset_info, "r") as f:
                asset_info = json.load(f)
                with open(path_layer3_template, "r") as layer3_template:
                    # Select archive manifest of main asset
                    m = _get_index_by_label(asset_info, "org.starlinglab.integrity")
                    n = [i for i, o in enumerate(asset_info["assertions"][m]["data"]["starling:archives"]) if o["sourceId"]["key"] == "data_id" and o["sourceId"]["value"] == source_id][0]
                    asset_archive_manifest = asset_info["assertions"][m]["data"]["starling:archives"][n] # TODO: get this from file
                    # print(asset_archive_manifest)
                    info_ext = asset_info_ext.get(source_id)

                    # TODO: Get image information
                    with Image.open(path_asset_img) as asset_img:
                        w, h = asset_img.size
                        asset_dimensions = f"{w} x {h}"
                        asset_format = asset_img.get_format_mimetype()

                    # Insert main asset information
                    layer3 = json.load(layer3_template)
                    layer3["description"] = info_ext.get("description")
                    layer3["assetCid"] = asset_archive_manifest["archiveEncrypted"]["cid"]
                    layer3["caption"]["captionText"] = info_ext.get("captionText")
                    layer3["caption"]["originalUrl"] = info_ext.get("originalUrl")

                    layer3["assetDetails"]["dimensions"] = asset_dimensions # TODO
                    layer3["assetDetails"]["format"] = asset_format # TODO
                    layer3["c2pa"]["assetFile"] = f"{source_id}.{ext}"
                    layer3["c2pa"]["manifestFile"] = f"{source_id}-manifest.json"

                    layer3["captureDate"] = info_ext.get("captureDate")
                    layer3["capturedBy"] = info_ext.get("capturedBy")

                    location = info_ext.get("countryName")
                    if info_ext.get("city"):
                        location = f"{info_ext.get('city')}, {info_ext.get('provinceState')}, {info_ext.get('countryName')}"
                    elif info_ext.get("provinceState"):
                        location = f"{info_ext.get('provinceState')}, {info_ext.get('countryName')}"
                    layer3["location"] = location

                    # Insert registration records
                    registration_records = asset_archive_manifest["registrationRecords"]
                    layer3["registrationRecords"]["openTimestamps"]["sha256"] = registration_records["openTimestamps"]["sha256"]
                    layer3["registrationRecords"]["openTimestamps"]["block"] = registration_records["openTimestamps"]["block"]
                    layer3["registrationRecords"]["numbersProtocol"]["tx"] = registration_records["numbersProtocol"]["numbersTxHash"]
                    layer3["registrationRecords"]["numbersProtocolAvalanche"]["tx"] = registration_records["numbersProtocol"]["avalancheTxHash"]
                    layer3["registrationRecords"]["iscn"]["iscnId"] = registration_records["iscn"]["iscnId"]
                    layer3["registrationRecords"]["iscn"]["tx"] = registration_records["iscn"]["txHash"]

                    # Insert storage records
                    layer3["storageRecords"]["ipfs"]["cid"] = info_ext.get("ipfsCid")
                    layer3["storageRecords"]["filecoin"]["pieceCid"] = info_ext.get("filecoinPieceCid")
                    layer3["storageRecords"]["storj"]["path"] = info_ext.get("storjPath")

                    # Insert c2pa manifests
                    layer3["verifiedBy"] = []
                    if info_ext.get("c2paManifest1"):
                        c2pa_1 = {
                            "name": info_ext.get("c2paManifest1"),
                            "value": "Starling Lab Bijeljina Investigation",
                            "file": "starling-lab-bijeljina-investigation.cert.pem"
                        }
                        layer3["verifiedBy"].append(c2pa_1)
                    if info_ext.get("c2paManifest2"):
                        if info_ext.get("c2paManifest2") == "ZK":
                            c2pa_2 = {
                                "name": info_ext.get("c2paManifest2"),
                                "value": "Starling Lab Bijeljina Investigation",
                                "file": "starling-lab-bijeljina-investigation.cert.pem"
                            }
                        else:
                            c2pa_2 = {
                                "name": info_ext.get("c2paManifest2"),
                                "value": "Adobe Photoshop",
                                "file": "adobe-photoshop.cert.pem"
                            } 
                        layer3["verifiedBy"].append(c2pa_2)
                    if info_ext.get("c2paManifest3"):
                        c2pa_3 = {
                            "name": info_ext.get("c2paManifest3"),
                            "value": "Adobe Photoshop",
                            "file": "adobe-photoshop.cert.pem"
                        }
                        layer3["verifiedBy"].append(c2pa_3)

                    # TODO: Insert attestation assets information
                    layer3["attestations"] = []
                    # layer3["attestations"].append(attestation)

                    # print(json.dumps(layer3, indent=2))
                    with open(os.path.join(path_layer3_out, f"{source_id}.json"), "w") as man:
                        json.dump(layer3, man)


###################
# GENERATE ASSETS #
###################

# Index archive manifests from path_archive_manifests
archive_manifests = ArchiveManifests(p_in_archive_manifests)
archive_manifests_related = ArchiveManifests(p_in_archive_manifests_related)

with open(p_asset_info_ext, "r") as f:
    asset_info_ext = json.load(f)["assetInfoExt"]
    if len(sys.argv) > 1:
        if  sys.argv[1] == "c2pa":
            _generate_c2pa_out_from_src(archive_manifests, archive_manifests_related, asset_info_ext)
        if sys.argv[1] == "layer3":
            _generate_layer3_out_from_src(archive_manifests, archive_manifests_related, asset_info_ext)
    else:
        print("Specify option: [ c2pa layer3 ]")