"""
Command-line interface for Redis load testing application.
"""
import click
import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

from config import RunnerConfig, TestConfig, RedisConnectionConfig, WorkloadConfig, WorkloadProfiles, get_redis_version
from test_runner import TestRunner

# Load environment variables from .env file
load_dotenv()


def get_env_or_default(env_var: str, default_value, value_type=str):
    """Get environment variable with type conversion and default fallback."""
    env_value = os.getenv(env_var)
    if env_value is None:
        return default_value
    
    try:
        if value_type == bool:
            return env_value.lower() in ('true', '1', 'yes', 'on')
        elif value_type == int:
            return int(env_value)
        elif value_type == float:
            return float(env_value)
        else:
            return env_value
    except (ValueError, TypeError):
        return default_value


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Redis Load Testing Tool - Simulate high-volume Redis operations for testing client resilience during database upgrades."""
    pass


@cli.command()
@click.option('--host', default=lambda: get_env_or_default('REDIS_HOST', 'localhost'), help='Redis host')
@click.option('--port', type=int, default=lambda: get_env_or_default('REDIS_PORT', 6379, int), help='Redis port')
@click.option('--password', default=lambda: get_env_or_default('REDIS_PASSWORD', None), help='Redis password')
@click.option('--db', type=int, default=lambda: get_env_or_default('REDIS_DB', 0, int), help='Redis database number')
@click.option('--cluster', is_flag=True, default=lambda: get_env_or_default('REDIS_CLUSTER', False, bool), help='Use Redis Cluster mode')
@click.option('--cluster-nodes', default=lambda: get_env_or_default('REDIS_CLUSTER_NODES', None), help='Comma-separated list of cluster nodes (host:port)')
@click.option('--ssl', is_flag=True, default=lambda: get_env_or_default('REDIS_SSL', False, bool), help='Use SSL/TLS connection')
@click.option('--ssl-cert-reqs', default=lambda: get_env_or_default('REDIS_SSL_CERT_REQS', 'required'), type=click.Choice(['none', 'optional', 'required']), help='SSL certificate requirements')
@click.option('--ssl-ca-certs', default=lambda: get_env_or_default('REDIS_SSL_CA_CERTS', None), help='Path to CA certificates file')
@click.option('--ssl-certfile', default=lambda: get_env_or_default('REDIS_SSL_CERTFILE', None), help='Path to client certificate file')
@click.option('--ssl-keyfile', default=lambda: get_env_or_default('REDIS_SSL_KEYFILE', None), help='Path to client private key file')
@click.option('--socket-timeout', type=float, default=lambda: get_env_or_default('REDIS_SOCKET_TIMEOUT', 5.0, float), help='Socket timeout in seconds')
@click.option('--socket-connect-timeout', type=float, default=lambda: get_env_or_default('REDIS_SOCKET_CONNECT_TIMEOUT', 5.0, float), help='Socket connect timeout in seconds')
@click.option('--max-connections', type=int, default=lambda: get_env_or_default('REDIS_MAX_CONNECTIONS', 50, int), help='Maximum connections per client')
@click.option('--retry-attempts', type=int, default=lambda: get_env_or_default('REDIS_RETRY_ATTEMPTS', 3, int), help='Number of retry attempts for failed operations')
@click.option('--retry-delay', type=float, default=lambda: get_env_or_default('REDIS_RETRY_DELAY', 0.1, float), help='Delay between retry attempts')
@click.option('--exponential-backoff', is_flag=True, default=lambda: get_env_or_default('REDIS_EXPONENTIAL_BACKOFF', True, bool), help='Use exponential backoff for retries')
@click.option('--client-instances', type=int, default=lambda: get_env_or_default('TEST_CLIENT_INSTANCES', 1, int), help='Number of client instances')
@click.option('--connections-per-client', type=int, default=lambda: get_env_or_default('TEST_CONNECTIONS_PER_CLIENT', 10, int), help='Number of connections per client instance')
@click.option('--threads-per-client', type=int, default=lambda: get_env_or_default('TEST_THREADS_PER_CLIENT', 4, int), help='Number of threads per client instance')
@click.option('--duration', type=int, default=lambda: get_env_or_default('TEST_DURATION', None, int), help='Test duration in seconds (unlimited if not specified)')
@click.option('--target-ops-per-second', type=int, default=lambda: get_env_or_default('TEST_TARGET_OPS_PER_SECOND', None, int), help='Target operations per second')
@click.option('--workload-profile', type=click.Choice(WorkloadProfiles.list_profiles()), default=lambda: get_env_or_default('TEST_WORKLOAD_PROFILE', None), help='Pre-defined workload profile')
@click.option('--operations', default=lambda: get_env_or_default('TEST_OPERATIONS', 'SET,GET'), help='Comma-separated list of Redis operations')
@click.option('--operation-weights', default=lambda: get_env_or_default('TEST_OPERATION_WEIGHTS', None), help='JSON string of operation weights (e.g., {"SET": 0.4, "GET": 0.6})')
@click.option('--key-prefix', default=lambda: get_env_or_default('TEST_KEY_PREFIX', 'test_key'), help='Prefix for generated keys')
@click.option('--key-range', type=int, default=lambda: get_env_or_default('TEST_KEY_RANGE', 10000, int), help='Range of key IDs to use')
@click.option('--value-size-min', type=int, default=lambda: get_env_or_default('TEST_VALUE_SIZE_MIN', 100, int), help='Minimum value size in bytes')
@click.option('--value-size-max', type=int, default=lambda: get_env_or_default('TEST_VALUE_SIZE_MAX', 1000, int), help='Maximum value size in bytes')
@click.option('--read-write-ratio', type=float, default=lambda: get_env_or_default('TEST_READ_WRITE_RATIO', 0.7, float), help='Ratio of read operations (0.0-1.0)')
@click.option('--use-pipeline', is_flag=True, default=lambda: get_env_or_default('TEST_USE_PIPELINE', False, bool), help='Use Redis pipelining')
@click.option('--pipeline-size', type=int, default=lambda: get_env_or_default('TEST_PIPELINE_SIZE', 10, int), help='Number of operations per pipeline')
@click.option('--async-mode', is_flag=True, default=lambda: get_env_or_default('TEST_ASYNC_MODE', False, bool), help='Use asynchronous operations')
@click.option('--pubsub-channels', default=lambda: get_env_or_default('TEST_PUBSUB_CHANNELS', None), help='Comma-separated list of pub/sub channels')
@click.option('--transaction-size', type=int, default=lambda: get_env_or_default('TEST_TRANSACTION_SIZE', 5, int), help='Number of operations per transaction')
@click.option('--log-level', default=lambda: get_env_or_default('LOG_LEVEL', 'INFO'), type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), help='Logging level')
@click.option('--log-file', default=lambda: get_env_or_default('LOG_FILE', None), help='Log file path')
@click.option('--metrics-enabled/--no-metrics', default=lambda: get_env_or_default('METRICS_ENABLED', True, bool), help='Enable metrics collection')
@click.option('--metrics-port', type=int, default=lambda: get_env_or_default('METRICS_PORT', 8000, int), help='Prometheus metrics server port')
@click.option('--metrics-interval', type=int, default=lambda: get_env_or_default('METRICS_INTERVAL', 5, int), help='Metrics reporting interval in seconds')
@click.option('--otel-enabled', is_flag=True, default=lambda: get_env_or_default('OTEL_ENABLED', True, bool), help='Enable OpenTelemetry')
@click.option('--otel-endpoint', default=lambda: get_env_or_default('OTEL_EXPORTER_OTLP_ENDPOINT', None), help='OpenTelemetry OTLP endpoint')
@click.option('--otel-service-name', default=lambda: get_env_or_default('OTEL_SERVICE_NAME', 'redis-load-test'), help='OpenTelemetry service name')
@click.option('--otel-export-interval', type=int, default=lambda: get_env_or_default('OTEL_EXPORT_INTERVAL', 5000, int), help='OpenTelemetry export interval in milliseconds')
@click.option('--app-name', default=lambda: get_env_or_default('APP_NAME', 'python'), help='Application name for multi-app filtering (python, go, java, etc.)')
@click.option('--instance-id', default=lambda: get_env_or_default('INSTANCE_ID', None), help='Unique instance identifier (auto-generated if not provided)')
@click.option('--run-id', default=lambda: get_env_or_default('RUN_ID', None), help='Unique run identifier (auto-generated if not provided)')
@click.option('--version', default=lambda: get_env_or_default('VERSION', None), help='Version identifier (defaults to redis-py package version)')
@click.option('--output-file', default=lambda: get_env_or_default('OUTPUT_FILE', None), help='Output file for final test summary (JSON). If not provided, prints to stdout.')
@click.option('--quiet', is_flag=True, default=False, help='Suppress periodic stats output')
@click.option('--config-file', default=lambda: get_env_or_default('CONFIG_FILE', None), help='Load configuration from YAML/JSON file')
@click.option('--save-config', help='Save current configuration to file')
def run(**kwargs):
    """Run Redis load test with specified configuration."""
    
    try:
        # Load configuration from file if specified
        if kwargs['config_file']:
            from config import load_config_from_file
            config = load_config_from_file(kwargs['config_file'])
            click.echo(f"Loaded configuration from {kwargs['config_file']}")
        else:
            # Build configuration from command line arguments
            config = _build_config_from_args(kwargs)
        
        # Save configuration if requested
        if kwargs['save_config']:
            from config import save_config_to_file
            save_config_to_file(config, kwargs['save_config'])
            click.echo(f"Configuration saved to {kwargs['save_config']}")
            return
        
        # Validate configuration
        _validate_config(config)
        
        # Run the test
        runner = TestRunner(config)
        runner.start()
        
    except KeyboardInterrupt:
        click.echo("\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def list_profiles():
    """List available workload profiles."""
    profiles = WorkloadProfiles.list_profiles()
    click.echo("Available workload profiles:")
    for profile in profiles:
        workload = WorkloadProfiles.get_profile(profile)
        operations = workload.get_option("operations", [workload.type])
        if isinstance(operations, list):
            ops_str = ', '.join(operations)
        else:
            ops_str = workload.type
        click.echo(f"  {profile}: {ops_str}")


@cli.command()
@click.argument('profile_name', type=click.Choice(WorkloadProfiles.list_profiles()))
def describe_profile(profile_name):
    """Describe a specific workload profile."""
    workload = WorkloadProfiles.get_profile(profile_name)

    click.echo(f"Workload Profile: {profile_name}")
    click.echo(f"Type: {workload.type}")
    click.echo(f"Duration: {workload.max_duration}")

    # Show operations if available
    operations = workload.get_option("operations")
    if operations:
        click.echo(f"Operations: {', '.join(operations)}")

        # Show operation weights if available
        weights = workload.get_option("operation_weights")
        if weights:
            click.echo("Operation Weights:")
            for op, weight in weights.items():
                click.echo(f"  {op}: {weight}")

    # Show key configuration options
    value_size = workload.get_option("valueSize")
    if value_size:
        click.echo(f"Value Size: {value_size} bytes")

    iteration_count = workload.get_option("iterationCount")
    if iteration_count:
        click.echo(f"Iteration Count: {iteration_count}")

    # Show pipeline configuration
    use_pipeline = workload.get_option("usePipeline", False)
    click.echo(f"Pipeline: {'Yes' if use_pipeline else 'No'}")
    if use_pipeline:
        pipeline_size = workload.get_option("pipelineSize", 10)
        click.echo(f"Pipeline Size: {pipeline_size}")

    # Show async configuration
    async_mode = workload.get_option("asyncMode", False)
    click.echo(f"Async Mode: {'Yes' if async_mode else 'No'}")

    # Show channels if available
    channels = workload.get_option("channels")
    if channels:
        click.echo(f"Channels: {', '.join(channels)}")

    # Show all other options
    click.echo("All Options:")
    for key, value in workload.options.items():
        click.echo(f"  {key}: {value}")

@cli.command()
def test_connection():
    """Test Redis connection with current configuration."""
    try:
        # Build minimal config for connection test
        redis_config = RedisConnectionConfig(
            host=get_env_or_default('REDIS_HOST', 'localhost'),
            port=get_env_or_default('REDIS_PORT', 6379, int),
            password=get_env_or_default('REDIS_PASSWORD', None),
            database=get_env_or_default('REDIS_DB', 0, "int"),
            cluster_mode=get_env_or_default('REDIS_CLUSTER', False, bool),
            ssl=get_env_or_default('REDIS_SSL', False, bool)
        )
        
        from redis_client import RedisClientManager
        client = RedisClientManager(redis_config)
        
        # Test basic operations
        client.ping()
        info = client.get_info()
        
        click.echo("✓ Redis connection successful!")
        click.echo(f"Redis version: {info.get('redis_version', 'unknown')}")
        click.echo(f"Redis mode: {'cluster' if redis_config.cluster_mode else 'standalone'}")
        click.echo(f"Connected clients: {info.get('connected_clients', 'unknown')}")
        
        client.close()

    except Exception as e:
        click.echo(f"✗ Redis connection failed: {e}", err=True)
        sys.exit(1)


def _build_config_from_args(kwargs) -> RunnerConfig:
    """Build TestConfig from command line arguments."""

    # Parse cluster nodes
    cluster_nodes = []
    if kwargs['cluster_nodes']:
        for node in kwargs['cluster_nodes'].split(','):
            host, port = node.strip().split(':')
            cluster_nodes.append({'host': host, 'port': int(port)})

    # Parse operation weights
    operation_weights = {}
    if kwargs['operation_weights']:
        operation_weights = json.loads(kwargs['operation_weights'])

    # Parse pub/sub channels
    pubsub_channels = []
    if kwargs['pubsub_channels']:
        pubsub_channels = [ch.strip() for ch in kwargs['pubsub_channels'].split(',')]

    # Build Redis connection config
    redis_config = RedisConnectionConfig(
        host=kwargs['host'],
        port=kwargs['port'],
        password=kwargs['password'],
        database=kwargs['db'],
        cluster_mode=kwargs['cluster'],
        cluster_nodes=cluster_nodes,
        ssl=kwargs['ssl'],
        ssl_cert_reqs=kwargs['ssl_cert_reqs'],
        ssl_ca_certs=kwargs['ssl_ca_certs'],
        ssl_certfile=kwargs['ssl_certfile'],
        ssl_keyfile=kwargs['ssl_keyfile'],
        socket_timeout=kwargs['socket_timeout'],
        socket_connect_timeout=kwargs['socket_connect_timeout'],
        max_connections=kwargs['max_connections'],
        retry_attempts=kwargs['retry_attempts'],
        retry_delay=kwargs['retry_delay'],
        exponential_backoff=kwargs['exponential_backoff']
    )

    # Build workload config
    if kwargs['workload_profile']:
        workload_config = WorkloadProfiles.get_profile(kwargs['workload_profile'])
    else:
        operations = [op.strip() for op in kwargs['operations'].split(',')]
        workload_config = WorkloadConfig(
            operations=operations,
            operation_weights=operation_weights,
            key_prefix=kwargs['key_prefix'],
            key_range=kwargs['key_range'],
            value_size_min=kwargs['value_size_min'],
            value_size_max=kwargs['value_size_max'],
            read_write_ratio=kwargs['read_write_ratio'],
            use_pipeline=kwargs['use_pipeline'],
            pipeline_size=kwargs['pipeline_size'],
            async_mode=kwargs['async_mode'],
            pubsub_channels=pubsub_channels,
            transaction_size=kwargs['transaction_size']
        )

    # Build test config
    test_config = TestConfig(
        mode="cluster" if kwargs.get('cluster', False) else "standalone",
        clients=kwargs['client_instances'],
        connections_per_client=kwargs['connections_per_client'],
        threads_per_connection=kwargs['threads_per_client'],
        duration=kwargs['duration'],  # Add duration support
        workload=workload_config
    )

    # Build concatenated app name with workload profile
    base_app_name = kwargs['app_name']
    workload_profile_name = kwargs.get('workload_profile', 'custom')
    concatenated_app_name = f"{base_app_name}-{workload_profile_name}"

    # Build main runner config
    config = RunnerConfig(
        redis=redis_config,
        test=test_config,
        log_level=kwargs['log_level'],
        log_file=kwargs['log_file'],
        metrics_enabled=kwargs['metrics_enabled'],
        metrics_port=kwargs['metrics_port'],
        metrics_interval=kwargs['metrics_interval'],
        output_file=kwargs['output_file'],
        quiet=kwargs['quiet'],
        otel_enabled=kwargs['otel_enabled'],
        otel_endpoint=kwargs['otel_endpoint'],
        otel_service_name=kwargs['otel_service_name'],
        otel_export_interval_ms=kwargs['otel_export_interval'],
        app_name=concatenated_app_name,
        instance_id=kwargs['instance_id'],
        run_id=kwargs['run_id'],
        version=kwargs['version'] or get_redis_version()
    )

    return config


def _validate_config(config: RunnerConfig):
    """Validate configuration parameters."""
    if config.test.client_instances <= 0:
        raise ValueError("client_instances must be greater than 0")

    if config.test.connections_per_client <= 0:
        raise ValueError("connections_per_client must be greater than 0")

    if config.test.threads_per_client <= 0:
        raise ValueError("threads_per_client must be greater than 0")

    if not config.test.workload.type:
        raise ValueError("Workload type must be specified")


if __name__ == '__main__':
    cli()
