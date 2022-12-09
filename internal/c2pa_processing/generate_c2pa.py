from datetime import datetime
import io
import json
import os
import tempfile
import zipfile

path_default = "assets/default/"
path_default_src = os.path.join(path_default, "src")
path_default_manifest_1_template = os.path.join(path_default, "manifest_1_template.json")

path_redaction_photoshop = "assets/redaction_photoshop/"
path_redaction_photoshop_src = os.path.join(path_redaction_photoshop, "src")
path_redaction_photoshop_manifest_1_template = os.path.join(path_redaction_photoshop, "manifest_1_template.json")

path_redaction_zk = "assets/redaction_zk/"
path_redaction_zk_src = os.path.join(path_redaction_zk, "src")
path_redaction_zk_manifest_1_template = os.path.join(path_redaction_zk, "manifest_1_template.json")

def _get_index_by_label(manifest, label):
    return [i for i, o in enumerate(manifest['assertions']) if o['label'] == label][0]

def _generate_manifest_1_from_template(path_manifest_1_template):
    for zfilename in os.scandir(path_default_src):
        with open(path_manifest_1_template, "r") as manifest_1_template:
            manifest_1 = json.load(manifest_1_template)

            with zipfile.ZipFile(zfilename) as zf:
                for filename in zf.namelist():
                    if filename.endswith('-meta-content.json'):
                        basename = os.path.basename(filename)
                        basefile = basename.split(".")[0]
                        f = zf.read(filename)
                        content_metadata = json.loads(f).get('contentMetadata')
                                            
                        m = _get_index_by_label(manifest_1, 'stds.schema-org.CreativeWork')
                        manifest_1['assertions'][m]['data']['author'][0]['@type'] = content_metadata.get('author').get('@type')
                        manifest_1['assertions'][m]['data']['author'][0]['identifier'] = content_metadata.get('author').get('identifier')
                        manifest_1['assertions'][m]['data']['author'][0]['name'] = content_metadata.get('author').get('name')

                        m = _get_index_by_label(manifest_1, 'c2pa.actions')
                        n = [i for i, o in enumerate(manifest_1['assertions'][m]['data']['actions']) if o['action'] == 'c2pa.created'][0]
                        manifest_1['assertions'][m]['data']['actions'][n]['when'] = content_metadata.get("dateCreated")
                        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
                        tmp = [i for i, o in enumerate(manifest_1['assertions'][m]['data']['actions']) if o['action'] == 'c2pa.converted']
                        if tmp:
                            n = tmp[0]
                            manifest_1['assertions'][m]['data']['actions'][n]['when'] = now
                        tmp = [i for i, o in enumerate(manifest_1['assertions'][m]['data']['actions']) if o['action'] == 'c2pa.resized']
                        if tmp:
                            n = tmp[0]
                            manifest_1['assertions'][m]['data']['actions'][n]['when'] = now

                        m = _get_index_by_label(manifest_1, 'org.starlinglab.integrity')
                        manifest_1['assertions'][m]['data']['starling:identifier'] = content_metadata.get('sourceId').get('value')
                        manifest_1['assertions'][m]['data']['starling:signatures'] = []
                        for sig in content_metadata.get('validatedSignatures'):
                            x = {}
                            if sig.get('provider'): x['starling:provider'] = sig.get('provider')
                            if sig.get('algorithm'): x['starling:algorithm'] = sig.get('algorithm')
                            if sig.get('publicKey'): x['starling:publicKey'] = sig.get('publicKey')
                            if sig.get('signature'): x['starling:signature'] = sig.get('signature')
                            if sig.get('authenticatedMessage'): x['starling:authenticatedMessage'] = sig.get('authenticatedMessage')
                            if sig.get('authenticatedMessageDescription'): x['starling:authenticatedMessageDescription'] = sig.get('authenticatedMessageDescription')
                            if sig.get('custom'): x['starling:custom'] = sig.get('custom')
                            manifest_1['assertions'][m]['data']['starling:signatures'].append(x)
                        manifest_1['assertions'][m]['data']['starling:archives'] = []

                        print(json.dumps(manifest_1, indent=2))

_generate_manifest_1_from_template(path_default_manifest_1_template)
_generate_manifest_1_from_template(path_redaction_photoshop_manifest_1_template)
_generate_manifest_1_from_template(path_redaction_zk_manifest_1_template)