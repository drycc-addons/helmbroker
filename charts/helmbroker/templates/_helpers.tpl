{{/* Generate helmbroker deployment envs */}}
{{- define "helmbroker.envs" }}
env:
- name: "TZ"
  value: {{ .Values.time_zone | default "UTC" | quote }}
- name: USERNAME:
  {{ if .Values.username | default "" | ne "" }}{{ .Values.username | b64enc }}{{ else }}{{ randAlphaNum 32 | b64enc }}{{ end }}
- name: PASSWORD:
  {{ if .Values.password | default "" | ne "" }}{{ .Values.password | b64enc }}{{ else }}{{ randAlphaNum 32 | b64enc }}{{ end }}
{{- range $key, $value := .Values.environment }}
- name: {{ $key }}
  value: {{ $value | quote }}
{{- end }}
{{- end }}


{{/* Generate helmbroker deployment limits */}}
{{- define "helmbroker.limits" -}}
{{- if or (.Values.limits_cpu) (.Values.limits_memory) }}
resources:
  limits:
{{- if (.Values.limits_cpu) }}
    cpu: {{.Values.limits_cpu}}
{{- end }}
{{- if (.Values.limits_memory) }}
    memory: {{.Values.limits_memory}}
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
