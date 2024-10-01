#!/bin/bash
# Build ARO in an arbitrary directory and create a container tagged with
# branch and commit hash. Works on git worktrees too.
#
# Usage: aro-build PATH [GO_TOOLSET_VERSION] [UBI_MINIMAL_VERSION] [GOLANGCI_LINT_VERSION]

set -euo pipefail
IMG_GO_TOOLSET="docker://registry.access.redhat.com/ubi8/go-toolset:${2:-1.18.4}"
IMG_UBI="docker://registry.access.redhat.com/ubi8/ubi-minimal:${3:-latest}"
IMG_GOLANGCI="docker://docker.io/golangci/golangci-lint:${4:-v1.55.0}"

SRC_DIR="$(readlink -f ${1})"
CONTAINERFILE="$(dirname $(readlink -f $0))/Containerfile.aro"
cd "$SRC_DIR"
if [ -f .git ]; then
    # worktree magic
    HOST_GITDIR="$(readlink -f $(sed 's/gitdir: //' .git))"
    GITDIR="/git/worktree/"
    HOST_COMMONDIR="$(readlink -f ${HOST_GITDIR}/$(cat ${HOST_GITDIR}/commondir))"
    COMMONDIR="/git/basetree/"
fi
BRANCH="$(git branch --show-current)"
REV="$(git rev-parse HEAD)"
TAG="${BRANCH}-${REV}"
RELEASE="$(git describe --exact-match 2>/dev/null ||:)"
if [ "$RELEASE" != "" ]; then
    TAG="${RELEASE}"
fi
TAG_BRANCH_FLAG="-t ${BRANCH}"
if [ "$BRANCH" == "" ]; then
    TAG_BRANCH_FLAG=""
fi
echo Building aro:${TAG} from $SRC_DIR

podman run \
    --rm \
    --volume "${SRC_DIR}:/app:O" \
    --workdir /app \
    --network=none \
    --pull=newer \
    "${IMG_GOLANGCI}" golangci-lint run -v ||:
buildah build \
    --file  "${CONTAINERFILE}" \
    --volume "${SRC_DIR}:/app/src:O" \
    $(if [ "${HOST_COMMONDIR}" != "" ]; \
        then echo --volume "${HOST_COMMONDIR}:${COMMONDIR}:O" --build-arg "COMMONDIR=${COMMONDIR}"; \
    fi) \
    $(if [ "${HOST_GITDIR}" != "" ]; \
        then echo --volume "${HOST_GITDIR}:${GITDIR}:O" --build-arg "GITDIR=${GITDIR}"; \
    fi) \
    --build-context "baseimg=${IMG_GO_TOOLSET}" \
    --build-context "ubi=${IMG_UBI}" \
    --build-arg "ARO_VERSION=${TAG}" \
    -t "aro:${TAG}" $TAG_BRANCH_FLAG \
    --pull \
    "${SRC_DIR}"
    # Network is needed to pull gotest.tools/gotestsum
    # --network none \
echo localhost/aro:${TAG}
