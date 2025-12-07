# Monitoring and Observability

## Overview

Vertex AR implements comprehensive monitoring using Prometheus for metrics collection, Grafana for visualization, and structured logging for detailed insights. The system tracks API performance, system health, background tasks, and business metrics.

## Logging

### Structured Logging

All application logs use structured JSON format with consistent fields:

```json
{
  "timestamp": "2025-12-07T10:30:45.123Z",
  "level": "info",
  "logger": "app.main",
  "event": "http_request_started",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": 123,
  "company_id": 456,
  "method": "POST",
  "path": "/api/ar-content",
  "client_host": "192.168.1.100"
}
```

### Key Log Fields

- **request_id**: Unique identifier for tracing requests across services
- **user_id**: Authenticated user ID (when available)
- **company_id**: Company context (when available)
- **method/path**: HTTP method and endpoint
- **duration_seconds**: Request processing time
- **status_code**: HTTP response status

### Log Levels

- **DEBUG**: Detailed diagnostic information (development only)
- **INFO**: General operational events
- **WARNING**: Potentially harmful situations
- **ERROR**: Error events that might still allow the application to continue
- **CRITICAL**: Critical errors requiring immediate attention

### Log Aggregation

Logs are collected by Docker and can be forwarded to:
- Elasticsearch for search and analysis
- Loki for lightweight log aggregation
- Cloud logging services (AWS CloudWatch, Google Cloud Logging)

## Metrics

### Prometheus Integration

Vertex AR exposes metrics via the `/api/health/metrics` endpoint in Prometheus format.

### Key Metrics

#### API Metrics

- `api_request_duration_seconds`: Request latency histogram
- `api_request_count_total`: Total requests counter by method, path, and status
- `http_requests_total`: Standard HTTP request counter

#### System Metrics

- `process_cpu_seconds_total`: CPU time consumed
- `process_resident_memory_bytes`: Memory usage
- `process_open_fds`: Open file descriptors

#### Business Metrics

- `ar_content_created_total`: Number of AR content items created
- `video_uploaded_total`: Number of videos uploaded
- `marker_generated_total`: Number of markers generated
- `user_login_total`: Number of user logins

#### Background Task Metrics

- `celery_task_duration_seconds`: Task processing time
- `celery_task_failure_total`: Failed task counter
- `celery_queue_length`: Current queue backlog

### Custom Metrics Example

```python
# app/tasks/marker_tasks.py
from prometheus_client import Counter, Histogram

MARKER_GENERATED = Counter('marker_generated_total', 'Total markers generated', ['status'])
MARKER_DURATION = Histogram('marker_generation_duration_seconds', 'Marker generation time')

@celery_app.task
def generate_mind_marker_task(...):
    start = time.time()
    try:
        # Generate marker
        result = marker_service.generate_marker(...)
        MARKER_GENERATED.labels(status='success').inc()
        return result
    except Exception as e:
        MARKER_GENERATED.labels(status='failure').inc()
        raise
    finally:
        MARKER_DURATION.observe(time.time() - start)
```

## Alerting

### Alert Rules

Alerts are defined in `prometheus/alert.rules.yml`:

#### Critical Alerts

- **High 5xx Error Rate**: >5% of requests returning 5xx errors for 1 minute
- **High API Latency**: 95th percentile >5 seconds for 2 minutes
- **High Celery Task Failures**: >10 task failures in 5 minutes
- **System Resource Exhaustion**: CPU/Memory >90% for 5 minutes

#### Warning Alerts

- **Celery Queue Backlog**: >100 tasks queued for 5 minutes
- **PostgreSQL High Connections**: >80 connections for 10 minutes
- **Low Disk Space**: <10% free space

### Alert Delivery

Alerts are delivered via:
- **Email**: To admin@vertexar.com
- **Telegram**: To admin chat group
- **Webhook**: To incident management systems

### Alert Suppression

- **Cooldown periods**: Prevent alert spam (5-60 minutes based on severity)
- **Maintenance windows**: Suppress non-critical alerts during maintenance
- **Dependency awareness**: Suppress dependent service alerts when root cause is identified

## Dashboards

### Grafana Dashboards

#### System Overview

Displays:
- CPU, memory, disk usage
- Network I/O
- Container health status
- Uptime statistics

#### API Performance

Displays:
- Request rate by endpoint
- Response time percentiles
- Error rates and distributions
- Throughput metrics

#### Business Metrics

Displays:
- AR content creation trends
- Video upload statistics
- User engagement metrics
- Storage utilization

#### Background Tasks

Displays:
- Celery worker status
- Task queue depths
- Processing times
- Failure rates

### Dashboard Access

- **Grafana**: http://localhost:3001 (credentials in `.env`)
- **Default dashboards**: Pre-configured in `grafana/dashboards/`

## Health Checks

### API Health Endpoint

`GET /api/health/status`

Returns comprehensive health information:

```json
{
  "database": "healthy",
  "redis": "healthy",
  "celery": {
    "status": "healthy",
    "queue_length": 5,
    "workers_alive": 2
  },
  "system": {
    "cpu_percent": 23.4,
    "memory_percent": 45.6,
    "disk_percent": 34.2
  },
  "marker_failures_last_hour": 0,
  "overall": "healthy"
}
```

### Container Health Checks

Defined in `docker-compose.yml`:

```yaml
services:
  app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

## Tracing

### Request Tracing

Each HTTP request is assigned a unique `request_id` that is:
- Generated at request start
- Included in all log entries for that request
- Returned in response headers for client-side tracing
- Propagated to background tasks

### Distributed Tracing

Integration with OpenTelemetry (future enhancement):
- Trace request flow across services
- Measure end-to-end latency
- Identify bottlenecks in complex operations

## Monitoring Setup

### Local Development

```bash
# Start monitoring stack
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Access Grafana
open http://localhost:3001

# Access Prometheus
open http://localhost:9090
```

### Production Deployment

Monitoring services are included in the main `docker-compose.yml`:
- Prometheus scrapes metrics every 15 seconds
- Grafana connects to Prometheus datasource
- Alertmanager handles alert routing and deduplication

### Configuration Files

- **Prometheus**: `prometheus/prometheus.yml`
- **Alert Rules**: `prometheus/alert.rules.yml`
- **Grafana**: `grafana/` directory with dashboards and configs
- **Alertmanager**: `alertmanager/config.yml`

## Best Practices

### Metric Design

1. **Use base units**: Seconds, bytes, counts
2. **Include labels**: For dimensions like status, method, endpoint
3. **Avoid high cardinality**: Limit unique label combinations
4. **Use histograms**: For latency and duration measurements
5. **Export consistently**: Same metrics across all instances

### Alert Design

1. **Actionable alerts**: Each alert should require human intervention
2. **Clear symptoms**: Alert on user-observable problems
3. **Appropriate thresholds**: Based on historical data and business impact
4. **Meaningful names**: Descriptive alert names and descriptions
5. **Severity levels**: Critical, warning, info with appropriate routing

### Dashboard Design

1. **Purpose-driven**: Each dashboard should serve a specific audience
2. **Consistent time ranges**: Default to meaningful time windows
3. **Clear visual hierarchy**: Important metrics prominent
4. **Contextual information**: Include explanations and links
5. **Regular review**: Update dashboards based on usage and feedback

## Troubleshooting

### Common Issues

#### Missing Metrics

```bash
# Check if metrics endpoint is accessible
curl http://localhost:8000/api/health/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify metric names
curl http://localhost:8000/api/health/metrics | grep api_request
```

#### High Cardinality

```bash
# Check metric cardinality
curl http://localhost:9090/api/v1/status/tsdb | jq '.data.seriesCountByMetric'

# Identify high-cardinality metrics
curl http://localhost:9090/api/v1/status/tsdb | jq '.data.labelValueCountByLabelName'
```

#### Alert Flooding

```bash
# Check alertmanager for silenced alerts
curl http://localhost:9093/api/v2/silences

# Review alert rules for tight thresholds
cat prometheus/alert.rules.yml
```