# MLflow Tracking Server Helm Chart

[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/mlflow-tracking-server)](https://artifacthub.io/packages/search?repo=mlflow-tracking-server)

Deploy MLflow Tracking Server with OIDC authentication using [mlflow-oidc-auth](https://github.com/mlflow-oidc/mlflow-oidc-auth).

## Features

- **OIDC Authentication** - Secure access with any OpenID Connect provider
- **Flexible Secrets Management** - External secrets with multiple injection methods
- **Secret Refs** - Inject individual env vars from external secrets via `secretKeyRef` lookups
- **Kubernetes Secrets Provider** - Native support for mounted K8s secrets
- **Cloud Provider Support** - AWS Secrets Manager, Azure Key Vault, HashiCorp Vault
- **Workspace / Multi-Tenancy** - Workspace-scoped resource isolation (MLflow >=3.10)
- **AI Gateway Permissions** - Control access to MLflow AI Gateway endpoints
- **Redis Caching** - Shared permission cache for multi-replica deployments
- **Webhook Management** - Workspace-scoped webhook support with encrypted secrets
- **Artifact Storage** - S3, Azure Blob, GCS support
- **Health Endpoints** - Built-in liveness (`/health/live`) and readiness (`/health/ready`) probes
- **JWT Audience Validation** - Optional `aud` claim enforcement for production security
- **Trusted Proxy Validation** - CIDR-based `X-Forwarded-*` header validation

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
> When `MLFLOW_SERVE_ARTIFACTS=true`, artifacts are proxied through MLflow. Set `MLFLOW_DEFAULT_ARTIFACT_ROOT=mlflow-artifacts:/` and configure `MLFLOW_ARTIFACTS_DESTINATION` to your actual storage (S3, Azure, GCS).

### OIDC Authentication (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `OIDC_DISCOVERY_URL` | OIDC discovery endpoint URL | **Required** |
| `OIDC_PROVIDER_DISPLAY_NAME` | Login button text | `Sign in with OIDC` |
| `OIDC_SCOPE` | OAuth scopes (comma-separated) | `openid,profile,email,groups` |
| `OIDC_GROUPS_ATTRIBUTE` | Token attribute for groups | `groups` |
| `OIDC_REDIRECT_URI` | Callback URL (auto-detected if unset) | Auto |
| `OIDC_AUDIENCE` | JWT audience validation (recommended for production) | - |
| `OIDC_GROUP_DETECTION_PLUGIN` | Custom group detection plugin | - |

### Authorization (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `OIDC_GROUP_NAME` | Allowed groups (comma-separated) | `mlflow-users` |
| `OIDC_ADMIN_GROUP_NAME` | Admin groups (comma-separated) | `mlflow-admins` |
| `DEFAULT_MLFLOW_PERMISSION` | Default permission level | `MANAGE` |
| `PERMISSION_SOURCE_ORDER` | Permission resolution order | `user,group,regex,group-regex` |

**Permission Levels:** `NO_PERMISSIONS`, `READ`, `USE`, `EDIT`, `MANAGE`

### Security (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `TRUSTED_PROXIES` | Trusted proxy CIDR ranges (comma-separated) | Empty (trust all) |
| `AUTOMATIC_LOGIN_REDIRECT` | Auto-redirect to OIDC login | `false` |

### Feature Flags (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `OIDC_GEN_AI_GATEWAY_ENABLED` | Enable AI Gateway permission management | `true` |
| `MLFLOW_ENABLE_WORKSPACES` | Enable multi-tenant workspace support (requires MLflow >=3.10) | `false` |

### Workspace Settings (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `OIDC_WORKSPACE_DEFAULT_PERMISSION` | Permission for auto-detected workspaces | `NO_PERMISSIONS` |
| `OIDC_WORKSPACE_CLAIM_NAME` | OIDC token claim for workspace detection | `workspace` |
| `OIDC_WORKSPACE_DETECTION_PLUGIN` | Custom workspace detection plugin | - |
| `WORKSPACE_CACHE_MAX_SIZE` | Workspace cache max entries | `1024` |
| `WORKSPACE_CACHE_TTL_SECONDS` | Workspace cache TTL | `300` |

### Caching (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `OIDC_JWKS_CACHE_TTL_SECONDS` | JWKS key set cache TTL | `300` |
| `PERMISSION_CACHE_TTL_SECONDS` | Permission resolution cache TTL | `30` |
| `CACHE_BACKEND` | Cache backend: `local` or `redis` | `local` |
| `CACHE_KEY_PREFIX` | Redis cache key prefix | `mlflow_oidc_auth:` |

> [!IMPORTANT]
> **Multi-replica deployments require Redis.** When `replicas > 1` or `hpa.enabled`, the chart
> enforces `CACHE_BACKEND=redis` and requires `CACHE_REDIS_URL` to be provided (via `secretRefs`,
> `secrets.externalSecretName`, `env`, or `config.data`). This ensures sessions and permission
> caches are consistent across pods. Any Redis-compatible server works (Valkey, Dragonfly, KeyDB).
> Installation will **fail** if Redis is not configured for multi-replica setups.

### UI Settings (`config.data`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `EXTEND_MLFLOW_MENU` | Add OIDC auth menu items | `true` |
| `DEFAULT_LANDING_PAGE_IS_PERMISSIONS` | Permissions as landing page | `true` |
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
| `SECRET_KEY` | Session signing key (must be same across replicas) | SECRET |
| `OIDC_CLIENT_ID` | OAuth client identifier | SENSITIVE |
| `OIDC_CLIENT_SECRET` | OAuth client secret | SECRET |
| `OIDC_USERS_DB_URI` | Auth database connection string | SENSITIVE |
| `MLFLOW_BACKEND_STORE_URI` | MLflow tracking database URI | SECRET |

### Optional Secret Keys

| Key | Description | When Needed |
|-----|-------------|-------------|
| `CACHE_REDIS_URL` | Redis connection URL | When `CACHE_BACKEND=redis` |
| `MLFLOW_WEBHOOK_SECRET_ENCRYPTION_KEY` | Fernet key for webhook secret encryption | When using webhooks with secrets |
| `CONFIG_VAULT_TOKEN` | HashiCorp Vault token | When using Vault provider |
| `CONFIG_VAULT_SECRET_ID` | Vault AppRole secret ID | When using Vault AppRole auth |

### Option 1: Secret Refs (Recommended)

Inject individual env vars from one or more Kubernetes Secrets using `valueFrom.secretKeyRef`. This is the most flexible approach and works with any external secret operator (External Secrets Operator, Sealed Secrets, etc.):

```yaml
secretRefs:
  SECRET_KEY:
    name: mlflow-oidc-secrets
    key: secret-key
  OIDC_CLIENT_ID:
    name: mlflow-oidc-secrets
    key: client-id
  OIDC_CLIENT_SECRET:
    name: mlflow-oidc-secrets
    key: client-secret
  OIDC_USERS_DB_URI:
    name: mlflow-db-credentials
    key: auth-db-uri
  MLFLOW_BACKEND_STORE_URI:
    name: mlflow-db-credentials
    key: tracking-db-uri
  CACHE_REDIS_URL:
    name: redis-credentials
    key: url
```

Each entry produces a `valueFrom.secretKeyRef` in the container spec. You can reference keys from different secrets, making it easy to compose credentials from multiple sources.

### Option 2: External Secret (Bulk Injection)

All keys from a single secret are injected as environment variables:

```yaml
secrets:
  externalSecretName: "mlflow-secrets"
  mountAsFiles:
    enabled: false
```

### Option 3: Kubernetes Secrets Provider (File Mount)

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
  name: mlflow-oidc-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: mlflow-oidc-secrets
  data:
    - secretKey: secret-key
      remoteRef:
        key: mlflow/config
        property: secret_key
    - secretKey: client-id
      remoteRef:
        key: mlflow/oidc
        property: client_id
    - secretKey: client-secret
      remoteRef:
        key: mlflow/oidc
        property: client_secret
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: mlflow-db-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: mlflow-db-credentials
  data:
    - secretKey: auth-db-uri
      remoteRef:
        key: mlflow/database
        property: auth_uri
    - secretKey: tracking-db-uri
      remoteRef:
        key: mlflow/database
        property: tracking_uri
```

Then reference them in values:

```yaml
secretRefs:
  SECRET_KEY:
    name: mlflow-oidc-secrets
    key: secret-key
  OIDC_CLIENT_ID:
    name: mlflow-oidc-secrets
    key: client-id
  OIDC_CLIENT_SECRET:
    name: mlflow-oidc-secrets
    key: client-secret
  OIDC_USERS_DB_URI:
    name: mlflow-db-credentials
    key: auth-db-uri
  MLFLOW_BACKEND_STORE_URI:
    name: mlflow-db-credentials
    key: tracking-db-uri
```

---

## Cloud Config Providers

The mlflow-oidc-auth plugin supports pluggable configuration providers. Enable them via environment variables in `config.data`:

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
    CONFIG_AZURE_KEYVAULT_NAME: "my-keyvault"

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

# Inject Vault token from a secret
secretRefs:
  CONFIG_VAULT_TOKEN:
    name: vault-credentials
    key: token
```

---

## Artifact Storage Examples

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
replicas: 2

image:
  registry: ghcr.io/mlflow-oidc
  name: mlflow-tracking-server
  # tag defaults to appVersion (7.0.0)

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
    OIDC_AUDIENCE: "my-mlflow-client-id"

    # Authorization
    OIDC_GROUP_NAME: "mlflow-users,data-scientists"
    OIDC_ADMIN_GROUP_NAME: "mlflow-admins"
    DEFAULT_MLFLOW_PERMISSION: "NO_PERMISSIONS"

    # Security
    TRUSTED_PROXIES: "10.0.0.0/8,172.16.0.0/12"

    # Multi-replica caching
    CACHE_BACKEND: "redis"
    PERMISSION_CACHE_TTL_SECONDS: "30"

# Individual secret lookups from external secrets
secretRefs:
  SECRET_KEY:
    name: mlflow-oidc-secrets
    key: secret-key
  OIDC_CLIENT_ID:
    name: mlflow-oidc-secrets
    key: client-id
  OIDC_CLIENT_SECRET:
    name: mlflow-oidc-secrets
    key: client-secret
  OIDC_USERS_DB_URI:
    name: mlflow-db-credentials
    key: auth-db-uri
  MLFLOW_BACKEND_STORE_URI:
    name: mlflow-db-credentials
    key: tracking-db-uri
  CACHE_REDIS_URL:
    name: redis-credentials
    key: url

serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789:role/mlflow-s3-access"

healthCheck:
  enabled: true
  liveness:
    path: health/live
  readiness:
    path: health/ready
  startup:
    path: health/ready
```

## Signature validation

```bash
cosign verify ghcr.io/mlflow-oidc/helm/mlflow-tracking-server:<version> --certificate-identity="https://github.com/mlflow-oidc/helm/.github/workflows/release.yaml@refs/heads/main" --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

---

## License

Apache 2.0
