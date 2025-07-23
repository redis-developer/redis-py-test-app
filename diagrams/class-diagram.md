# Redis Test Application - Class Diagram

## Core Classes and Their Relationships

```mermaid
classDiagram
    %% Configuration Classes
    class RunnerConfig {
        +RedisConnectionConfig redis
        +TestConfig test
        +str log_level
        +str log_file
        +int metrics_interval
        +str output_file
        +bool quiet
        +str otel_endpoint
        +str otel_service_name
        +str otel_service_version
        +int otel_export_interval_ms
        +Dict[str,str] otel_resource_attributes
        +str app_name
        +str instance_id
        +str run_id
        +str version
    }

    class RedisConnectionConfig {
        +str client_name
        +str host
        +int port
        +str username
        +str password
        +int database
        +bool use_tls
        +bool verify_peer
        +float timeout
        +bool cluster_mode
        +List[Dict[str,Any]] cluster_nodes
        +bool ssl
        +str ssl_cert_reqs
        +str ssl_ca_certs
        +str ssl_certfile
        +str ssl_keyfile
        +float socket_timeout
        +float socket_connect_timeout
        +bool socket_keepalive
        +Dict[str,int] socket_keepalive_options
        +int max_connections
        +bool retry_on_timeout
        +int health_check_interval
        +int retry_attempts
        +float retry_delay
        +bool exponential_backoff
    }

    class TestConfig {
        +str mode
        +int clients
        +int connections_per_client
        +int threads_per_connection
        +int duration
        +int target_ops_per_second
        +WorkloadConfig workload
        +client_instances() int
        +threads_per_client() int
    }

    class WorkloadConfig {
        +str type
        +str max_duration
        +Dict[str,Any] options
        +get_option(key: str, default) Any
        +get_set_ratio() float
        +value_size() int
        +iteration_count() int
        +key_prefix() str
        +key_range() int
        +transaction_size() int
        +elements_count() int
    }

    class WorkloadProfiles {
        <<static>>
        +get_profile(profile_name: str) WorkloadConfig
        +list_profiles() List[str]
    }

    %% Main Application Classes
    class TestRunner {
        +RunnerConfig config
        +Logger logger
        +MetricsCollector metrics
        +List[RedisClientPool] _client_pools
        +List[Thread] _workload_threads
        +Thread _stats_thread
        +Event _stop_event
        +bool _running
        +run() void
        +stop() void
        +_create_client_pools() List[RedisClientPool]
        +_worker_thread(pool: RedisClientPool, thread_id: int) void
        +_stats_reporter() void
        +get_current_stats() Dict[str,Any]
    }

    class RedisClientManager {
        +RedisConnectionConfig config
        +Logger logger
        +MetricsCollector metrics
        +Union[Redis,RedisCluster] _client
        +RLock _connection_lock
        +float _last_connection_attempt
        +float _connection_backoff
        +Dict[str,Any] _pool_kwargs
        +_connect() bool
        +_connect_standalone() void
        +_connect_cluster() void
        +_build_pool_kwargs() Dict[str,Any]
        +is_connected() bool
        +reconnect() bool
        +_execute_with_metrics(operation: str, func: callable, *args, **kwargs) Any
        +get(key: str) Any
        +set(key: str, value: Any) bool
        +delete(key: str) int
        +incr(key: str) int
        +lpush(key: str, *values) int
        +rpop(key: str) Any
        +lrange(key: str, start: int, end: int) List
        +lpop(key: str) Any
        +rpush(key: str, *values) int
        +publish(channel: str, message: str) int
        +pubsub() PubSub
        +pipeline() Pipeline
        +ping() bool
        +close() void
    }

    class RedisClientPool {
        +RedisConnectionConfig config
        +int pool_size
        +Logger logger
        +List[RedisClientManager] _clients
        +List[RedisClientManager] _available_clients
        +Lock _lock
        +_initialize_pool() void
        +get_client() RedisClientManager
        +return_client(client: RedisClientManager) void
        +close_all() void
        +get_pool_stats() Dict[str,int]
    }

    %% Workload Classes
    class BaseWorkload {
        <<abstract>>
        +WorkloadConfig config
        +RedisClientManager client
        +Logger logger
        +MetricsCollector metrics
        +int _key_counter
        +Lock _key_lock
        +_generate_key() str
        +_generate_value() str
        +_choose_operation() str
        +execute_operation()* int
        +run(duration: int, target_ops_per_second: int) void
        +cleanup() void
    }

    class BasicWorkload {
        +execute_operation() int
    }

    class ListWorkload {
        +execute_operation() int
    }

    class PipelineWorkload {
        +execute_operation() int
    }

    class TransactionWorkload {
        +execute_operation() int
    }

    class PubSubWorkload {
        +PubSub _pubsub
        +Thread _subscriber_thread
        +Event _stop_subscriber
        +execute_operation() int
        +_subscriber_worker() void
        +cleanup() void
    }

    class WorkloadFactory {
        <<static>>
        +create_workload(config: WorkloadConfig, client: RedisClientManager) BaseWorkload
    }

    %% Relationships
    RunnerConfig *-- RedisConnectionConfig
    RunnerConfig *-- TestConfig
    TestConfig *-- WorkloadConfig
    TestRunner *-- RunnerConfig
    TestRunner *-- RedisClientPool
    RedisClientPool *-- RedisClientManager
    RedisClientManager *-- RedisConnectionConfig
    BaseWorkload *-- WorkloadConfig
    BaseWorkload *-- RedisClientManager
    BasicWorkload --|> BaseWorkload
    ListWorkload --|> BaseWorkload
    PipelineWorkload --|> BaseWorkload
    TransactionWorkload --|> BaseWorkload
    PubSubWorkload --|> BaseWorkload
    WorkloadFactory ..> BaseWorkload : creates
    WorkloadProfiles ..> WorkloadConfig : creates
```

## Metrics and Logging Classes

```mermaid
classDiagram
    %% Metrics Classes
    class MetricsCollector {
        +str otel_endpoint
        +str service_name
        +str service_version
        +int otel_export_interval_ms
        +str app_name
        +str instance_id
        +str run_id
        +str version
        +RLock _lock
        +Dict[str,OperationMetrics] _metrics
        +float _start_time
        +float _last_reset_time
        +int _connection_attempts
        +int _connection_failures
        +int _connection_drops
        +int _reconnection_count
        +float _reconnection_duration
        +Meter meter
        +Counter otel_operations_counter
        +Histogram otel_operation_duration
        +Counter otel_connections_counter
        +Counter otel_connection_drops_counter
        +Histogram otel_reconnection_duration
        +Gauge otel_active_connections
        +Counter otel_pubsub_operations_counter
        +_setup_opentelemetry() void
        +record_operation(operation: str, duration: float, success: bool, error_type: str) void
        +record_connection_attempt(success: bool) void
        +record_connection_drop() void
        +record_reconnection(duration: float) void
        +update_active_connections(count: int) void
        +record_pubsub_operation(operation: str, success: bool) void
        +get_overall_stats() Dict[str,Any]
        +get_final_summary() Dict[str,Any]
        +reset_interval_metrics() void
        +export_to_json(filename: str) void
    }

    class OperationMetrics {
        +int total_count
        +int success_count
        +int error_count
        +float total_duration
        +Deque[float] latencies
        +Dict[str,int] errors_by_type
    }

    %% Logging Classes
    class RedisTestLogger {
        +int log_level
        +str log_file
        +Logger logger
        +_setup_logging() void
        +get_logger() Logger
        +log_error_with_traceback(message: str, exception: Exception) void
        +log_operation_result(operation: str, success: bool, duration: float, error: str) void
        +log_connection_event(event_type: str, details: Dict) void
    }

    %% CLI Functions (not classes)
    note for CLI "CLI is implemented as functions in cli.py:
    - cli() - Main CLI group
    - run() - Run load test
    - list_profiles() - List workload profiles
    - describe_profile() - Describe profile
    - test_connection() - Test Redis connection"

    %% Relationships
    MetricsCollector *-- OperationMetrics
    TestRunner *-- MetricsCollector
    TestRunner *-- RedisTestLogger
    RedisClientManager *-- MetricsCollector
    RedisClientManager *-- RedisTestLogger
    BaseWorkload *-- MetricsCollector
    BaseWorkload *-- RedisTestLogger
```
