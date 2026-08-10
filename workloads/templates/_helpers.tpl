{{- define "workloads.telemetry.env" -}}
- name: OTEL_INSTRUMENTATION_COMMON_DEFAULT_ENABLED
  value: "false"
- name: OTEL_INSTRUMENTATION_GRPC_ENABLED
  value: "true"
- name: OTEL_INSTRUMENTATION_JDBC_ENABLED
  value: "true"
- name: OTEL_INSTRUMENTATION_HIKARICP_ENABLED
  value: "true"
- name: PYROSCOPE_APPLICATION_NAME
  value: {{ . }}
- name: PYROSCOPE_PROFILING_INTERVAL
  value: 1ms
- name: PYROSCOPE_PROFILER_ALLOC
  value: 128k
- name: PYROSCOPE_LABELS
  value: pod=$(POD_NAME),service_name={{ . }}
{{- end -}}
