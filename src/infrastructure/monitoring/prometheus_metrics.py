"""
Prometheus Metrics Exporter
Exposes key metrics for monitoring and alerting
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)

# Bot metrics
bot_requests_total = Counter(
    'bot_requests_total',
    'Total number of bot requests',
    ['command', 'user_id']
)

bot_errors_total = Counter(
    'bot_errors_total',
    'Total number of bot errors',
    ['error_type', 'command']
)

# AI metrics
ai_categorization_requests_total = Counter(
    'ai_categorization_requests_total',
    'Total number of AI categorization requests',
    ['user_id']
)

ai_categorization_duration_seconds = Histogram(
    'ai_categorization_duration_seconds',
    'Time spent on AI categorization',
    ['user_id'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

ai_confidence_score = Histogram(
    'ai_confidence_score',
    'AI categorization confidence scores',
    ['user_id', 'category'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
)

ai_auto_confirmed_total = Counter(
    'ai_auto_confirmed_total',
    'Total number of auto-confirmed categorizations',
    ['user_id', 'category']
)

ai_manual_confirmation_required_total = Counter(
    'ai_manual_confirmation_required_total',
    'Total number of categorizations requiring manual confirmation',
    ['user_id', 'category']
)

ai_corrections_total = Counter(
    'ai_corrections_total',
    'Total number of AI corrections by users',
    ['user_id', 'ai_category', 'correct_category']
)

# Transaction metrics
transactions_synced_total = Counter(
    'transactions_synced_total',
    'Total number of transactions synced',
    ['user_id', 'wallet_type']
)

transactions_categorized_total = Counter(
    'transactions_categorized_total',
    'Total number of transactions categorized',
    ['user_id', 'category']
)

crypto_card_topups_detected_total = Counter(
    'crypto_card_topups_detected_total',
    'Total number of crypto card top-ups detected',
    ['user_id']
)

# Queue metrics
queue_tasks_enqueued_total = Counter(
    'queue_tasks_enqueued_total',
    'Total number of tasks enqueued',
    ['task_type', 'priority']
)

queue_tasks_completed_total = Counter(
    'queue_tasks_completed_total',
    'Total number of tasks completed',
    ['task_type', 'status']
)

queue_tasks_duration_seconds = Histogram(
    'queue_tasks_duration_seconds',
    'Time spent processing queue tasks',
    ['task_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

queue_size = Gauge(
    'queue_size',
    'Current queue size',
    ['priority']
)

# Redis metrics
redis_operations_total = Counter(
    'redis_operations_total',
    'Total number of Redis operations',
    ['operation', 'status']
)

redis_operation_duration_seconds = Histogram(
    'redis_operation_duration_seconds',
    'Time spent on Redis operations',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# Database metrics
db_queries_total = Counter(
    'db_queries_total',
    'Total number of database queries',
    ['table', 'operation', 'status']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Time spent on database queries',
    ['table', 'operation'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Current database connection pool size'
)

db_connection_pool_available = Gauge(
    'db_connection_pool_available',
    'Available connections in database pool'
)

# System metrics
active_users = Gauge(
    'active_users',
    'Number of active users'
)

active_wallets = Gauge(
    'active_wallets',
    'Number of active wallets'
)

# Application info
app_info = Info(
    'app_info',
    'Application information'
)

# Set application info
app_info.info({
    'version': '1.0.0',
    'name': 'Midas Finance Bot',
    'environment': 'production'
})

logger.info("✅ Prometheus metrics initialized")
