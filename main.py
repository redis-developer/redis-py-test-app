#!/usr/bin/env python3
"""
Redis Load Testing Application

A comprehensive Redis load testing tool designed to simulate high-volume operations
for testing client resilience during database upgrades.

Features:
- Multi-threaded architecture supporting 100K+ ops/sec
- Support for standalone and cluster Redis deployments
- Comprehensive metrics collection with OpenTelemetry and Prometheus
- Configurable workload profiles
- Connection resilience and retry logic
- Environment variable configuration support
"""

from cli import cli

if __name__ == '__main__':
    cli()
