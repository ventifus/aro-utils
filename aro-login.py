#!/usr/bin/p#!/bin/bashython3

import json
import os

import openshift as oc  # type: ignore
from azure.identity import AzureCliCredential
from azure.mgmt.redhatopenshift import AzureRedHatOpenShiftClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.subscription import SubscriptionClient

for required_env in ("AZURE_SUBSCRIPTION_ID", "CLUSTER", "RESOURCEGROUP"):
    if not os.environ.get(required_env):
        print(f"Please set environment variable {required_env}.")
        exit(1)

cluster_info = {
    "subscription_id": os.environ["AZURE_SUBSCRIPTION_ID"],
    "name": os.environ["CLUSTER"],
    "resource-group": os.environ["RESOURCEGROUP"]
}

credential = AzureCliCredential()
resource_client = ResourceManagementClient(credential, cluster_info["subscription_id"])
shared_cluster_rg = resource_client.resource_groups.get(cluster_info["resource-group"])
aro_client = AzureRedHatOpenShiftClient(credential, cluster_info["subscription_id"])
shared_cluster_aro = aro_client.open_shift_clusters.get(cluster_info["resource-group"], cluster_info["name"])
print(f"Cluster {shared_cluster_aro.name} in {shared_cluster_aro.location}, provsioning state: {shared_cluster_aro.provisioning_state}")
# admin_creds = aro_client.open_shift_clusters.list_admin_credentials(shared_cluster["resource-group"], shared_cluster["name"])
creds = aro_client.open_shift_clusters.list_credentials(cluster_info["resource-group"], cluster_info["name"])

with oc.api_server(shared_cluster_aro.apiserver_profile.url) as api_server:
    oc.login(creds.kubeadmin_username, creds.kubeadmin_password)
    print("{}: {}".format(api_server.api_url, oc.get_server_version()))