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
            "severity": "P1",
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
        # Root cause: redis-cache / P1 / restart_service
        # Red herring: user-service deployed 45m ago looks suspicious
        # Victims: api-gateway, auth-service, user-service all alert; redis-cache evidence comes last
        "task_description": "Multiple services degraded simultaneously. Identify the shared dependency causing the cascade.",
        "alerts": [
            {"service": "api-gateway", "metric": "latency_p99", "value": "7800ms", "threshold": "200ms", "firing_for": "10m"},
            {"service": "auth-service", "metric": "error_rate", "value": "28%", "threshold": "1%", "firing_for": "10m"},
            {"service": "user-service", "metric": "error_rate", "value": "22%", "threshold": "1%", "firing_for": "9m"},
            {"service": "session-service", "metric": "timeout_rate", "value": "35%", "threshold": "2%", "firing_for": "9m"},
            {"service": "redis-cache", "metric": "used_memory_percent", "value": "99%", "threshold": "80%", "firing_for": "12m"},
        ],
        "log_snippets": [
            "[auth-service] ERROR: Session lookup failed — connection pool exhausted after 5000ms",
            "[user-service] ERROR: Cache read timed out — falling back to DB, latency spike observed",
            "[session-service] ERROR: Write to session store failed — operation timed out after 4800ms",
            "[api-gateway] WARN: auth-service and user-service both exceeding SLA — upstream degraded",
            "[redis-cache] WARN: Eviction rate spiking — maxmemory policy active, keys being dropped under load",
        ],
        "dependency_graph": {
            "api-gateway": ["auth-service", "user-service", "payments-service"],
            "auth-service": ["redis-cache", "postgres-primary"],
            "user-service": ["redis-cache", "postgres-replica"],
            "session-service": ["redis-cache"],
            "payments-service": ["postgres-primary"],
        },
        "recent_deployments": [
            {"service": "user-service", "version": "v1.9.0", "deployed_at": "45 minutes ago", "note": "Enabled aggressive read-through caching — cache hit rate expected to increase"},
        ],
        "ground_truth": {
            "root_cause": "redis-cache",
            "severity": "P1",
            "remediation": "restart_service",
        },
    },
    {
        # Root cause: postgres-replica / P1 / failover_db
        # Red herring: payments-gateway deployed 45m ago looks like the culprit for duplicate charges
        # Victims: payments-service and stripe-api alert; all logs are application-layer only
        # LLM must infer replica divergence from write-then-read inconsistency patterns alone
        "id": "medium_2",
        "task_description": "Intermittent payment failures with duplicate charge complaints. Some transactions succeed. Identify root cause.",
        "alerts": [
            {"service": "payments-service", "metric": "error_rate", "value": "16%", "threshold": "1%", "firing_for": "25m"},
            {"service": "payments-service", "metric": "duplicate_transaction_rate", "value": "4.2%", "threshold": "0.01%", "firing_for": "24m"},
            {"service": "stripe-api", "metric": "idempotency_conflict_rate", "value": "3.8%", "threshold": "0.1%", "firing_for": "22m"},
            {"service": "order-service", "metric": "fulfillment_error_rate", "value": "6%", "threshold": "0.5%", "firing_for": "20m"},
        ],
        "log_snippets": [
            "[payments-service] ERROR: Charge attempt for txn_id=8842f rejected — payment already exists, but pre-check returned no record",
            "[order-service] ERROR: Order ORD-19920 marked unfulfilled — inventory showed 3 units available at time of purchase, now shows 0",
            "[payments-service] WARN: Balance read immediately after write returned stale value — retrying with strong consistency flag",
            "[payments-service] ERROR: Idempotency key txn_id=9021a already processed according to stripe-api, but local state shows pending",
            "[payments-service] WARN: Read path returning inconsistent state on 4% of requests — writes confirmed on primary but reads diverging",
        ],
        "dependency_graph": {
            "payments-service": ["postgres-primary", "postgres-replica", "payments-gateway"],
            "order-service": ["postgres-replica", "inventory-service"],
            "inventory-service": ["postgres-replica"],
            "payments-gateway": ["stripe-api"],
        },
        "recent_deployments": [
            {"service": "payments-gateway", "version": "v2.4.0", "deployed_at": "45 minutes ago", "note": "Updated idempotency key generation — switched from UUID v4 to UUID v7 for ordering guarantees"},
        ],
        "ground_truth": {
            "root_cause": "postgres-replica",
            "severity": "P1",
            "remediation": "failover_db",
        },
    },
    {
        # Root cause: api-gateway / P2 / rollback_deployment
        # Red herrings: cdn-edge config update (looks like misconfigured TTL) and auth-service deploy
        # LLM must correlate api-gateway deploy timing (33m ago) with CDN miss rate spike onset (30m ago)
        # No cache-busting or Cache-Control mentioned in logs — only business-layer symptoms
        "id": "medium_3",
        "task_description": "CDN costs have spiked 9x and users are reporting slow page loads. Origin servers are overloaded. Nothing looks broken. Find what changed.",
        "alerts": [
            {"service": "cdn-edge", "metric": "cache_hit_rate", "value": "4%", "threshold": "85%", "firing_for": "30m"},
            {"service": "cdn-edge", "metric": "egress_cost_usd_per_hour", "value": "340", "threshold": "38", "firing_for": "30m"},
            {"service": "content-service", "metric": "request_rate", "value": "14200rps", "threshold": "1800rps", "firing_for": "29m"},
            {"service": "api-gateway", "metric": "cpu_utilization", "value": "88%", "threshold": "60%", "firing_for": "27m"},
        ],
        "log_snippets": [
            "[cdn-edge] WARN: Cache hit ratio dropped from 87% to 4% — all traffic now hitting origin",
            "[content-service] WARN: Request rate 7.9x above baseline — origin serving traffic that CDN should absorb",
            "[cdn-edge] INFO: No CDN configuration changes detected — TTL rules and routing policies unchanged",
            "[api-gateway] WARN: Sustained high CPU — processing 7x normal inbound request volume since 14:28 UTC",
            "[cdn-edge] WARN: Cache miss spike onset at 14:29 UTC — correlates with upstream response characteristic change",
        ],
        "dependency_graph": {
            "cdn-edge": ["api-gateway", "static-assets-service"],
            "api-gateway": ["auth-service", "content-service", "static-assets-service"],
            "auth-service": ["postgres-primary"],
            "content-service": ["postgres-replica"],
        },
        "recent_deployments": [
            {"service": "cdn-edge", "version": "config-v3.8", "deployed_at": "2 hours ago", "note": "Updated geo-routing rules — traffic now balanced across 3 PoPs instead of 2"},
            {"service": "auth-service", "version": "v4.1.0", "deployed_at": "55 minutes ago", "note": "Stricter token validation — rejects tokens missing aud claim"},
            {"service": "api-gateway", "version": "v5.0.2", "deployed_at": "33 minutes ago", "note": "Response pipeline configuration update"},
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
        # Root cause: feature-flag-service (2 hops: api-gateway → auth-service → feature-flag-service)
        # Red herring: auth-service deployed 18m ago, looks like the culprit
        # Logs: all victim symptoms — no mention of feature-flag-service
        "id": "hard_1",
        "task_description": "Full production outage. Multiple teams paging. You have 5 minutes. Find root cause and act.",
        "alerts": [
            {"service": "api-gateway", "metric": "error_rate", "value": "89%", "threshold": "1%", "firing_for": "5m"},
            {"service": "auth-service", "metric": "latency_p99", "value": "43000ms", "threshold": "300ms", "firing_for": "5m"},
            {"service": "payments-service", "metric": "error_rate", "value": "87%", "threshold": "1%", "firing_for": "5m"},
            {"service": "notification-service", "metric": "error_rate", "value": "81%", "threshold": "1%", "firing_for": "4m"},
            {"service": "user-service", "metric": "latency_p99", "value": "41000ms", "threshold": "300ms", "firing_for": "4m"},
            {"service": "postgres-primary", "metric": "active_queries", "value": "940", "threshold": "100", "firing_for": "6m"},
        ],
        "log_snippets": [
            "[auth-service] ERROR: Upstream call did not respond within 44s deadline — request aborted",
            "[payments-service] ERROR: Synchronous dependency exceeded 43s timeout — propagating failure to caller",
            "[postgres-primary] ERROR: Lock wait timeout — 370 queries blocked behind a long-running transaction",
            "[notification-service] WARN: Internal dependency unresponsive for 40s, request abandoned",
            "[user-service] WARN: Response time from shared dependency exceeds SLA — serving degraded",
            "[api-gateway] WARN: All upstreams reporting >30s latency, no circuit breaker active",
        ],
        "dependency_graph": {
            "api-gateway": ["auth-service", "payments-service", "notification-service", "user-service"],
            "auth-service": ["feature-flag-service", "postgres-primary"],
            "payments-service": ["feature-flag-service", "postgres-primary"],
            "notification-service": ["feature-flag-service", "user-service"],
            "user-service": ["postgres-replica", "feature-flag-service"],
            "feature-flag-service": ["postgres-primary", "remote-config-api"],
        },
        "recent_deployments": [
            {"service": "auth-service", "version": "v8.2.0", "deployed_at": "18 minutes ago", "note": "Added per-request session validation to enforce new compliance policy"},
            {"service": "feature-flag-service", "version": "v1.2.0", "deployed_at": "8 minutes ago", "note": "Configuration parameter change"},
        ],
        "ground_truth": {
            "root_cause": "feature-flag-service",
            "severity": "P1",
            "remediation": "rollback_deployment",
        },
    },
    {
        # Root cause: etl-pipeline (2 hops: analytics-dashboard → analytics-api → postgres-warehouse ← etl-pipeline)
        # Red herring: kafka-consumer deployed 4h ago, consumer lag looks causal
        # Logs: warehouse lock, stale reads, kafka lag — etl-pipeline never named
        "id": "hard_2",
        "task_description": "Data pipeline is failing silently. End users see stale data. No obvious error alerts.",
        "alerts": [
            {"service": "analytics-dashboard", "metric": "data_freshness_minutes", "value": "231", "threshold": "15", "firing_for": "3h 51m"},
            {"service": "reporting-service", "metric": "stale_data_rate", "value": "94%", "threshold": "5%", "firing_for": "3h 40m"},
            {"service": "analytics-api", "metric": "query_duration_p99", "value": "9200ms", "threshold": "500ms", "firing_for": "3h 30m"},
            {"service": "postgres-warehouse", "metric": "long_running_transactions", "value": "3", "threshold": "0", "firing_for": "3h 50m"},
        ],
        "log_snippets": [
            "[postgres-warehouse] WARN: Write lock on table 'events_raw' held for 3h 51m by pid=7823 — all writers blocked",
            "[analytics-api] WARN: Query returning stale snapshot — events_processed last updated 4 hours ago",
            "[kafka-consumer] INFO: Consumer lag growing on topic 'raw_events' — 2.4M messages pending, no writer draining",
            "[reporting-service] WARN: Scheduled report refresh blocked — upstream data has not advanced in 3h 47m",
            "[data-validator] WARN: Write lock acquisition failed on events_raw — queued behind pid=7823, retrying",
            "[postgres-warehouse] INFO: Transaction pid=7823 open since 03:12 UTC — no commit or rollback issued",
        ],
        "dependency_graph": {
            "analytics-dashboard": ["analytics-api", "reporting-service"],
            "analytics-api": ["postgres-warehouse"],
            "reporting-service": ["analytics-api"],
            "etl-pipeline": ["postgres-warehouse", "kafka-consumer", "data-validator"],
            "data-validator": ["postgres-warehouse"],
            "kafka-consumer": ["kafka-cluster"],
        },
        "recent_deployments": [
            {"service": "kafka-consumer", "version": "v2.1.0", "deployed_at": "4 hours ago", "note": "Increased partition thread count to reduce consumer lag under peak load"},
        ],
        "ground_truth": {
            "root_cause": "etl-pipeline",
            "severity": "P2",
            "remediation": "restart_service",
        },
    },
    {
        # Root cause: license-server (3 hops: load-balancer → payments-service-v2 → entitlement-checker → license-server)
        # Red herring: entitlement-checker deployed 3h ago with fail-fast timeouts, looks responsible
        # Logs: 503s on v2 pod group, entitlement timeouts, upstream 429 — license-server never named
        "id": "hard_3",
        "task_description": "Sporadic 503s hitting 0.1% of users — but all affected users are VIP enterprise accounts.",
        "alerts": [
            {"service": "api-gateway", "metric": "error_rate_enterprise_tier", "value": "8.3%", "threshold": "0.1%", "firing_for": "52m"},
            {"service": "load-balancer", "metric": "backend_503_rate", "value": "0.1%", "threshold": "0.01%", "firing_for": "52m"},
            {"service": "payments-service-v2", "metric": "request_timeout_rate", "value": "11%", "threshold": "0.5%", "firing_for": "50m"},
            {"service": "entitlement-checker", "metric": "latency_p99", "value": "27500ms", "threshold": "200ms", "firing_for": "55m"},
        ],
        "log_snippets": [
            "[payments-service-v2] ERROR: Entitlement check timed out after 27s for tenant_id=5142 — request rejected",
            "[entitlement-checker] ERROR: Retry 5/5 exhausted — upstream returning 429, exponential backoff triggered",
            "[load-balancer] WARN: Backend pod group returning 503 for requests in tenant_id range [5001..5200]",
            "[payments-service-v2] INFO: Enterprise capability gated on entitlement check — failing closed per policy",
            "[api-gateway] WARN: Error rate elevated only on /v2/payments enterprise routing path",
            "[entitlement-checker] WARN: Downstream dependency rate-limiting all outbound calls — quota exceeded",
        ],
        "dependency_graph": {
            "api-gateway": ["load-balancer"],
            "load-balancer": ["payments-service-v1", "payments-service-v2"],
            "payments-service-v2": ["entitlement-checker", "postgres-primary", "redis-cache"],
            "payments-service-v1": ["postgres-primary"],
            "entitlement-checker": ["license-server", "feature-store"],
            "license-server": ["vendor-license-api"],
        },
        "recent_deployments": [
            {"service": "entitlement-checker", "version": "v2.3.0", "deployed_at": "3 hours ago", "note": "Reduced upstream timeout from 60s to 5s — faster failure detection"},
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
