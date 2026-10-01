# Copilot Instructions for AI Agents

## Project Overview
This repository contains Helm charts for deploying MLflow Tracking Server and an OIDC provider mock. The charts are designed for Kubernetes environments and support OIDC-based authentication and flexible backend/artifact storage.

## Key Components
- **charts/mlflow-tracking-server/**: Helm chart for MLflow Tracking Server with OIDC integration.
- **charts/oidc-provider-mock/**: Helm chart for a mock OIDC provider for development/testing.

## Configuration Patterns
- All major configuration is handled via `values.yaml` in each chart directory.
- OIDC, backend store, and artifact store settings are under their respective keys in `values.yaml`.
- Sensitive values (e.g., secrets, DB URIs) are templated and can be overridden at install time.
- Example:
  ```yaml
  oidc:
    enabled: true
    client_id: "..."
    users_db_uri: "sqlite:///mlflow_users.db"
  backend_store:
    db_uri: "sqlite:///:memory:"
  ```

## Developer Workflows
- **Install/Upgrade Chart:**
  ```sh
  helm install mlflow-tracking-server ./charts/mlflow-tracking-server -f charts/mlflow-tracking-server/values.yaml
  helm upgrade mlflow-tracking-server ./charts/mlflow-tracking-server -f charts/mlflow-tracking-server/values.yaml
  ```
- **Lint Charts:**
  ```sh
  helm lint ./charts/mlflow-tracking-server
  ```
- **Template Rendering:**
  ```sh
  helm template ./charts/mlflow-tracking-server -f charts/mlflow-tracking-server/values.yaml
  ```

## Conventions & Patterns
- Use YAML anchors/comments in `values.yaml` to document and provide alternative config examples.
- All Kubernetes manifests are under `templates/` in each chart.
- Avoid hardcoding secrets; use Helm templating and environment variables.
- Service accounts and persistent storage are configurable and disabled by default.

## Integration Points
- OIDC provider URL and credentials are configurable for real or mock providers.
- Backend and artifact stores support multiple DB/storage types (see commented examples in `values.yaml`).

## References
- See `charts/mlflow-tracking-server/values.yaml` for all available config options and usage patterns.
- See `charts/mlflow-tracking-server/templates/` for Kubernetes manifest structure.

---
For questions about chart structure or deployment, review the comments in `values.yaml` or the Helm documentation.
