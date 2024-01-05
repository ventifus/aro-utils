#!/bin/python3
from argparse import ArgumentParser
from os import execvp, environ
from pathlib import Path
from dataclasses import dataclass
from sys import stdout, stderr
from tempfile import TemporaryFile

ARO_SECRETS = environ.get("ARO_SECRETS")


def sanitize_container_name(c: str) -> str:
    outstr = ""
    for i in range(len(c)):
        if not (c[i].isalpha() or c[i].isnumeric() or c[i] in ("-", "_", ".")):
            outstr += "_"
        else:
            outstr += c[i]
    return outstr


def main():
    args = ArgumentParser(description="Run an ARO container")
    args.add_argument(
        "-e",
        "--env",
        action="append",
        metavar="NAME=VALUE",
        help="Set environment variables in container",
    )
    args.add_argument(
        "--env-file",
        metavar="FILE",
        type=Path,
        default=ARO_SECRETS,
        help="Read in a file of environment variables",
    )
    args.add_argument(
        "-v",
        "--volume",
        action="append",
        metavar="HOSTPATH:CONTAINERPATH",
        help="Bind mount a volume into the container",
    )
    args.add_argument(
        "-n",
        "--net",
        "--network",
        metavar="NETWORK",
        help="Connect a container to a network",
    )
    args.add_argument(
        '--random-port',
        action="store_true",
        help="Listen on random ports"
    )
    args.add_argument(
        '--trustcert',
        type=Path,
        help="Add an additional root certificate"

    )
    args.add_argument("label", metavar="LABEL", default="latest", help="Run this label")
    args.add_argument("-i", "--image", metavar="IMAGE", help="Run this image")
    args.add_argument("-k", "--kubeconfig", metavar="FILE", type=Path, help="Provide a kubeconfig to the container")
    args.add_argument(
        "-p", "--podman", metavar="ARG", action="append", help="Custom podman argument"
    )
    args.add_argument(
        "cmd",
        metavar="COMMAND",
        nargs="*",
        help="Pass these arguments to the container",
    )

    @dataclass
    class Namespace:
        env: list[str]
        env_file: Path
        volume: list[str]
        image: str
        net: str
        label: str
        podman: list[str]
        cmd: list[str]
        random_port: bool
        trustcert: Path
        kubeconfig: Path

    ns: Namespace = args.parse_args()

    podman_args = [
        "--rm",
        "--secret=proxy-crt,type=mount,target=/secrets/proxy.crt",
        "--secret=proxy-client-key,type=mount,target=/secrets/proxy-client.key",
        "--secret=proxy-client-crt,type=mount,target=/secrets/proxy-client.crt",
    ]

    if ns.env_file:
        env_file: Path = ns.env_file.expanduser().resolve()
        podman_args.append(f"--env-file={env_file}")
    else:
        print("NOTE: Inheriting environment")
        podman_args.append("--env-host")

    if "TERM" in environ:
        podman_args.append("-it")

    if ns.volume:
        for vol in ns.volume:
            v = vol.split(":")
            v[0] == Path(v[0]).expanduser().resolve()
            podman_args.append("--volume=" + ":".join(v))

    if ns.env:
        for e in ns.env:
            podman_args.append(f"--env={e}")

    print(f"Loading environment {ns.env_file}")

    if ns.image:
        image = ns.image
        container_name = image
        ns.cmd.insert(
            0, ns.label
        )  # If -i is specified, then the first positional arg isn't actually "image" anymore, it's the first command.
    else:
        container_name = "aro." + ns.label
        image = f"localhost/aro:{ns.label}"

    if ns.net:
        podman_args.append(f"--network={ns.net}")
    else:
        podman_args.append("--network=host")

    basecmd = ""
    if ns.cmd:
        for cmd in ns.cmd:
            if not cmd.startswith("-"):
                basecmd = cmd
                break

    if ns.trustcert:
        hostcerts = Path("/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem")
        tmpfile = ns.trustcert.with_name(ns.trustcert.name + ".root")
        with tmpfile.open("wb") as tmp:
            tmp.write(hostcerts.read_bytes())
            tmp.write(ns.trustcert.read_bytes())
            tmp.flush()
            podman_args.append(f"--volume={tmpfile.absolute()}:/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem:z")


    if basecmd == "rp":
        podman_socket = Path(
            environ.get("XDG_RUNTIME_DIR", "/var/run/"), "podman/podman.sock"
        )
        podman_args.append(f"--volume={podman_socket}:/run/podman.sock")
        podman_args.append("--env=ARO_PODMAN_SOCKET=unix:/run/podman.sock")
        podman_args.append(
            "--env=CONTAINER_HOST=unix:/run/podman.sock"
        )  # Podman's environment variable for podman-remote
        podman_args.append(
            "--security-opt=label=disable"
        )  # Allow the container to connect to the podman socket by not applying a container selinux label (otherwise the socket will have to be relabeled.)

    if (ns.net and "host" not in ns.net) or ns.random_port:
        podman_args.append("--expose=6060")
        podman_args.append("--publish=127.0.0.1::6060")

        if basecmd == "rp":
            if ns.random_port:
                podman_args.append("--publish=127.0.0.1::8443")
            else:
                podman_args.append("--publish=127.0.0.1:8443:8443")
        elif basecmd == "portal":
            if ns.random_port:
                podman_args.append("--publish=127.0.0.1::8444")
            else:
                podman_args.append("--publish=127.0.0.1:8444:8444")

    if ns.kubeconfig:
        kubeconfig = ns.kubeconfig.expanduser().resolve()
        podman_args.append("--env=KUBECONFIG=/kubeconfig")
        podman_args.append(f"--volume={kubeconfig}:/kubeconfig:z")

    if ns.podman:
        podman_args = podman_args + ns.podman

    container_name = sanitize_container_name(container_name + "." + basecmd)
    exec_args = (
        ["podman", "run", f"--name={container_name}"] + podman_args + [image] + ns.cmd
    )
    print("EXEC", " ".join(exec_args))
    stdout.flush()
    stderr.flush()
    execvp("podman", exec_args)


if __name__ == "__main__":
    main()
