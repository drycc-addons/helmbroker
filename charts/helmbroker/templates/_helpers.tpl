{{/* Generate helmbroker deployment envs */}}
{{- define "helmbroker.envs" }}
env:
- name: "TZ"
  value: {{ .Values.time_zone | default "UTC" | quote }}
- name: HELMBROKER_USERNAME
  value: {{ if .Values.username | default "" | ne "" }}{{ .Values.username }}{{ else }}{{ randAlphaNum 32 }}{{ end }}
- name: HELMBROKER_PASSWORD
  value: {{ if .Values.password | default "" | ne "" }}{{ .Values.password }}{{ else }}{{ randAlphaNum 32 }}{{ end }}
{{- if (.Values.valkeyUrl) }}
- name: HELMBROKER_VALKEY_URL
  valueFrom:
    secretKeyRef:
      name: helmbroker-creds
      key: valkey-url
{{- else if .Values.valkey.enabled }}
- name: VALKEY_PASSWORD
  valueFrom:
    secretKeyRef:
      name: valkey-creds
      key: password
- name: HELMBROKER_VALKEY_URL
  value: "redis://:$(VALKEY_PASSWORD)@drycc-valkey:26379/0?master_set=drycc"
{{- end }}
{{- range $key, $value := .Values.environment }}
- name: {{ $key }}
  value: {{ $value | quote }}
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
