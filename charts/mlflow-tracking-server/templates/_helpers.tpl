{{/*
  Validation: require Redis when running multiple replicas.

  When replicas > 1 or HPA is enabled, mlflow-oidc-auth requires a shared
  cache backend (Redis) so that sessions and permission caches are consistent
  across pods.

  Rules:
  1. CACHE_BACKEND must be "redis" in config.data.
  2. CACHE_REDIS_URL must be supplied through at least one of:
     - config.data.CACHE_REDIS_URL
     - secretRefs.CACHE_REDIS_URL
     - env (a list entry with name CACHE_REDIS_URL)
     - secrets.externalSecretName (we trust the external secret contains it)
*/}}
{{- define "application.validateRedis" -}}
{{- $multiReplica := false -}}
{{- if gt (int (default 1 .Values.replicas)) 1 -}}
  {{- $multiReplica = true -}}
{{- end -}}
{{- $hpa := default (dict) .Values.hpa -}}
{{- if $hpa.enabled -}}
  {{- $multiReplica = true -}}
{{- end -}}

{{- if $multiReplica -}}
  {{- $configData := default (dict) .Values.config.data -}}

  {{/* 1. CACHE_BACKEND must be "redis" */}}
  {{- if ne (default "" (index $configData "CACHE_BACKEND")) "redis" -}}
    {{- fail "Multi-replica deployment detected (replicas > 1 or HPA enabled). Set config.data.CACHE_BACKEND to \"redis\" so that sessions and caches are shared across pods." -}}
  {{- end -}}

  {{/* 2. CACHE_REDIS_URL must be reachable through some path */}}
  {{- $secrets := default (dict) .Values.secrets -}}
  {{- $hasRedisURL := false -}}

  {{/* Check config.data */}}
  {{- if index $configData "CACHE_REDIS_URL" -}}
    {{- $hasRedisURL = true -}}
  {{- end -}}

  {{/* Check secretRefs */}}
  {{- $secretRefs := default (dict) .Values.secretRefs -}}
  {{- if index $secretRefs "CACHE_REDIS_URL" -}}
    {{- $hasRedisURL = true -}}
  {{- end -}}

  {{/* Check env list */}}
  {{- range (default (list) .Values.env) -}}
    {{- if eq (default "" .name) "CACHE_REDIS_URL" -}}
      {{- $hasRedisURL = true -}}
    {{- end -}}
  {{- end -}}

  {{/* If externalSecretName is set, trust it contains the URL */}}
  {{- if $secrets.externalSecretName -}}
    {{- $hasRedisURL = true -}}
  {{- end -}}

  {{- if not $hasRedisURL -}}
    {{- fail "Multi-replica deployment with CACHE_BACKEND=redis requires CACHE_REDIS_URL. Provide it via config.data.CACHE_REDIS_URL, secretRefs.CACHE_REDIS_URL, an env entry, or include it in your secrets.externalSecretName secret." -}}
  {{- end -}}
{{- end -}}
{{- end -}}

{{/*
  The image reference, shared by the app container and the db-upgrade init container.
*/}}
{{- define "application.image" -}}
{{ default "ghcr.io/mlflow-oidc" .Values.image.registry }}/{{ .Values.image.name }}:{{ .Values.image.tag | default (include "common.chart.appVersion" .) }}
{{- end -}}

{{/*
  envFrom and env for the containers this chart renders itself (the app container when
  secrets.externalSecretName is set, and the db-upgrade init container), so both see the same
  configuration as the tracking server.
*/}}
{{- define "application.envFrom" -}}
{{- $secrets := default (dict) .Values.secrets -}}
{{- $mountAsFiles := default (dict) $secrets.mountAsFiles -}}
envFrom:
  - configMapRef:
      name: {{ template "common.fullname" . }}
  {{- if and $secrets.externalSecretName (not $mountAsFiles.enabled) }}
  - secretRef:
      name: {{ $secrets.externalSecretName }}
  {{- end }}
  {{ include "common.envvar.shared.configs" . | indent 2 }}
  {{ include "common.envvar.shared.secrets" . | indent 2 }}
{{- end -}}

{{- define "application.env" -}}
{{- $secrets := default (dict) .Values.secrets -}}
{{- $mountAsFiles := default (dict) $secrets.mountAsFiles -}}
{{- $filesMode := and $secrets.externalSecretName $mountAsFiles.enabled -}}
{{- if or $filesMode .Values.env .Values.secretRefs }}
env:
  {{- if $filesMode }}
  - name: CONFIG_K8S_SECRETS_ENABLED
    value: "true"
  - name: CONFIG_K8S_SECRETS_PATH
    value: {{ $mountAsFiles.path | default "/var/run/secrets/mlflow-oidc-auth" | quote }}
  {{- end }}
  {{- with .Values.env }}
  {{- toYaml . | nindent 2 }}
  {{- end }}
  {{- range $envName, $ref := .Values.secretRefs }}
  - name: {{ $envName }}
    valueFrom:
      secretKeyRef:
        name: {{ $ref.name }}
        key: {{ $ref.key }}
  {{- end }}
{{- end }}
{{- end -}}

{{/*
  volumeMounts for the containers this chart renders itself: the secret files (mountAsFiles)
  and .Values.volumeMounts (e.g. a writable /tmp when the root filesystem is read-only).
*/}}
{{- define "application.volumeMounts" -}}
{{- $secrets := default (dict) .Values.secrets -}}
{{- $mountAsFiles := default (dict) $secrets.mountAsFiles -}}
{{- $filesMode := and $secrets.externalSecretName $mountAsFiles.enabled -}}
{{- if or $filesMode .Values.volumeMounts }}
volumeMounts:
  {{- if $filesMode }}
  - name: mlflow-secrets
    mountPath: {{ $mountAsFiles.path | default "/var/run/secrets/mlflow-oidc-auth" }}
    readOnly: true
  {{- end }}
  {{- with .Values.volumeMounts }}
  {{- toYaml . | nindent 2 }}
  {{- end }}
{{- end }}
{{- end -}}
