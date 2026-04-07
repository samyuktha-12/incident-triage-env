# server/scenarios.py
# All task scenarios with ground truth for deterministic grading.

EASY_SCENARIOS = [
    {
        "id": "easy_1",
        "task_description": "Triage the current incident. Identify root cause, severity, and correct remediation.",
        "alerts": [
            {"service": "payments-service", "metric": "error_rate", "value": "45%", "threshold": "5%", "firing_for": "8m"},
            {"service": "payments-service", "metric": "latency_p99", "value": "12000ms", "threshold": "500ms", "firing_for": "8m"},
        ],
        "log_snippets": [
            "[payments-service] ERROR: Connection refused to postgres-primary:5432",
            "[payments-service] ERROR: Connection refused to postgres-primary:5432",
            "[payments-service] WARN: Retrying DB connection (attempt 5/5)",
            "[postgres-primary] FATAL: max_connections=100 reached",
        ],
        "dependency_graph": {
            "api-gateway": ["payments-service", "auth-service"],
            "payments-service": ["postgres-primary", "redis-cache"],
            "auth-service": ["postgres-primary"],
        },
        "recent_deployments": [],
        "ground_truth": {
            "root_cause": "postgres-primary",
            "severity": "P1",
            "remediation": "scale_out",
        },
    },
    {
        "id": "easy_2",
        "task_description": "A service is down after a recent deployment. Identify and remediate.",
        "alerts": [
            {"service": "recommendation-service", "metric": "http_5xx_rate", "value": "98%", "threshold": "1%", "firing_for": "3m"},
            {"service": "recommendation-service", "metric": "pod_restarts", "value": "15", "threshold": "3", "firing_for": "3m"},
        ],
        "log_snippets": [
            "[recommendation-service] FATAL: ImportError: cannot import name 'ModelV2' from 'ml_lib'",
            "[recommendation-service] ERROR: CrashLoopBackOff",
            "[k8s] Pod recommendation-service-7f9d restarting...",
        ],
        "dependency_graph": {
            "api-gateway": ["recommendation-service", "search-service"],
            "recommendation-service": ["feature-store", "redis-cache"],
        },
        "recent_deployments": [
            {"service": "recommendation-service", "version": "v2.4.1", "deployed_at": "14 minutes ago", "deployed_by": "ci-pipeline"},
        ],
        "ground_truth": {
            "root_cause": "recommendation-service",
            "severity": "P2",
            "remediation": "rollback_deployment",
        },
    },
    {
        "id": "easy_3",
        "task_description": "High memory usage alert. Determine the affected component and appropriate action.",
        "alerts": [
            {"service": "search-service", "metric": "memory_usage", "value": "97%", "threshold": "85%", "firing_for": "15m"},
            {"service": "search-service", "metric": "gc_pause_ms", "value": "4500ms", "threshold": "500ms", "firing_for": "12m"},
        ],
        "log_snippets": [
            "[search-service] WARN: Java heap space OutOfMemoryError",
            "[search-service] WARN: GC overhead limit exceeded",
            "[search-service] INFO: Cache size: 12.4GB (limit: 4GB)",
        ],
        "dependency_graph": {
            "api-gateway": ["search-service"],
            "search-service": ["elasticsearch", "redis-cache"],
        },
        "recent_deployments": [],
        "ground_truth": {
            "root_cause": "search-service",
            "severity": "P2",
            "remediation": "restart_service",
        },
    },
]

MEDIUM_SCENARIOS = [
    {
        "id": "medium_1",
        "task_description": "Multiple services are degraded. Cascading failure — find the origin service.",
        "alerts": [
            {"service": "api-gateway", "metric": "latency_p99", "value": "8000ms", "threshold": "200ms", "firing_for": "10m"},
            {"service": "auth-service", "metric": "error_rate", "value": "30%", "threshold": "1%", "firing_for": "10m"},
            {"service": "user-service", "metric": "error_rate", "value": "25%", "threshold": "1%", "firing_for": "9m"},
            {"service": "redis-cache", "metric": "connection_refused", "value": "true", "threshold": "false", "firing_for": "11m"},
        ],
        "log_snippets": [
            "[auth-service] ERROR: redis.exceptions.ConnectionError: Connection refused 127.0.0.1:6379",
            "[user-service] ERROR: Cache miss fallback failed: redis.exceptions.ConnectionError",
            "[api-gateway] WARN: Upstream timeout from auth-service after 5000ms",
            "[redis-cache] FATAL: OOM command not allowed when used memory > maxmemory",
        ],
        "dependency_graph": {
            "api-gateway": ["auth-service", "user-service", "payments-service"],
            "auth-service": ["redis-cache", "postgres-primary"],
            "user-service": ["redis-cache", "postgres-replica"],
            "payments-service": ["postgres-primary"],
        },
        "recent_deployments": [
            {"service": "user-service", "version": "v1.9.0", "deployed_at": "2 hours ago", "deployed_by": "ci-pipeline"},
        ],
        "ground_truth": {
            "root_cause": "redis-cache",
            "severity": "P1",
            "remediation": "restart_service",
        },
    },
    {
        "id": "medium_2",
        "task_description": "Intermittent payment failures. Some requests succeed. Identify root cause.",
        "alerts": [
            {"service": "payments-service", "metric": "error_rate", "value": "15%", "threshold": "1%", "firing_for": "20m"},
            {"service": "payments-gateway", "metric": "timeout_rate", "value": "12%", "threshold": "0.5%", "firing_for": "20m"},
            {"service": "postgres-primary", "metric": "replication_lag_seconds", "value": "45", "threshold": "5", "firing_for": "25m"},
        ],
        "log_snippets": [
            "[payments-service] ERROR: Read your writes consistency violated — stale data from replica",
            "[payments-service] ERROR: Duplicate transaction detected, idempotency key collision",
            "[postgres-replica] WARN: Replication lag: 45 seconds behind primary",
            "[payments-service] INFO: Routing 30% reads to replica (read-replica strategy active)",
        ],
        "dependency_graph": {
            "payments-service": ["postgres-primary", "postgres-replica", "payments-gateway"],
            "payments-gateway": ["stripe-api"],
        },
        "recent_deployments": [
            {"service": "payments-service", "version": "v3.1.0", "deployed_at": "3 hours ago", "note": "Enabled read replica routing"},
        ],
        "ground_truth": {
            "root_cause": "postgres-replica",
            "severity": "P1",
            "remediation": "failover_db",
        },
    },
    {
        "id": "medium_3",
        "task_description": "CDN alerts firing but origin services look healthy. What is wrong?",
        "alerts": [
            {"service": "cdn-edge", "metric": "cache_hit_rate", "value": "2%", "threshold": "85%", "firing_for": "30m"},
            {"service": "cdn-edge", "metric": "origin_fetch_rate", "value": "98%", "threshold": "15%", "firing_for": "30m"},
            {"service": "api-gateway", "metric": "request_rate", "value": "8500rps", "threshold": "2000rps", "firing_for": "28m"},
        ],
        "log_snippets": [
            "[cdn-edge] WARN: Cache-Control: no-store header detected on all /api/v2/* responses",
            "[api-gateway] INFO: Response headers modified — cache-busting middleware active",
            "[cdn-edge] INFO: Purging cache due to upstream Cache-Control directives",
            "[api-gateway] WARN: Downstream load 4x normal — CDN not absorbing traffic",
        ],
        "dependency_graph": {
            "cdn-edge": ["api-gateway"],
            "api-gateway": ["static-assets-service", "auth-service", "content-service"],
        },
        "recent_deployments": [
            {"service": "api-gateway", "version": "v5.0.2", "deployed_at": "35 minutes ago", "note": "Added cache-busting middleware for GDPR compliance"},
        ],
        "ground_truth": {
            "root_cause": "api-gateway",
            "severity": "P2",
            "remediation": "rollback_deployment",
        },
    },
]

HARD_SCENARIOS = [
    {
        "id": "hard_1",
        "task_description": "Full production outage. Multiple teams paging. You have 5 minutes. Find root cause and act.",
        "alerts": [
            {"service": "api-gateway", "metric": "error_rate", "value": "92%", "threshold": "1%", "firing_for": "4m"},
            {"service": "auth-service", "metric": "error_rate", "value": "88%", "threshold": "1%", "firing_for": "4m"},
            {"service": "payments-service", "metric": "error_rate", "value": "91%", "threshold": "1%", "firing_for": "4m"},
            {"service": "notification-service", "metric": "error_rate", "value": "85%", "threshold": "1%", "firing_for": "3m"},
            {"service": "postgres-primary", "metric": "active_queries", "value": "980", "threshold": "100", "firing_for": "5m"},
            {"service": "feature-flag-service", "metric": "latency_p99", "value": "45000ms", "threshold": "100ms", "firing_for": "6m"},
        ],
        "log_snippets": [
            "[feature-flag-service] WARN: Flag evaluation taking 44s — remote config fetch timeout",
            "[feature-flag-service] INFO: Synchronous flag fetch on every request (cache disabled by config)",
            "[auth-service] ERROR: Timeout waiting for feature flag 'new-auth-flow': 44000ms",
            "[payments-service] ERROR: Blocking on feature-flag-service for 'dynamic-pricing-v2'",
            "[postgres-primary] ERROR: Lock wait timeout — 400 queries waiting on feature_flags table",
            "[api-gateway] WARN: All upstreams reporting >30s latency, circuit breaker not configured",
        ],
        "dependency_graph": {
            "api-gateway": ["auth-service", "payments-service", "notification-service"],
            "auth-service": ["feature-flag-service", "postgres-primary"],
            "payments-service": ["feature-flag-service", "postgres-primary"],
            "notification-service": ["feature-flag-service"],
            "feature-flag-service": ["postgres-primary", "remote-config-api"],
        },
        "recent_deployments": [
            {"service": "feature-flag-service", "version": "v1.2.0", "deployed_at": "7 minutes ago", "note": "Disabled local cache to force real-time flag evaluation"},
            {"service": "auth-service", "version": "v8.1.0", "deployed_at": "2 hours ago", "note": "New auth flow behind feature flag"},
        ],
        "ground_truth": {
            "root_cause": "feature-flag-service",
            "severity": "P1",
            "remediation": "rollback_deployment",
        },
    },
    {
        "id": "hard_2",
        "task_description": "Data pipeline is failing silently. End users see stale data. No obvious error alerts.",
        "alerts": [
            {"service": "analytics-dashboard", "metric": "data_freshness_minutes", "value": "187", "threshold": "15", "firing_for": "3h"},
            {"service": "etl-pipeline", "metric": "job_duration_minutes", "value": "180", "threshold": "45", "firing_for": "3h"},
        ],
        "log_snippets": [
            "[etl-pipeline] INFO: Processing batch_id=20260408_0300 (started 3h ago, still running)",
            "[etl-pipeline] INFO: Waiting on lock for table 'events_raw' — held by batch_id=20260407_2100",
            "[etl-pipeline] WARN: Previous batch 20260407_2100 marked complete but lock not released",
            "[postgres-warehouse] INFO: Long-running transaction (pid=4821) holds lock on events_raw: 3h 12m",
            "[etl-pipeline] INFO: No error thrown — pipeline believes upstream batch succeeded",
        ],
        "dependency_graph": {
            "analytics-dashboard": ["analytics-api"],
            "analytics-api": ["postgres-warehouse"],
            "etl-pipeline": ["postgres-warehouse", "kafka-consumer"],
            "kafka-consumer": ["kafka-cluster"],
        },
        "recent_deployments": [],
        "ground_truth": {
            "root_cause": "etl-pipeline",
            "severity": "P2",
            "remediation": "restart_service",
        },
    },
    {
        "id": "hard_3",
        "task_description": "Sporadic 503s hitting 0.1% of users — but all affected users are VIP enterprise accounts.",
        "alerts": [
            {"service": "load-balancer", "metric": "backend_503_rate", "value": "0.1%", "threshold": "0.01%", "firing_for": "45m"},
        ],
        "log_snippets": [
            "[load-balancer] WARN: Backend pod payments-service-v2-7d9f returning 503 for tenant_id in [5001..5200]",
            "[payments-service] INFO: Tenant routing: enterprise tenants (id>5000) routed to v2 pod group",
            "[payments-service-v2] ERROR: License validation failed: license server unreachable",
            "[license-server] WARN: Rate limited by upstream vendor API: 429 Too Many Requests",
            "[payments-service-v2] ERROR: Feature 'enterprise-sla' gated behind license check — failing closed",
        ],
        "dependency_graph": {
            "load-balancer": ["payments-service-v1", "payments-service-v2"],
            "payments-service-v2": ["license-server", "postgres-primary"],
            "license-server": ["vendor-license-api"],
        },
        "recent_deployments": [
            {"service": "payments-service-v2", "version": "v4.0.0", "deployed_at": "2 days ago", "note": "Enterprise tier with license-gated features"},
        ],
        "ground_truth": {
            "root_cause": "license-server",
            "severity": "P1",
            "remediation": "escalate_to_engineer",
        },
    },
]

ALL_SCENARIOS = {
    "easy": EASY_SCENARIOS,
    "medium": MEDIUM_SCENARIOS,
    "hard": HARD_SCENARIOS,
}
