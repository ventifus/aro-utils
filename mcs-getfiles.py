#!/usr/bin/python3
from base64 import b64decode
from sys import argv, stderr, stdin, stdout
from typing import Any, Dict, List
from urllib.parse import unquote

import yaml


def decode_data(data: str) -> str:
    if data[0:5] == "data:":
        # data url
        comma_index = data.find(",")
        data_type = data[5:comma_index]
        if data_type == "":
            return unquote(data[comma_index+1:])
        else:
            data_types = data_type.split(";")
            charset = "utf-8"
            for t in data_types:
                if t.startswith("charset="):
                    charset = t[8:]
            print(f"### {data_types}")
            if "base64" in data_types:
                in_data = data[comma_index+1:]
                out_data: bytes = b64decode(in_data)
                return out_data.decode(encoding=charset)
                # print(b64decode(data[comma_index+1:], stdout))
            else:
                return unquote(data[comma_index+1:])
    else:
        print("No type specified, assuming url-encoding", file=stderr)
        return unquote(data)

if __name__ == "__main__":
    search_files: list[str] = []
    if len(argv) > 1:
        search_files = argv[1:]
    y: Dict[str, Any] = yaml.safe_load(stdin)
    if type(y) != dict:
        print(f"Input was not yaml, detected {type(y)}.")
        exit(1)
    kind = y.get('kind')
    machineconfigs: List[Dict[str, Any]] = list()
    if kind == "MachineConfig":
        machineconfigs.append(y)
    if kind == "List" and "items" in y:
        machineconfigs = y["items"]
    for mc in machineconfigs:
        if "metadata" not in mc:
            print("Malformed document: entry has no metadata", file=stderr)
            continue
        metadata = mc['metadata']
        kind = mc.get('kind')
        print(f"### {metadata.get('name')} #{metadata.get('generation')}   created={metadata.get('creationTimestamp')}")
        if kind != "MachineConfig":
            print(f"Unsupported kind: {kind}")
            exit(1)
        for file in mc["spec"]["config"].get("storage", dict()).get("files", list()):
            file_name = file.get('path')
            if search_files:
                found = False
                for f in search_files:
                    if f in file_name:
                        found = True
                if not found:
                    continue
            contents = file["contents"]
            print("---")
            print(f"### [{metadata.get('name')}] {file_name}   [mode={file.get('mode')}, overwrite={file.get('overwrite')}]")
            source = contents.get("source")
            if source:
                print(decode_data(source), flush=True)
        units = mc["spec"]["config"].get("systemd", dict()).get("units", list())
        for unit in units:
            name = unit.get("name")
            if search_files:
                found = False
                for f in search_files:
                    if f in name:
                        found = True
                if not found:
                    continue
            print(f"### Systemd Unit {name} enabled={unit.get('enabled')}")
            for dropin in unit.get("dropins", list()):
                print(f"### {name}.d/{dropin.get('name')}")
                print(dropin["contents"], flush=True)