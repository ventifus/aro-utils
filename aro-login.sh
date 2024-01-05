#!/bin/bash
set -eo pipefail

if [ "${CLUSTER}" == "" ]; then
    CLUSTER=shared-cluster
    RESOURCEGROUP=shared-cluster
fi

echo "[ Cluster ${CLUSTER} ]"
INFO=$(az aro show --name ${CLUSTER} --resource-group ${RESOURCEGROUP} -o json)
CREDS=$(az aro list-credentials --name ${CLUSTER} --resource-group ${RESOURCEGROUP} -o json)
KUBE_USER=$(jq -r .kubeadminUsername <<< ${CREDS} )
KUBE_PASS=$(jq -r .kubeadminPassword <<< ${CREDS} )
echo KubeadminUsername: ${KUBE_USER}
echo KubeadminPassword: ${KUBE_PASS}
echo Provisining State: $(jq -r .provisioningState <<< ${INFO} )
echo Console URL: $(jq -r .consoleProfile.url <<< ${INFO} )
API_URL=$(jq -r .apiserverProfile.url <<< ${INFO} )
echo API URL: ${API_URL}
CURRENT_CONTEXT=$(oc config current-context)
if [ $CURRENT_CONTEXT == $CLUSTER ]; then
    oc config set-credentials kube:admin --username $KUBE_USER --password $KUBE_PASS
else
    # oc config delete-context $CLUSTER
    oc login --username "${KUBE_USER}" --password "${KUBE_PASS}" ${API_URL}
    oc config rename-context $CURRENT_CONTEXT $CLUSTER
fi
oc get clusterversion && 
oc get co aro