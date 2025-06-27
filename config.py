"""
Configuration management for Redis test application.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import yaml
import json


@dataclass
class RedisConnectionConfig:
    """Redis connection configuration matching lettuce-test-app structure."""
    client_name: str = "redis-py-test-app"
    host: str = "localhost"
    port: int = 6379
    username: Optional[str] = None
    password: Optional[str] = None
    database: int = 0  # Changed from 'db' to match lettuce
    use_tls: bool = False  # Changed from 'ssl' to match lettuce
    verify_peer: bool = False
    timeout: Optional[float] = None  # Connection timeout in seconds
    
    # Cluster configuration
    cluster_mode: bool = False
    cluster_nodes: List[Dict[str, Any]] = field(default_factory=list)
    
    # TLS configuration
    ssl: bool = False
    ssl_cert_reqs: str = "required"
    ssl_ca_certs: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    
    # Connection settings
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = field(default_factory=dict)
    
    # Connection pool settings
    max_connections: int = 50
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    # Retry configuration
    retry_attempts: int = 3
    retry_delay: float = 0.1
    exponential_backoff: bool = True


@dataclass
class WorkloadConfig:
    """Workload configuration matching lettuce-test-app structure."""
    type: str = "get_set"  # Workload type (get_set, redis_commands, multi, pub_sub, etc.)
    max_duration: Optional[str] = "PT60S"  # ISO 8601 duration format

    # Options dictionary for workload-specific configuration
    options: Dict[str, Any] = field(default_factory=dict)

    # Common options (moved from separate fields to options dict)
    def get_option(self, key: str, default=None):
        """Get option value with default."""
        return self.options.get(key, default)

    # Convenience properties for common options
    @property
    def get_set_ratio(self) -> float:
        return self.get_option("getSetRatio", 0.5)

    @property
    def value_size(self) -> int:
        return self.get_option("valueSize", 100)

    @property
    def iteration_count(self) -> int:
        return self.get_option("iterationCount", 1000)

    @property
    def key_prefix(self) -> str:
        return self.get_option("keyPrefix", "test_key")

    @property
    def key_range(self) -> int:
        return self.get_option("keyRange", 10000)

    @property
    def transaction_size(self) -> int:
        return self.get_option("transactionSize", 5)

    @property
    def elements_count(self) -> int:
        return self.get_option("elementsCount", 10)


@dataclass
class TestConfig:
    """Test configuration matching lettuce-test-app structure."""
    mode: str = "standalone"  # standalone, cluster
    clients: int = 1  # Number of client instances
    connections_per_client: int = 1  # Number of connections per client
    threads_per_connection: int = 1  # Number of threads sharing same connection

    # Workload configuration
    workload: WorkloadConfig = field(default_factory=WorkloadConfig)

    # Legacy properties for backward compatibility
    @property
    def client_instances(self) -> int:
        return self.clients

    @property
    def threads_per_client(self) -> int:
        return self.threads_per_connection


@dataclass
class RunnerConfig:
    """Main runner configuration matching lettuce-test-app structure."""
    redis: RedisConnectionConfig = field(default_factory=RedisConnectionConfig)
    test: TestConfig = field(default_factory=TestConfig)

    # Logging and metrics (keeping from original implementation)
    log_level: str = "INFO"
    log_file: Optional[str] = None
    metrics_enabled: bool = True
    metrics_port: int = 8000
    metrics_interval: int = 5

    # Output
    output_file: Optional[str] = None
    quiet: bool = False

    # OpenTelemetry configuration
    otel_enabled: bool = True
    otel_endpoint: Optional[str] = None
    otel_service_name: str = "redis-py-test-app"
    otel_service_version: str = "1.0.0"
    otel_export_interval_ms: int = 5000
    otel_resource_attributes: Dict[str, str] = field(default_factory=dict)


class WorkloadProfiles:
    """Pre-defined workload profiles with intuitive, descriptive names."""

    @staticmethod
    def get_profile(profile_name: str) -> WorkloadConfig:
        """Get a pre-defined workload profile."""
        profiles = {
            "basic_rw": WorkloadConfig(
                type="basic_rw",
                max_duration="PT60S",
                options={
                    "operations": ["SET", "GET", "DEL"],
                    "operation_weights": {"SET": 0.4, "GET": 0.5, "DEL": 0.1},
                    "valueSize": 100,
                    "iterationCount": 1000,
                    "keyPrefix": "test_key",
                    "keyRange": 10000
                }
            ),

            "high_throughput": WorkloadConfig(
                type="high_throughput",
                max_duration="PT60S",
                options={
                    "operations": ["SET", "GET"],
                    "operation_weights": {"SET": 0.4, "GET": 0.6},
                    "valueSize": 50,
                    "iterationCount": 2000,
                    "usePipeline": True,
                    "pipelineSize": 10,
                    "keyPrefix": "perf_test",
                    "keyRange": 50000
                }
            ),

            "list_operations": WorkloadConfig(
                type="list_operations",
                max_duration="PT60S",
                options={
                    "operations": ["LPUSH", "LRANGE", "LPOP"],
                    "operation_weights": {"LPUSH": 0.4, "LRANGE": 0.4, "LPOP": 0.2},
                    "valueSize": 100,
                    "iterationCount": 1000,
                    "elementsCount": 10,
                    "keyPrefix": "list_test"
                }
            ),

            "pubsub_heavy": WorkloadConfig(
                type="pubsub_heavy",
                max_duration="PT60S",
                options={
                    "operations": ["PUBLISH", "SUBSCRIBE"],
                    "operation_weights": {"PUBLISH": 0.7, "SUBSCRIBE": 0.3},
                    "channels": ["channel1", "channel2", "channel3"],
                    "messageSize": 200,
                    "messageCount": 1000
                }
            ),

            "transaction_heavy": WorkloadConfig(
                type="transaction_heavy",
                max_duration="PT60S",
                options={
                    "operations": ["SET", "GET"],
                    "transactionSize": 5,
                    "valueSize": 100,
                    "iterationCount": 500,
                    "keyPrefix": "tx_test"
                }
            ),

            "async_mixed": WorkloadConfig(
                type="async_mixed",
                max_duration="PT60S",
                options={
                    "operations": ["SET", "GET", "LPUSH", "LRANGE"],
                    "operation_weights": {"SET": 0.3, "GET": 0.4, "LPUSH": 0.2, "LRANGE": 0.1},
                    "asyncMode": True,
                    "usePipeline": True,
                    "pipelineSize": 20,
                    "valueSize": 150,
                    "iterationCount": 1500,
                    "awaitAllResponses": True
                }
            )
        }

        return profiles.get(profile_name, WorkloadConfig())

    @staticmethod
    def list_profiles() -> List[str]:
        """List available workload profiles."""
        return ["basic_rw", "high_throughput", "list_operations", "pubsub_heavy", "transaction_heavy", "async_mixed"]


def load_config_from_file(file_path: str) -> RunnerConfig:
    """Load configuration from YAML or JSON file."""
    with open(file_path, 'r') as f:
        if file_path.endswith('.yaml') or file_path.endswith('.yml'):
            data = yaml.safe_load(f)
        else:
            data = json.load(f)

    # Convert nested dictionaries to dataclass instances
    if 'redis' in data:
        data['redis'] = RedisConnectionConfig(**data['redis'])

    if 'test' in data:
        test_data = data['test']
        if 'workload' in test_data:
            test_data['workload'] = WorkloadConfig(**test_data['workload'])
        data['test'] = TestConfig(**test_data)

    return RunnerConfig(**data)


def save_config_to_file(config: RunnerConfig, file_path: str):
    """Save configuration to YAML file."""
    # Convert dataclasses to dictionaries
    config_dict = {
        'redis': config.redis.__dict__,
        'test': {
            'mode': config.test.mode,
            'clients': config.test.clients,
            'connections_per_client': config.test.connections_per_client,
            'threads_per_connection': config.test.threads_per_connection,
            'workload': config.test.workload.__dict__
        },
        'log_level': config.log_level,
        'log_file': config.log_file,
        'metrics_enabled': config.metrics_enabled,
        'metrics_port': config.metrics_port,
        'metrics_interval': config.metrics_interval,
        'output_file': config.output_file,
        'quiet': config.quiet,
        'otel_enabled': config.otel_enabled,
        'otel_endpoint': config.otel_endpoint,
        'otel_service_name': config.otel_service_name,
        'otel_service_version': config.otel_service_version,
        'otel_resource_attributes': config.otel_resource_attributes
    }

    with open(file_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, indent=2)
