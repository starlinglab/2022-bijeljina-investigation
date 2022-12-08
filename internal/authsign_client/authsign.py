from datetime import datetime, timezone
import dotenv
import json
import os
import requests
import sys

dotenv.load_dotenv()
authsign_server_url = os.environ.get("AUTHSIGN_SERVER_URL")
authsign_auth_token = os.environ.get("AUTHSIGN_AUTH_TOKEN")

def authsign_sign(
    data_hash,
    authsign_file_path=None,
):
    """
    Sign the provided hash with authsign.
    Args:
        data_hash: hash of data as a hexadecimal string
        authsign_file_path: optional output path for authsign proof file (.authsign)
    Raises:
        Any errors with the request
    Returns:
        The signature proof as a string
    """

    dt = datetime.now()
    if isinstance(dt, datetime):
        # Convert to ISO format string
        dt = (
            dt.astimezone(timezone.utc)
            .replace(tzinfo=None)
            .isoformat(timespec="seconds")
            + "Z"
        )

    headers = {}
    if authsign_auth_token != "":
        headers = {"Authorization": f"bearer {authsign_auth_token}"}

    r = requests.post(
        authsign_server_url + "/sign",
        headers=headers,
        json={"hash": data_hash, "created": dt},
    )
    r.raise_for_status()
    authsign_proof = r.text

    # Write proof to file
    if authsign_file_path != None:
        with open(authsign_file_path, "w") as f:
            f.write(json.dumps(authsign_proof))
            f.write("\n")

    return authsign_proof


print(json.dumps(json.loads(authsign_sign(sys.argv[1], None)), indent=2))