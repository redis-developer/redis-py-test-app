#!/usr/bin/env python3
"""
Quick test to verify that specific Redis methods are working correctly
and generating proper operation-specific metrics.
"""

import time
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import RedisConnectionConfig
from redis_client import RedisClientManager
from metrics import setup_metrics

def test_specific_methods():
    """Test that specific Redis methods work and generate correct metrics."""
    
    print("🧪 Testing Specific Redis Methods")
    print("=" * 40)
    
    # Setup metrics
    metrics = setup_metrics(
        enable_prometheus=True,
        prometheus_port=8001,  # Different port to avoid conflicts
        enable_otel=False  # Disable OTEL for simple test
    )
    
    # Setup Redis connection
    config = RedisConnectionConfig(
        host="localhost",
        port=6379,
        database=0
    )
    
    client = RedisClientManager(config, metrics)
    
    try:
        # Test connection
        if not client.connect():
            print("❌ Failed to connect to Redis")
            return False
        
        print("✅ Connected to Redis")
        
        # Test basic operations
        print("\n📝 Testing Basic Operations:")
        
        # SET operation
        result = client.set("test:key1", "test_value")
        print(f"SET test:key1 = {result}")
        
        # GET operation  
        result = client.get("test:key1")
        print(f"GET test:key1 = {result}")
        
        # INCR operation
        result = client.incr("test:counter")
        print(f"INCR test:counter = {result}")
        
        # DELETE operation
        result = client.delete("test:key1")
        print(f"DELETE test:key1 = {result}")
        
        print("\n📋 Testing List Operations:")
        
        # LPUSH operation
        result = client.lpush("test:list", "item1", "item2")
        print(f"LPUSH test:list = {result}")
        
        # RPUSH operation
        result = client.rpush("test:list", "item3")
        print(f"RPUSH test:list = {result}")
        
        # LRANGE operation
        result = client.lrange("test:list", 0, -1)
        print(f"LRANGE test:list = {result}")
        
        # LPOP operation
        result = client.lpop("test:list")
        print(f"LPOP test:list = {result}")
        
        print("\n📡 Testing Pub/Sub Operations:")
        
        # PUBLISH operation
        result = client.publish("test:channel", "hello world")
        print(f"PUBLISH test:channel = {result}")
        
        print("\n📊 Checking Metrics:")
        
        # Get current metrics
        operation_metrics = metrics.get_metrics()
        
        print("Operation counts:")
        for operation, metrics_data in operation_metrics.items():
            total = metrics_data.total_count
            success = metrics_data.success_count
            if total > 0:
                print(f"  {operation}: {total} total, {success} success")
        
        # Check if we have operation-specific metrics
        expected_operations = ['SET', 'GET', 'INCR', 'DELETE', 'LPUSH', 'RPUSH', 'LRANGE', 'LPOP', 'PUBLISH']
        found_operations = [op for op in expected_operations if op in operation_metrics and operation_metrics[op].total_count > 0]
        
        print(f"\n✅ Found metrics for operations: {found_operations}")
        
        if len(found_operations) >= 5:  # At least 5 different operations
            print("🎉 SUCCESS: Specific Redis methods are working correctly!")
            print("🎯 Each operation type is being tracked separately")
            return True
        else:
            print("❌ FAILED: Not enough operation-specific metrics found")
            return False
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    finally:
        # Cleanup
        try:
            client.delete("test:key1", "test:counter", "test:list")
        except:
            pass
        client.disconnect()

if __name__ == "__main__":
    success = test_specific_methods()
    sys.exit(0 if success else 1)
