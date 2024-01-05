#!/bin/bash
if [ -f "~/Projects/Azure/ARO-RP/secrets.env" ]; then
  pushd ~/Projects/Azure/ARO-RP/
  env -i bash --noprofile --norc -c "source ./env; set | grep -E -v -e '^(BASH|SHELL|SHLVL|TERM|UID|EUID|IFS|OPTERR|OPTIND|PATH|HOSTNAME|DIRSTACK|GROUPS|PPID|PWD|HOSTTYPE|MACHTYPE|OSTYPE|PS4|_=)'" > secrets.env
  popd
fi

LABEL="${1:-latest}"
podman run \
  --rm \
  -it \
  --env-file ~/Projects/Azure/ARO-RP/secrets.env \
  --secret=proxy-crt,type=mount,target=/secrets/proxy.crt \
  --secret=proxy-client-key,type=mount,target=/secrets/proxy-client.key \
  --secret=proxy-client-crt,type=mount,target=/secrets/proxy-client.crt \
  localhost/aro:${LABEL} \
  ${@:2}
