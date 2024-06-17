import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
import lbrlabs_pulumi_eks as eks
import pulumi_kubernetes as k8s

PROJECT_NAME = pulumi.get_project()
STACK = pulumi.get_stack()
TAGS = {
    "environment": STACK,
    "project": PROJECT_NAME,
    "owner": "lbriggs",
}

TAILSCALE_CONFIG = pulumi.Config("tailscale")
TAILSCALE_OAUTH_CLIENT_ID = TAILSCALE_CONFIG.require("oauth_client_id")
TAILSCALE_OAUTH_CLIENT_SECRET = TAILSCALE_CONFIG.require_secret("oauth_client_secret")

CONFIG = pulumi.Config()

vpc = awsx.ec2.Vpc(
    f"vpc-{STACK}",
    cidr_block="10.0.0.0/16",
    subnet_strategy="Auto",
    subnet_specs=[
        awsx.ec2.SubnetSpecArgs(
            type=awsx.ec2.SubnetType.PUBLIC,
            cidr_mask=20,
            tags={"kubernetes.io/role/elb": "1", **TAGS},
        ),
        awsx.ec2.SubnetSpecArgs(
            type=awsx.ec2.SubnetType.PRIVATE,
            cidr_mask=19,
            tags={"kubernetes.io/role/internal-elb": "1", **TAGS},
        ),
    ],
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags=TAGS,
)

cluster = eks.Cluster(
    STACK,
    cluster_subnet_ids=vpc.public_subnet_ids,
    system_node_subnet_ids=vpc.private_subnet_ids,
    system_node_instance_types=["t3.medium"],
    system_node_desired_count=2,
    nginx_ingress_version="4.9.1",
    lets_encrypt_email="lee@tailscale.com",
    enable_external_dns=False,  # only supported oob with route53
    enable_cert_manager=False,  # only supported oob with route53
    enable_otel=False,
    ingress_config=eks.IngressConfigArgs(
        controller_replicas=2,
    ),
    tags=TAGS,
    enable_karpenter=True,
    lb_type="nlb",
)

pulumi.export("kubeconfig", cluster.kubeconfig)

provider = k8s.Provider(
    "k8s-provider",
    kubeconfig=cluster.kubeconfig,
    enable_server_side_apply=True,
    opts=pulumi.ResourceOptions(parent=cluster),
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
        "oauth": {
            "clientId": TAILSCALE_OAUTH_CLIENT_ID,
            "clientSecret": TAILSCALE_OAUTH_CLIENT_SECRET,
        },
        "operatorConfig": {
            "hostname": f"{PROJECT_NAME}-{STACK}-tailscale-operator",
            "tolerations": [
                {
                    "key": "node.lbrlabs.com/system",
                    "operator": "Equal",
                    "value": "true",
                    "effect": "NoSchedule",
                },
            ],
        },
    },
    opts=pulumi.ResourceOptions(provider=provider, parent=tailscale_ns),
)

gpu_nodes = eks.AttachedNodeGroup(
    "gpu",
    cluster_name=cluster.cluster_name,
    instance_types=["g6.8xlarge"],
    subnet_ids=vpc.private_subnet_ids,
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=1,
        max_size=1,
        min_size=1,
    ),
    disk_size=200,
    ami_type="AL2_x86_64_GPU",
    taints=[
        {
            "key": "nvidia.com/gpu",
            "value": "present",
            "effect": "NO_SCHEDULE",
        },
    ],
    opts=pulumi.ResourceOptions(
        parent=cluster,
        providers={"kubernetes": provider},
    ),
)

nvidia_ns = k8s.core.v1.Namespace(
    "nvidia-device-plugin",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="nvidia-device-plugin",
    ),
    opts=pulumi.ResourceOptions(parent=provider, provider=provider),
)

nvidia_plugin = k8s.helm.v3.Release(
    "nvidia-device-plugin",
    repository_opts=k8s.helm.v3.RepositoryOptsArgs(
        repo="https://nvidia.github.io/k8s-device-plugin",
    ),
    chart="nvidia-device-plugin",
    namespace=nvidia_ns.metadata.name,
    values={
        "gfd": {
            "enabled": True,
            "tolerations": [
                {
                    "key": "node.lbrlabs.com/system",
                    "operator": "Equal",
                    "value": "true",
                    "effect": "NoSchedule",
                },
                {
                    "key": "nvidia.com/gpu",
                    "operator": "Equal",
                    "value": "present",
                    "effect": "NoSchedule",
                },
            ],
        },
        "nfd": {
            "master": {
                "tolerations": [
                    {
                        "key": "node.lbrlabs.com/system",
                        "operator": "Equal",
                        "value": "true",
                        "effect": "NoSchedule",
                    },
                    {
                        "key": "nvidia.com/gpu",
                        "operator": "Equal",
                        "value": "present",
                        "effect": "NoSchedule",
                    },
                ],
            }
        },
    },
    opts=pulumi.ResourceOptions(parent=nvidia_ns, provider=provider),
)
