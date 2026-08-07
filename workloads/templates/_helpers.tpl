{{- define "workloads.telemetry.env" -}}
- name: JAVA_TOOL_OPTIONS
  value: -javaagent:/opt/byteman/lib/byteman.jar=listener:true,port:9288,address:0.0.0.0 -javaagent:/agent/pyroscope.jar -javaagent:/agent/opentelemetry-javaagent.jar
- name: OTEL_SERVICE_NAME
  value: {{ . }}
- name: PYROSCOPE_APPLICATION_NAME
  value: {{ . }}
- name: PYROSCOPE_PROFILING_INTERVAL
  value: 1ms
- name: PYROSCOPE_PROFILER_ALLOC
  value: 128k
- name: PYROSCOPE_LABELS
  value: pod=$(POD_NAME),service_name={{ . }}
{{- end -}}
