# Midas Finance Bot - Monitoring Setup

Complete monitoring stack with Prometheus, Grafana, Loki, and Promtail for observability.

## Components

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation
- **Promtail**: Log shipping to Loki

## Quick Start

### 1. Start Monitoring Stack

```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`
  
- **Prometheus**: http://localhost:9090

### 3. Start Bot with Metrics

The bot automatically exposes metrics on port 8000:

```bash
# Bot metrics endpoint
curl http://localhost:8000/metrics

# Health check
curl http://localhost:8000/health
```

## Key Metrics

### Bot Metrics
- `bot_requests_total`: Total bot requests by command
- `bot_errors_total`: Total bot errors by type

### AI Metrics
- `ai_categorization_requests_total`: AI categorization requests
- `ai_categorization_duration_seconds`: AI processing time
- `ai_confidence_score`: AI confidence distribution
- `ai_auto_confirmed_total`: Auto-confirmed categorizations
- `ai_corrections_total`: User corrections

### Transaction Metrics
- `transactions_synced_total`: Transactions synced by wallet type
- `transactions_categorized_total`: Transactions categorized
- `crypto_card_topups_detected_total`: Crypto card top-ups detected

### Queue Metrics
- `queue_tasks_enqueued_total`: Tasks enqueued
- `queue_tasks_completed_total`: Tasks completed
- `queue_size`: Current queue size

### Database Metrics
- `db_queries_total`: Database queries
- `db_query_duration_seconds`: Query duration
- `db_connection_pool_size`: Connection pool size

### Redis Metrics
- `redis_operations_total`: Redis operations
- `redis_operation_duration_seconds`: Operation duration

## Alerts

Prometheus alerts are configured in `alerts.yml`:

- **HighErrorRate**: Error rate > 0.1 errors/sec
- **LowAIConfidence**: >50% categorizations require manual confirmation
- **QueueBacklog**: Queue size > 100 tasks
- **SlowAIProcessing**: p95 processing time > 10s
- **SlowDatabaseQueries**: p95 query time > 2s
- **RedisConnectionErrors**: Redis error rate > 0.05 errors/sec
- **NoActiveUsers**: No active users for 30 minutes

## Grafana Dashboards

### Midas Bot Overview
Pre-configured dashboard with:
- Bot request rate
- Error rate
- AI categorization duration (p95)
- AI confidence distribution
- Auto-confirmation rate
- Active users
- Queue size
- Transaction sync rate
- Database query duration
- Redis operations rate

## Logs

Logs are collected by Promtail and sent to Loki. View logs in Grafana:

1. Go to Explore
2. Select "Loki" datasource
3. Query examples:
   ```
   {job="midas-bot"}
   {job="midas-bot", level="ERROR"}
   {job="midas-worker", task_type="categorization"}
   ```

## Production Recommendations

1. **Retention**: Configure retention policies in Prometheus and Loki
2. **Alerting**: Set up Alertmanager for notifications
3. **Security**: Change default Grafana password
4. **Backup**: Backup Prometheus and Grafana data volumes
5. **Scaling**: Use remote storage for Prometheus (e.g., Thanos, Cortex)

## Troubleshooting

### Metrics not showing up
- Check bot is running and metrics endpoint is accessible
- Verify Prometheus targets: http://localhost:9090/targets
- Check Prometheus logs: `docker logs midas-prometheus`

### Logs not appearing
- Check Promtail is running: `docker logs midas-promtail`
- Verify log file paths in `promtail-config.yml`
- Check Loki logs: `docker logs midas-loki`

### Grafana dashboard empty
- Verify datasources are configured: Settings → Data Sources
- Check Prometheus is scraping: http://localhost:9090/targets
- Refresh dashboard or adjust time range

## Stopping Monitoring Stack

```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml down
```

To remove volumes:
```bash
docker-compose -f docker-compose.monitoring.yml down -v
```
