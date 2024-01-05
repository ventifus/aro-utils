#!/usr/bin/python3
from base64 import b64decode
from sys import argv, stderr, stdin, stdout
from typing import Any, Dict, List
from urllib.parse import unquote
from argparse import ArgumentParser
from fnmatch import fnmatch

import yaml

"""
usage: Pipe in yaml to stdin. For example, 
  $ oc get machineconfig 01-master-container-runtime -o yaml | machineconfig-getfiles.py

usage: machineconfig-getfiles [-h] [-l] [FILE ...]

Extracts files from MachineConfig yaml

positional arguments:
  FILE        a path or wildcard glob

options:
  -h, --help  show this help message and exit
  -l, --list  show only file names.
"""

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
            else:
                return unquote(data[comma_index+1:])
    else:
        print("No type specified, assuming url-encoding", file=stderr)
        return unquote(data)

EXAMPLE = """Pipe in yaml to stdin. For example, 
  $ oc get machineconfig 01-master-container-runtime -o yaml | machineconfig-getfiles.py
"""

if __name__ == "__main__":
    parser = ArgumentParser(prog="machineconfig-getfiles", description="Extracts files from MachineConfig yaml")
    parser.add_argument("file_globs", metavar="FILE", type=str, nargs="*", help="a path or wildcard glob")
    parser.add_argument("-l", "--list", dest="only_names", action="store_true", help="show only file names.")
    parser.usage = EXAMPLE + "\n" + parser.format_usage()
    args = parser.parse_args()
    search_files: list[str] = args.file_globs
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
        if args.only_names:
            print(f"{metadata.get('name')} #{metadata.get('generation')}   created={metadata.get('creationTimestamp')}")
        else:
            print(f"### {metadata.get('name')} #{metadata.get('generation')}   created={metadata.get('creationTimestamp')}")
        if kind != "MachineConfig":
            print(f"Unsupported kind: {kind}")
            exit(1)
        for file in mc["spec"]["config"].get("storage", dict()).get("files", list()):
            file_name = file.get('path')
            if search_files:
                found = False
                for f in search_files:
                    if fnmatch(file_name, f):
                        found = True
                if not found:
                    continue
            contents = file["contents"]
            mode = file.get('mode')
            mode_oct = oct(mode).replace("o", "")
            if args.only_names:
                
                print(f"    {file_name}   [{mode=} ({mode_oct}), overwrite={file.get('overwrite')}]")
                continue
            else:
                print("---")
                print(f"### [{metadata.get('name')}] {file_name}   [mode={mode=} ({mode_oct}), overwrite={file.get('overwrite')}]")
            source = contents.get("source")
            if source:
                print(decode_data(source), flush=True)
        units = mc["spec"]["config"].get("systemd", dict()).get("units", list())
        for unit in units:
            name = unit.get("name")
            contents = unit.get("contents")
            if search_files:
                found = False
                for f in search_files:
                    if fnmatch(name, f):
                        found = True
                if not found:
                    continue
            if args.only_names:
                print(f"    {name}   [enabled={unit.get('enabled')}]")
                continue
            else:
                print(f"### Systemd Unit {name}   [enabled={unit.get('enabled')}]")
                if contents:
                    print(decode_data(contents), flush=True)

            for dropin in unit.get("dropins", list()):
                print(f"### {name}.d/{dropin.get('name')}")
                print(dropin["contents"], flush=True)