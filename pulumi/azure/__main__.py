import pulumi
import pulumi_azure as azure
import pulumi_tls as tls
import pulumi_kubernetes as k8s

STACK = pulumi.get_stack()
PROJECT = pulumi.get_project()
LOCATION = "WestUS2"

CONFIG = pulumi.Config()

TAILSCALE_CONFIG = pulumi.Config("tailscale")
TAILSCALE_OAUTH_CLIENT_ID = TAILSCALE_CONFIG.require("oauth_client_id")
TAILSCALE_OAUTH_CLIENT_SECRET = TAILSCALE_CONFIG.require_secret("oauth_client_secret")

tags = {
    "project": PROJECT,
    "stack": STACK,
}

resource_group = azure.core.ResourceGroup(
    STACK,
    location=LOCATION,
)

ssh_key = tls.PrivateKey(
    f"{STACK}-aks-node-ssh-key",
    algorithm="RSA",
    rsa_bits=4096,
)

cluster = azure.containerservice.KubernetesCluster(
    "azure",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    dns_prefix=f"{PROJECT}-{STACK}",
    node_os_channel_upgrade="None",
    sku_tier="Standard",
    linux_profile=azure.containerservice.KubernetesClusterLinuxProfileArgs(
        admin_username="aks",
        ssh_key=azure.containerservice.KubernetesClusterLinuxProfileSshKeyArgs(
            key_data=ssh_key.public_key_openssh,
        ),
    ),
    storage_profile=azure.containerservice.KubernetesClusterStorageProfileArgs(
        blob_driver_enabled=True,
        snapshot_controller_enabled=True,
        file_driver_enabled=True,
    ),
    oidc_issuer_enabled=True,
    local_account_disabled=False,
    identity=azure.containerservice.KubernetesClusterIdentityArgs(
        type="SystemAssigned"
    ),
    default_node_pool=azure.containerservice.KubernetesClusterDefaultNodePoolArgs(
        name="system",
        node_count=1,
        max_count=5,
        min_count=1,
        vm_size="Standard_D4s_v3",
        enable_auto_scaling=True,
        tags=tags,
        temporary_name_for_rotation="temp",
        only_critical_addons_enabled=True,
    ),
    tags=tags,
    opts=pulumi.ResourceOptions(ignore_changes=["defaultNodePool.nodeCount"]),
)

app_nodes = azure.containerservice.KubernetesClusterNodePool(
    "app",
    kubernetes_cluster_id=cluster.id,
    vm_size="Standard_D4_v3",
    enable_auto_scaling=True,
    node_count=2,
    min_count=2,
    max_count=5,
    tags=tags,
    opts=pulumi.ResourceOptions(parent=cluster, ignore_changes=["nodeCount"]),
)

provider = k8s.Provider(
    "kube",
    kubeconfig=cluster.kube_config_raw,
)

tailscale_ns = k8s.core.v1.Namespace(
    "tailscale",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="tailscale"),
    opts=pulumi.ResourceOptions(provider=provider, parent=provider),
)

tailscale_operator = k8s.helm.v3.Release(
    "tailscale",
    repository_opts=k8s.helm.v3.RepositoryOptsArgs(
        repo="https://pkgs.tailscale.com/helmcharts",
    ),
    namespace=tailscale_ns.metadata.name,
    version="1.61.11",
    chart="tailscale-operator",
    values={
        "apiServerProxyConfig": {
          "mode": "true",
        },
        "oauth": {
            "clientId": TAILSCALE_OAUTH_CLIENT_ID,
            "clientSecret": TAILSCALE_OAUTH_CLIENT_SECRET,
        },
        "operatorConfig": {
            "hostname": f"aks-tailscale-operator",
        },
    },
    opts=pulumi.ResourceOptions(provider=provider, parent=tailscale_ns),
)

pulumi.export("kubeconfig", cluster.kube_config_raw)
