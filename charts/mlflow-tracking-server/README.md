# MLflow Tracking Server Helm Chart

Deploy MLflow Tracking Server with OIDC authentication using [mlflow-oidc-auth](https://github.com/mlflow-oidc/mlflow-oidc-auth).

## Features

- **OIDC Authentication** - Secure access with any OpenID Connect provider
- **Flexible Secrets Management** - External secrets with multiple provider options
- **Kubernetes Secrets Provider** - Native support for mounted K8s secrets
- **Cloud Provider Support** - AWS Secrets Manager, Azure Key Vault, HashiCorp Vault
- **Artifact Storage** - Local, S3, Azure Blob, GCS support
- **Health Endpoints** - Built-in liveness (`/health/live`) and readiness (`/health/ready`) probes

---

## Prerequisites

1. **Kubernetes cluster** (1.21+)
2. **Helm** (3.0+)
3. **External Kubernetes Secret** with required credentials (see [Secrets](#secrets-configuration))

---

## Quick Start

### 1. Create Required Secret

```bash
kubectl create secret generic mlflow-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=OIDC_CLIENT_ID="your-client-id" \
  --from-literal=OIDC_CLIENT_SECRET="your-client-secret" \
  --from-literal=OIDC_USERS_DB_URI="postgresql://user:pass@host:5432/mlflow_auth" \
  --from-literal=MLFLOW_BACKEND_STORE_URI="postgresql://user:pass@host:5432/mlflow"
```

### 2. Install Chart

```bash
helm install mlflow ./charts/mlflow-tracking-server \
  --set secrets.externalSecretName=mlflow-secrets \
  --set config.data.OIDC_DISCOVERY_URL="https://your-oidc-provider/.well-known/openid-configuration"
```

---

## Configuration Reference

### MLflow Server Configuration (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `MLFLOW_HOST` | Host to bind | `0.0.0.0` |
| `MLFLOW_PORT` | Port to listen on | `8080` |
| `MLFLOW_WORKERS` | Number of worker processes | `4` |
| `MLFLOW_DEFAULT_ARTIFACT_ROOT` | Default artifact root for experiments | `mlflow-artifacts:/` |
| `MLFLOW_SERVE_ARTIFACTS` | Enable artifact serving proxy | `true` |
| `MLFLOW_ARTIFACTS_DESTINATION` | Where artifacts are stored | `/mlflow-data` |
| `MLFLOW_REGISTRY_STORE_URI` | Model registry database (optional) | Same as backend |

> [!NOTE]
> When `MLFLOW_SERVE_ARTIFACTS=true`, artifacts are proxied through MLflow. Set `MLFLOW_DEFAULT_ARTIFACT_ROOT=mlflow-artifacts:/` and configure `MLFLOW_ARTIFACTS_DESTINATION` to your actual storage (S3, Azure, GCS, local path).

### OIDC Authentication (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `OIDC_DISCOVERY_URL` | OIDC discovery endpoint URL | **Required** |
| `OIDC_PROVIDER_DISPLAY_NAME` | Login button text | `Sign in with OIDC` |
| `OIDC_SCOPE` | OAuth scopes (comma-separated) | `openid,profile,email,groups` |
| `OIDC_GROUPS_ATTRIBUTE` | Token attribute for groups | `groups` |
| `OIDC_REDIRECT_URI` | Callback URL (auto-detected if unset) | Auto |
| `OIDC_GROUP_DETECTION_PLUGIN` | Custom group detection plugin | - |

### Authorization (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `OIDC_GROUP_NAME` | Allowed groups (comma-separated) | `mlflow-users` |
| `OIDC_ADMIN_GROUP_NAME` | Admin groups (comma-separated) | `mlflow-admins` |
| `DEFAULT_MLFLOW_PERMISSION` | Default permission level | `MANAGE` |
| `PERMISSION_SOURCE_ORDER` | Permission resolution order | `user,group,regex,group-regex` |

**Permission Levels:** `NO_PERMISSIONS`, `READ`, `EDIT`, `MANAGE`

### UI Settings (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `EXTEND_MLFLOW_MENU` | Add OIDC auth menu items | `true` |
| `DEFAULT_LANDING_PAGE_IS_PERMISSIONS` | Permissions as landing page | `true` |
| `AUTOMATIC_LOGIN_REDIRECT` | Auto-redirect to OIDC login | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Database Migration (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `OIDC_ALEMBIC_VERSION_TABLE` | Alembic version table name | `alembic_version` |

---

## Secrets Configuration

### Required Secret Keys

| Key | Description | Classification |
|-----|-------------|----------------|
| `SECRET_KEY` | Session signing key | SECRET |
| `OIDC_CLIENT_ID` | OAuth client identifier | SENSITIVE |
| `OIDC_CLIENT_SECRET` | OAuth client secret | SECRET |
| `OIDC_USERS_DB_URI` | Auth database connection string | SENSITIVE |
| `MLFLOW_BACKEND_STORE_URI` | MLflow tracking database URI | SECRET |

### Option 1: Environment Variables (Default)

Secrets are injected as environment variables:

```yaml
secrets:
  externalSecretName: "mlflow-secrets"
  mountAsFiles:
    enabled: false
```

### Option 2: Kubernetes Secrets Provider (Recommended)

Secrets are mounted as files, using the native Kubernetes secrets provider:

```yaml
secrets:
  externalSecretName: "mlflow-secrets"
  mountAsFiles:
    enabled: true
    path: "/var/run/secrets/mlflow-oidc-auth"
```

This enables `CONFIG_K8S_SECRETS_ENABLED=true` and mounts secrets at the specified path.

---

## Example Secret Manifests

### Basic Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mlflow-secrets
type: Opaque
stringData:
  SECRET_KEY: "your-32-byte-hex-secret-key-here"
  OIDC_CLIENT_ID: "mlflow-client"
  OIDC_CLIENT_SECRET: "super-secret-client-secret"
  OIDC_USERS_DB_URI: "postgresql://mlflow:password@postgres:5432/mlflow_auth"
  MLFLOW_BACKEND_STORE_URI: "postgresql://mlflow:password@postgres:5432/mlflow"
```

### With External Secrets Operator

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: mlflow-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: mlflow-secrets
  data:
    - secretKey: SECRET_KEY
      remoteRef:
        key: mlflow/config
        property: secret_key
    - secretKey: OIDC_CLIENT_SECRET
      remoteRef:
        key: mlflow/oidc
        property: client_secret
    # ... additional keys
```

---

## Cloud Config Providers

The mlflow-oidc-auth plugin supports additional configuration providers. Enable them via environment variables in `config.data`:

### AWS Secrets Manager

```yaml
config:
  data:
    CONFIG_AWS_SECRETS_ENABLED: "true"
    CONFIG_AWS_SECRETS_NAME: "mlflow-oidc-auth"
    CONFIG_AWS_SECRETS_REGION: "us-east-1"

serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789:role/mlflow-role"
```

### Azure Key Vault

```yaml
config:
  data:
    CONFIG_AZURE_KEYVAULT_ENABLED: "true"
    CONFIG_AZURE_KEYVAULT_URL: "https://my-keyvault.vault.azure.net"

serviceAccount:
  create: true
  annotations:
    azure.workload.identity/client-id: "00000000-0000-0000-0000-000000000000"
```

### HashiCorp Vault

```yaml
config:
  data:
    CONFIG_VAULT_ENABLED: "true"
    CONFIG_VAULT_ADDR: "https://vault.example.com"
    CONFIG_VAULT_PATH: "secret/data/mlflow"
    CONFIG_VAULT_AUTH_METHOD: "kubernetes"
    CONFIG_VAULT_ROLE: "mlflow"
```

---

## Artifact Storage Examples

### Local Storage (with persistence)

```yaml
config:
  data:
    MLFLOW_DEFAULT_ARTIFACT_ROOT: "mlflow-artifacts:/"
    MLFLOW_SERVE_ARTIFACTS: "true"
    MLFLOW_ARTIFACTS_DESTINATION: "/mlflow-data"

persistence:
  enabled: true
  size: 50Gi
  storageClass: "standard"
```

### S3-Compatible Storage

```yaml
config:
  data:
    MLFLOW_DEFAULT_ARTIFACT_ROOT: "mlflow-artifacts:/"
    MLFLOW_SERVE_ARTIFACTS: "true"
    MLFLOW_ARTIFACTS_DESTINATION: "s3://my-bucket/mlruns"

# Ensure AWS credentials via:
# - Service account with IRSA
# - Environment variables
# - Instance profile
```

### Azure Blob Storage

```yaml
config:
  data:
    MLFLOW_DEFAULT_ARTIFACT_ROOT: "mlflow-artifacts:/"
    MLFLOW_SERVE_ARTIFACTS: "true"
    MLFLOW_ARTIFACTS_DESTINATION: "wasbs://container@storage.blob.core.windows.net/mlruns"
```

---

## Complete Example

```yaml
replicaCount: 2

image:
  registry: ghcr.io/mlflow-oidc
  name: mlflow-tracking-server
  tag: "2.17.0"

config:
  data:
    # MLflow Server
    MLFLOW_HOST: "0.0.0.0"
    MLFLOW_PORT: "8080"
    MLFLOW_WORKERS: "4"
    MLFLOW_DEFAULT_ARTIFACT_ROOT: "mlflow-artifacts:/"
    MLFLOW_SERVE_ARTIFACTS: "true"
    MLFLOW_ARTIFACTS_DESTINATION: "s3://mlflow-artifacts/runs"

    # OIDC Provider
    OIDC_DISCOVERY_URL: "https://login.microsoftonline.com/tenant-id/v2.0/.well-known/openid-configuration"
    OIDC_PROVIDER_DISPLAY_NAME: "Sign in with Microsoft"
    OIDC_SCOPE: "openid,profile,email"
    OIDC_GROUPS_ATTRIBUTE: "groups"
    OIDC_GROUP_DETECTION_PLUGIN: "mlflow_oidc_auth.plugins.group_detection_microsoft_entra_id"

    # Authorization
    OIDC_GROUP_NAME: "mlflow-users,data-scientists"
    OIDC_ADMIN_GROUP_NAME: "mlflow-admins"
    DEFAULT_MLFLOW_PERMISSION: "READ"

secrets:
  externalSecretName: "mlflow-secrets"
  mountAsFiles:
    enabled: true

serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789:role/mlflow-s3-access"
```

---

## Helm Commands

```bash
# Lint
helm lint ./charts/mlflow-tracking-server

# Template preview
helm template mlflow ./charts/mlflow-tracking-server -f values.yaml

# Install
helm install mlflow ./charts/mlflow-tracking-server -f values.yaml

# Upgrade
helm upgrade mlflow ./charts/mlflow-tracking-server -f values.yaml

# Uninstall
helm uninstall mlflow
```

---

## Troubleshooting

### Pod fails to start

1. Check if secret exists: `kubectl get secret mlflow-secrets`
2. Verify all required keys are present
3. Check pod logs: `kubectl logs -l app.kubernetes.io/name=mlflow-tracking-server`

### OIDC authentication fails

1. Verify `OIDC_DISCOVERY_URL` is accessible from the cluster
2. Check `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET` match your provider
3. Ensure redirect URI is correctly configured in your OIDC provider

### Database connection errors

1. Verify `OIDC_USERS_DB_URI` and `MLFLOW_BACKEND_STORE_URI` are correct
2. Check network policies allow database access
3. Verify database credentials

---

## References

- [mlflow-oidc-auth Documentation](https://github.com/mlflow-oidc/mlflow-oidc-auth)
- [Config Providers](https://github.com/mlflow-oidc/mlflow-oidc-auth/tree/main/mlflow_oidc_auth/config_providers)
- [MLflow CLI Reference](https://mlflow.org/docs/latest/api_reference/cli.html#mlflow-server)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)

---

## License

Apache 2.0
