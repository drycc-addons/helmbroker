{{/* Generate helmbroker deployment envs */}}
{{- define "helmbroker.envs" }}
env:
- name: "TZ"
  value: {{ .Values.time_zone | default "UTC" | quote }}
- name: HELMBROKER_USERNAME
  value: {{ if .Values.username | default "" | ne "" }}{{ .Values.username }}{{ else }}{{ randAlphaNum 32 }}{{ end }}
- name: HELMBROKER_PASSWORD
  value: {{ if .Values.password | default "" | ne "" }}{{ .Values.password }}{{ else }}{{ randAlphaNum 32 }}{{ end }}
{{- if (.Values.rabbitmqUrl) }}
- name: HELMBROKER_RABBITMQ_URL
  value: {{ .Values.rabbitmqUrl }}
{{- else if eq .Values.global.rabbitmqLocation "on-cluster" }}
- name: "HELMBROKER_RABBITMQ_USERNAME"
  valueFrom:
    secretKeyRef:
      name: rabbitmq-creds
      key: username
- name: "HELMBROKER_RABBITMQ_PASSWORD"
  valueFrom:
    secretKeyRef:
      name: rabbitmq-creds
      key: password
- name: "HELMBROKER_RABBITMQ_URL"
  value: "amqp://$(HELMBROKER_RABBITMQ_USERNAME):$(HELMBROKER_RABBITMQ_PASSWORD)@drycc-rabbitmq.{{$.Release.Namespace}}.svc.{{$.Values.global.clusterDomain}}:5672/helmbroker"
{{- end }}
{{- if (.Values.redisUrl) }}
- name: HELMBROKER_REDIS_URL
  value: {{ .Values.redisUrl }}
{{- else if eq .Values.global.redisLocation "on-cluster" }}
- name: "HELMBROKER_REDIS_ADDRS"
  valueFrom:
    secretKeyRef:
      name: redis-creds
      key: addrs
- name: "HELMBROKER_REDIS_PASSWORD"
  valueFrom:
    secretKeyRef:
      name: redis-creds
      key: password
- name: "HELMBROKER_REDIS_URL"
  value: "redis://:$(HELMBROKER_REDIS_PASSWORD)@$(HELMBROKER_REDIS_ADDRS)/0"
{{- end }}
{{- range $key, $value := .Values.environment }}
- name: {{ $key }}
  value: {{ $value | quote }}
{{- end }}
{{- end }}

{{/* Generate helmbroker deployment limits */}}
{{- define "helmbroker.limits" -}}
{{- if or (.Values.limitsCpu) (.Values.limitsMemory) }}
resources:
  limits:
{{- if (.Values.limitsCpu) }}
    cpu: {{.Values.limitsCpu}}
{{- end }}
{{- if (.Values.limitsMemory) }}
    memory: {{.Values.limitsMemory}}
{{- end }}
{{- end }}
{{- end }}

{{/* Generate helmbroker deployment volumeMounts */}}
{{- define "helmbroker.volumeMounts" }}
volumeMounts:
- name: drycc-helmbroker-cm
  mountPath: "/etc/helmbroker/config"
  readOnly: true
{{- if .Values.persistence.enabled }}
- name: helmbroker-data
  mountPath: /etc/helmbroker
{{- end }}
{{- end }}

{{/* Generate helmbroker deployment volumes */}}
{{- define "helmbroker.volumes" }}
volumes:
- name: drycc-helmbroker-cm
  configMap:
    name: drycc-helmbroker-cm
{{- if .Values.persistence.enabled }}
- name: helmbroker-data
  persistentVolumeClaim:
    claimName: drycc-helmbroker
{{- else }}
- name: helmbroker-data
  emptyDir: {}
{{- end }}
{{- end }}
