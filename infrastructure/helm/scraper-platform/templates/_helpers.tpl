{{/*
Expand the name of the chart.
*/}}
{{- define "scraper.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this.
*/}}
{{- define "scraper.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "scraper.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every resource.
*/}}
{{- define "scraper.labels" -}}
helm.sh/chart: {{ include "scraper.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/part-of: scraper-platform
{{ include "scraper.selectorLabels" . }}
{{- end }}

{{/*
Selector labels (subset used in matchLabels).
*/}}
{{- define "scraper.selectorLabels" -}}
app.kubernetes.io/name: {{ include "scraper.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Component-scoped labels. Call with (list $ "component-name").
*/}}
{{- define "scraper.componentLabels" -}}
{{- $root := index . 0 -}}
{{- $component := index . 1 -}}
{{ include "scraper.labels" $root }}
app.kubernetes.io/component: {{ $component }}
{{- end }}

{{/*
Component-scoped selector labels. Call with (list $ "component-name").
*/}}
{{- define "scraper.componentSelectorLabels" -}}
{{- $root := index . 0 -}}
{{- $component := index . 1 -}}
{{ include "scraper.selectorLabels" $root }}
app.kubernetes.io/component: {{ $component }}
{{- end }}

{{/*
Image reference helper.  Call with (list $ .Values.<component>.image).
*/}}
{{- define "scraper.image" -}}
{{- $root := index . 0 -}}
{{- $img  := index . 1 -}}
{{- $registry := default "" $root.Values.global.imageRegistry -}}
{{- $tag := default $root.Chart.AppVersion $img.tag -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $img.repository $tag }}
{{- else -}}
{{- printf "%s:%s" $img.repository $tag }}
{{- end -}}
{{- end }}

{{/*
PostgreSQL host — resolves to subchart service or external.
*/}}
{{- define "scraper.postgresql.host" -}}
{{- if .Values.postgresql.enabled -}}
{{- printf "%s-postgresql" (include "scraper.fullname" .) }}
{{- else -}}
{{- .Values.externalPostgresql.host }}
{{- end -}}
{{- end }}

{{/*
PostgreSQL port.
*/}}
{{- define "scraper.postgresql.port" -}}
{{- if .Values.postgresql.enabled -}}
5432
{{- else -}}
{{- .Values.externalPostgresql.port | default 5432 }}
{{- end -}}
{{- end }}

{{/*
PostgreSQL database name.
*/}}
{{- define "scraper.postgresql.database" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.database }}
{{- else -}}
{{- .Values.externalPostgresql.database }}
{{- end -}}
{{- end }}

{{/*
PostgreSQL username.
*/}}
{{- define "scraper.postgresql.username" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.username }}
{{- else -}}
{{- .Values.externalPostgresql.username }}
{{- end -}}
{{- end }}

{{/*
Redis host — resolves to subchart service or external.
*/}}
{{- define "scraper.redis.host" -}}
{{- if .Values.redis.enabled -}}
{{- printf "%s-redis-master" (include "scraper.fullname" .) }}
{{- else -}}
{{- .Values.externalRedis.host }}
{{- end -}}
{{- end }}

{{/*
Redis port.
*/}}
{{- define "scraper.redis.port" -}}
{{- if .Values.redis.enabled -}}
6379
{{- else -}}
{{- .Values.externalRedis.port | default 6379 }}
{{- end -}}
{{- end }}

{{/*
Name of the Secret that holds platform credentials.
*/}}
{{- define "scraper.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret }}
{{- else -}}
{{- include "scraper.fullname" . }}
{{- end -}}
{{- end }}
