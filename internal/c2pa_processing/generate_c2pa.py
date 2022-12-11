from datetime import datetime
import io
import json
import os
import shutil
import subprocess
import tempfile
import zipfile

path_c2patool = os.path.abspath("c2patool/c2patool_starling_mac_universal_v0.3.9")
path_default = "assets/default/"
path_redaction_photoshop = "assets/redaction_photoshop/"
path_redaction_zk = "assets/redaction_zk/"

def _get_index_by_label(c2pa, label):
    return [i for i, o in enumerate(c2pa["assertions"]) if o["label"] == label][0]

def _generate_c2pa_1_src_from_archive(path_archive, path_c2pa_1_template, path_c2pa_1_src):
    with open(path_c2pa_1_template, "r") as c2pa_1_template:
        c2pa_1 = json.load(c2pa_1_template)

        with zipfile.ZipFile(path_archive) as zf:
            sourceId = None
            for filename in zf.namelist():
                if filename.endswith("-meta-content.json"):
                    f = zf.read(filename)
                    content_metadata = json.loads(f).get("contentMetadata")
                    sourceId = content_metadata.get("sourceId").get("value")
                    if sourceId is None:
                        raise Exception("Missing sourceId")
                                        
                    m = _get_index_by_label(c2pa_1, "stds.schema-org.CreativeWork")
                    c2pa_1["assertions"][m]["data"]["author"][0]["@type"] = content_metadata.get("author").get("@type")
                    c2pa_1["assertions"][m]["data"]["author"][0]["identifier"] = content_metadata.get("author").get("identifier")
                    c2pa_1["assertions"][m]["data"]["author"][0]["name"] = content_metadata.get("author").get("name")

                    m = _get_index_by_label(c2pa_1, "c2pa.actions")
                    n = [i for i, o in enumerate(c2pa_1["assertions"][m]["data"]["actions"]) if o["action"] == "c2pa.created"][0]
                    c2pa_1["assertions"][m]["data"]["actions"][n]["when"] = content_metadata.get("dateCreated")
                    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
                    tmp = [i for i, o in enumerate(c2pa_1["assertions"][m]["data"]["actions"]) if o["action"] == "c2pa.converted"]
                    if tmp:
                        n = tmp[0]
                        c2pa_1["assertions"][m]["data"]["actions"][n]["when"] = now
                    tmp = [i for i, o in enumerate(c2pa_1["assertions"][m]["data"]["actions"]) if o["action"] == "c2pa.resized"]
                    if tmp:
                        n = tmp[0]
                        c2pa_1["assertions"][m]["data"]["actions"][n]["when"] = now

                    m = _get_index_by_label(c2pa_1, "org.starlinglab.integrity")
                    c2pa_1["assertions"][m]["data"]["starling:identifier"] = content_metadata.get("sourceId").get("value")
                    c2pa_1["assertions"][m]["data"]["starling:signatures"] = []
                    for sig in content_metadata.get("validatedSignatures"):
                        x = {}
                        if sig.get("provider"): x["starling:provider"] = sig.get("provider")
                        if sig.get("algorithm"): x["starling:algorithm"] = sig.get("algorithm")
                        if sig.get("publicKey"): x["starling:publicKey"] = sig.get("publicKey")
                        if sig.get("signature"): x["starling:signature"] = sig.get("signature")
                        if sig.get("authenticatedMessage"): x["starling:authenticatedMessage"] = sig.get("authenticatedMessage")
                        if sig.get("authenticatedMessageDescription"): x["starling:authenticatedMessageDescription"] = sig.get("authenticatedMessageDescription")
                        if sig.get("custom"): x["starling:custom"] = sig.get("custom")
                        c2pa_1["assertions"][m]["data"]["starling:signatures"].append(x)
                    c2pa_1["assertions"][m]["data"]["starling:archives"] = []
                    # TODO

                    # print(json.dumps(c2pa_1, indent=2))
                    with open(os.path.join(path_c2pa_1_src, f"{sourceId}.json"), "w") as man:
                        json.dump(c2pa_1, man)

            for filename in zf.namelist():
                if filename.endswith(".jpg") or filename.endswith(".png"):
                    if sourceId is None:
                        raise Exception("Missing sourceId")
                    ext = os.path.basename(filename).split(".")[1]
                    with zf.open(filename) as zimg, open(os.path.join(path_c2pa_1_src, f"{sourceId}.{ext}"), "wb") as img:
                        shutil.copyfileobj(zimg, img)

def _generate_c2pa_1(path_assets):
    path_archives = os.path.join(path_assets, "archives")
    path_c2pa_1_src = os.path.join(path_assets, "c2pa_1_src")
    path_c2pa_1_out = os.path.join(path_assets, "c2pa_1_out")
    path_c2pa_1_template = os.path.join(path_assets, "c2pa_1_template.json")
    
    # Generate intermediate files for c2pa injection
    for archive in os.listdir(path_archives):
        if archive.endswith(".zip"):
            path_archive = os.path.join(path_archives, archive)
            _generate_c2pa_1_src_from_archive(path_archive, path_c2pa_1_template, path_c2pa_1_src)

            break # TODO: remove

    # Generate c2pa injected assets in path_c2pa_1_out
    for filename in os.listdir(path_c2pa_1_src):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            basename = os.path.basename(filename).split(".")[0]
            ext = os.path.basename(filename).split(".")[1]

            path_out = os.path.join(path_c2pa_1_out, filename)
            path_out_man = os.path.join(path_c2pa_1_out, f"{basename}.json")
            path_img = os.path.join(path_c2pa_1_src, filename)
            path_man = os.path.join(path_c2pa_1_src, f"{basename}.json")
            path_thumb = os.path.join(path_c2pa_1_src, f"{basename}.thumb")
            if os.path.isfile(path_thumb):
                p = subprocess.run([f"{path_c2patool}", f"{path_img}", "--manifest", f"{path_man}", "--thumb", f"{path_thumb}", "--output" , f"{path_out}", "--force"])
            else:
                p = subprocess.run([f"{path_c2patool}", f"{path_img}", "--manifest", f"{path_man}", "--output" , f"{path_out}", "--force"])
            
            # Write detailed c2pa manifest out to file
            with open(path_out_man, "w") as f:
                p = subprocess.run([f"{path_c2patool}", f"{path_out}", "--detailed"], stdout=f)

_generate_c2pa_1(path_default)
# _generate_c2pa_1(path_redaction_photoshop)
# _generate_c2pa_1(path_redaction_zk)