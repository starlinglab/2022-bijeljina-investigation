import json
import os
import urllib.parse

p_layer3 = "../../layer3"

e_opentimestamps = "https://www.blockchain.com/explorer/blocks/btc/"
e_numbers = "https://mainnet.num.network/tx/"
e_avalanche = "https://snowtrace.io/tx/"
e_iscn = "https://app.like.co/view/"
e_ipfs = "https://ipfs.io/ipfs/"
e_filecoin = "https://filecoin.tools/"
e_storj = "https://link.storjshare.io/s/"

print(f"data_id,type,record_id,opentimestamps,numbers,avalanche,iscn,ipfs,filecoin,storj")
for filename in os.listdir(p_layer3):
    if filename.endswith(".json"):
        with open(os.path.join(p_layer3, filename), "r") as f:
            layer3 = json.load(f)

            opentimestamps = None
            numbers = None
            avalanche = None
            iscn = None
            ipfs = None
            filecoin = None
            storj = None

            r = layer3.get('registrationRecords', {})
            s = layer3.get('storageRecords', {})
            if r.get('openTimestamps', {}).get('block'): opentimestamps = f"{e_opentimestamps}{r.get('openTimestamps', {}).get('block')}"
            if r.get('numbersProtocol', {}).get('tx'): numbers = f"{e_numbers}{r.get('numbersProtocol', {}).get('tx')}"
            if r.get('numbersProtocolAvalanche', {}).get('tx'): avalanche = f"{e_avalanche}{r.get('numbersProtocolAvalanche', {}).get('tx')}"
            if r.get('iscn', {}).get('iscnId'): iscn = f"{e_iscn}{urllib.parse.quote(r.get('iscn', {}).get('iscnId'), safe='')}"
            if s.get('ipfs', {}).get('cid'): ipfs = f"{e_ipfs}{s.get('ipfs', {}).get('cid')}"
            if s.get('filecoin', {}).get('pieceCid'): filecoin = f"{e_filecoin}{s.get('filecoin', {}).get('pieceCid')}"
            if s.get('storj', {}).get('path'): storj = f"{e_storj}{urllib.parse.quote(s.get('storj', {}).get('path'), safe='')}"

            print(f"{layer3['c2pa']['assetFile'].split('.')[0]},{'Primary'},{layer3['assetCid']},{opentimestamps if opentimestamps else ''},{numbers if numbers else ''},{avalanche if avalanche else ''},{iscn if iscn else ''},{ipfs if ipfs else ''},{filecoin if filecoin else ''},{storj if storj else ''}")
    
            for a in layer3.get("attestations", []):
                r = layer3.get('records', {})
                if r.get('openTimestamps', {}).get('block'): opentimestamps = f"{e_opentimestamps}{r.get('openTimestamps', {}).get('block')}"
                if r.get('numbersProtocol', {}).get('tx'): numbers = f"{e_numbers}{r.get('numbersProtocol', {}).get('tx')}"
                if r.get('numbersProtocolAvalanche', {}).get('tx'): avalanche = f"{e_avalanche}{r.get('numbersProtocolAvalanche', {}).get('tx')}"
                if r.get('iscn', {}).get('iscnId'): iscn = f"{e_iscn}{urllib.parse.quote(r.get('iscn', {}).get('iscnId'), safe='')}"
                if s.get('ipfs', {}).get('cid'): ipfs = f"{e_ipfs}{s.get('ipfs', {}).get('cid')}"
                if s.get('filecoin', {}).get('pieceCid'): filecoin = f"{e_filecoin}{s.get('filecoin', {}).get('pieceCid')}"
                if s.get('storj', {}).get('path'): storj = f"{e_storj}{urllib.parse.quote(s.get('storj', {}).get('path'), safe='')}"

                print(f",{a['name']},{a['value']},{opentimestamps if opentimestamps else ''},{numbers if numbers else ''},{avalanche if avalanche else ''},{iscn if iscn else ''},{ipfs if ipfs else ''},{filecoin if filecoin else ''},{storj if storj else ''}")
        