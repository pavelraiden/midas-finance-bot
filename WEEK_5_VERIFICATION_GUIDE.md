# Week 5 Critical Infrastructure - Verification Guide

**Purpose**: Verify that all Week 5 infrastructure components work correctly before proceeding to AI features.

**Time**: 15-30 minutes

## Prerequisites

- Docker and docker-compose installed
- Bot environment variables configured (.env file)
- Port 3000, 8000, 9090 available

## Step-by-Step Verification

### 1. Start Monitoring Stack (5 minutes)

```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

**Expected output**:
```
Creating midas-prometheus ... done
Creating midas-loki       ... done
Creating midas-grafana    ... done
Creating midas-promtail   ... done
```

**Verify containers are running**:
```bash
docker ps | grep midas
```

Should see 4 containers: prometheus, grafana, loki, promtail.

### 2. Access Grafana (2 minutes)

Open browser: http://localhost:3000

**Login**:
- Username: `admin`
- Password: `admin`

**Expected**: Grafana login page appears.

**First login**: You'll be prompted to change password. You can skip or set new password.

### 3. Verify Prometheus Datasource (2 minutes)

In Grafana:
1. Go to **Configuration** → **Data Sources**
2. Click **Prometheus**
3. Scroll down and click **Save & Test**

**Expected**: ✅ "Data source is working"

### 4. Start Bot with Metrics (3 minutes)

In a new terminal:

```bash
cd /path/to/midas-finance-bot
python3 -m src.main
```

**Expected output**:
```
✅ Prometheus metrics initialized
✅ Prometheus metrics server started on http://0.0.0.0:8000/metrics
✅ Health check endpoint: http://0.0.0.0:8000/health
✅ Bot started successfully
```

### 5. Verify Metrics Endpoint (2 minutes)

Open browser or use curl:

```bash
curl http://localhost:8000/metrics
```

**Expected**: Prometheus metrics in text format:
```
# HELP bot_requests_total Total number of bot requests
# TYPE bot_requests_total counter
bot_requests_total{command="start",user_id="123"} 0.0
...
# HELP app_info Application information
# TYPE app_info gauge
app_info{environment="production",name="Midas Finance Bot",version="1.0.0"} 1.0
```

**Health check**:
```bash
curl http://localhost:8000/health
```

**Expected**:
```json
{"status": "healthy", "service": "midas-finance-bot"}
```

### 6. Verify Prometheus Scraping (3 minutes)

Open browser: http://localhost:9090

1. Go to **Status** → **Targets**
2. Find `midas-bot` job

**Expected**: 
- State: **UP** (green)
- Last Scrape: recent timestamp
- Scrape Duration: <100ms

### 7. View Grafana Dashboard (5 minutes)

In Grafana:
1. Go to **Dashboards** → **Browse**
2. Click **Midas Finance Bot - Overview**

**Expected panels**:
- Bot Requests Rate
- Bot Error Rate
- AI Categorization Duration (p95)
- AI Confidence Distribution
- Auto-Confirmation Rate
- Active Users
- Queue Size
- Transactions Synced Rate
- Database Query Duration (p95)
- Redis Operations Rate

**Note**: Some panels may be empty if no activity yet. That's OK!

### 8. Generate Some Activity (5 minutes)

Interact with the bot:
1. Send `/start` command
2. Add a wallet
3. Sync transactions
4. Categorize a transaction

**Then refresh Grafana dashboard** (wait 30 seconds for metrics to update).

**Expected**: 
- Bot Requests Rate should show activity
- Active Users should be > 0
- Some panels should have data

### 9. Verify Structured Logs (3 minutes)

Check logs directory:
```bash
ls -la logs/
```

**Expected**:
```
structured.log
bot.log
worker.log
```

**View structured logs**:
```bash
tail -f logs/structured.log
```

**Expected**: JSON-formatted logs:
```json
{"timestamp": "2025-11-30T12:00:00Z", "level": "INFO", "logger": "midas.bot", "message": "Bot request: /start", "user_id": "123", "command": "/start"}
```

### 10. Verify Loki Logs (Optional, 5 minutes)

In Grafana:
1. Go to **Explore**
2. Select **Loki** datasource
3. Query: `{job="midas-bot"}`

**Expected**: Logs appear in Loki (if Promtail is configured correctly).

**Note**: Promtail needs correct log file paths in `promtail-config.yml`.

### 11. Verify Redis Confirmation Storage (3 minutes)

**Connect to Redis**:
```bash
docker exec -it redis redis-cli
```

**Create a test confirmation** (via bot or manually):
```bash
# In Redis CLI
KEYS confirmation:*
```

**Expected**: Should see confirmation keys if any confirmations were created.

**Check TTL**:
```bash
TTL confirmation:conf_123_1234567890
```

**Expected**: Should show remaining seconds (e.g., 86400 for 24 hours).

### 12. Verify Database Indexes (2 minutes)

**Connect to database**:
```bash
psql -U postgres -d midas_finance
```

**Check indexes**:
```sql
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'public' 
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
```

**Expected**: Should see 20+ indexes starting with `idx_`.

**Example**:
```
idx_transactions_user_id_timestamp | transactions
idx_transactions_uncategorized     | transactions
idx_merchant_mappings_user_merchant| merchant_mappings
...
```

## Verification Checklist

Use this checklist to track your progress:

- [ ] Monitoring stack started (4 containers running)
- [ ] Grafana accessible (http://localhost:3000)
- [ ] Prometheus datasource working
- [ ] Bot started with metrics endpoint
- [ ] Metrics endpoint responding (http://localhost:8000/metrics)
- [ ] Health check responding (http://localhost:8000/health)
- [ ] Prometheus scraping bot metrics (target UP)
- [ ] Grafana dashboard visible
- [ ] Dashboard shows activity after bot interaction
- [ ] Structured logs created (logs/structured.log)
- [ ] Logs are JSON-formatted
- [ ] Redis confirmation storage working (optional)
- [ ] Database indexes created (optional)

## Troubleshooting

### Monitoring stack won't start

**Issue**: Port conflict or Docker not running.

**Solution**:
```bash
# Check if ports are in use
lsof -i :3000
lsof -i :9090

# Stop conflicting services or change ports in docker-compose.monitoring.yml
```

### Grafana shows "Data source is working" but no data

**Issue**: Bot not started or metrics endpoint not accessible.

**Solution**:
```bash
# Check bot is running
ps aux | grep python

# Check metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus targets
# Open http://localhost:9090/targets
```

### Metrics endpoint returns 404

**Issue**: Metrics server not started in bot.

**Solution**:
- Verify `src/infrastructure/monitoring/metrics_server.py` is imported in `src/main.py`
- Check bot logs for metrics server startup message

### Structured logs not created

**Issue**: Logs directory doesn't exist or permissions issue.

**Solution**:
```bash
# Create logs directory
mkdir -p logs

# Check permissions
chmod 755 logs
```

### Redis confirmation not working

**Issue**: Redis not running or connection error.

**Solution**:
```bash
# Check Redis is running
docker ps | grep redis

# Check Redis connection
redis-cli ping
# Expected: PONG

# Check bot logs for Redis errors
```

### Database indexes not created

**Issue**: Migration not run.

**Solution**:
```bash
# Run migration manually
psql -U postgres -d midas_finance < migrations/003_add_performance_indexes.sql
```

## Success Criteria

✅ **All checks passed**:
- Monitoring stack running
- Grafana dashboard showing data
- Metrics being collected
- Structured logs working
- Redis confirmation storage functional
- Database indexes created

🎯 **Ready to proceed with Week 5 AI Features!**

## Next Steps

After successful verification:

1. **Stop monitoring stack** (if needed):
   ```bash
   cd monitoring
   docker-compose -f docker-compose.monitoring.yml down
   ```

2. **Report results** to confirm infrastructure is ready.

3. **Proceed to Week 5 AI Features**:
   - Merchant Normalization DB (18 hours)
   - Natural Language Queries (15 hours)

---

**Questions or issues?** Check troubleshooting section or ask for help!
