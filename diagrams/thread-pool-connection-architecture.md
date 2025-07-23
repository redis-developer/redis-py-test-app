# Thread, Pool, and Connection Architecture

## Architecture Overview

This diagram shows the relationship between threads, client instance pools, Redis client instances, and TCP connection pools.

```mermaid
graph TB
    subgraph "CLI Configuration"
        A1["--client-instances = 2"]
        A2["--connections-per-client = 3"] 
        A3["--threads-per-client = 4"]
        A4["--max-connections = 50"]
    end
    
    subgraph "TestRunner"
        B[TestRunner Main Thread]
    end
    
    A1 --> C1[Create 2 Client Instance Pools]
    A2 --> C2[Each Pool has 3 RedisClientManager instances]
    A3 --> C3[Each Pool spawns 4 Worker Threads]
    A4 --> C4[Each redis.Redis has max_connections=50]
    
    B --> C1
    
    subgraph "Client Instance Pool 1"
        D1[RedisClientManager 1-1]
        D2[RedisClientManager 1-2] 
        D3[RedisClientManager 1-3]
        D4[Available Clients List]
        D5[Thread Lock]
    end
    
    subgraph "Client Instance Pool 2"
        E1[RedisClientManager 2-1]
        E2[RedisClientManager 2-2]
        E3[RedisClientManager 2-3] 
        E4[Available Clients List]
        E5[Thread Lock]
    end
    
    C1 --> D1
    C1 --> D2
    C1 --> D3
    C1 --> E1
    C1 --> E2
    C1 --> E3
    
    subgraph "Worker Threads for Pool 1"
        F1[Worker Thread 1-1]
        F2[Worker Thread 1-2]
        F3[Worker Thread 1-3]
        F4[Worker Thread 1-4]
    end
    
    subgraph "Worker Threads for Pool 2"
        G1[Worker Thread 2-1]
        G2[Worker Thread 2-2]
        G3[Worker Thread 2-3]
        G4[Worker Thread 2-4]
    end
    
    C3 --> F1
    C3 --> F2
    C3 --> F3
    C3 --> F4
    C3 --> G1
    C3 --> G2
    C3 --> G3
    C3 --> G4
    
    %% Thread to Client relationships
    F1 -.->|"get_client()"| D4
    F2 -.->|"get_client()"| D4
    F3 -.->|"get_client()"| D4
    F4 -.->|"get_client()"| D4

    G1 -.->|"get_client()"| E4
    G2 -.->|"get_client()"| E4
    G3 -.->|"get_client()"| E4
    G4 -.->|"get_client()"| E4
    
    D4 -.->|returns| D1
    D4 -.->|returns| D2
    D4 -.->|returns| D3
    
    E4 -.->|returns| E1
    E4 -.->|returns| E2
    E4 -.->|returns| E3
```

## Detailed Connection Architecture

```mermaid
graph TB
    subgraph "Worker Thread Execution"
        A[Worker Thread 1-1]
        B[Worker Thread 1-2]
        C[Worker Thread 1-3]
        D[Worker Thread 1-4]
    end
    
    subgraph "Client Instance Pool 1"
        E[RedisClientPool]
        F[Available Clients List]
        G[Thread Lock]
    end
    
    subgraph "Redis Client Instances"
        H[RedisClientManager 1-1]
        I[RedisClientManager 1-2]
        J[RedisClientManager 1-3]
    end
    
    subgraph "redis-py Client Layer"
        K["redis.Redis Instance 1-1"]
        L["redis.Redis Instance 1-2"]
        M["redis.Redis Instance 1-3"]
    end
    
    subgraph "TCP Connection Pools (redis-py internal)"
        N["TCP Pool 1-1<br/>(max_connections=50)"]
        O["TCP Pool 1-2<br/>(max_connections=50)"]
        P["TCP Pool 1-3<br/>(max_connections=50)"]
    end
    
    subgraph "Redis Server"
        Q[Redis Server Instance]
    end
    
    %% Thread to Pool relationships
    A -->|"1. pool.get_client()"| E
    B -->|"1. pool.get_client()"| E
    C -->|"1. pool.get_client()"| E
    D -->|"1. pool.get_client()"| E

    E -->|"2. with lock, pop from"| F
    F -->|"3. returns"| H
    F -->|"3. returns"| I
    F -->|"3. returns"| J
    
    %% Client Manager to redis.Redis relationships
    H -->|"wraps"| K
    I -->|"wraps"| L
    J -->|"wraps"| M
    
    %% redis.Redis to TCP Pool relationships
    K -->|"uses"| N
    L -->|"uses"| O
    M -->|"uses"| P

    %% TCP connections to Redis
    N -->|"TCP connections"| Q
    O -->|"TCP connections"| Q
    P -->|"TCP connections"| Q

    %% Return path
    A -.->|"4. return_client()"| E
    B -.->|"4. return_client()"| E
    C -.->|"4. return_client()"| E
    D -.->|"4. return_client()"| E
```

## Connection Flow Explanation

### **1. Thread Gets Client Instance**
```python
# Worker thread execution
client = pool.get_client()  # Gets RedisClientManager from pool
```

### **2. Client Instance Pool Management**
```python
class RedisClientPool:
    def get_client(self) -> RedisClientManager:
        with self._lock:  # Thread-safe access
            if self._available_clients:
                return self._available_clients.pop()  # Return available client
```

### **3. RedisClientManager Wraps redis.Redis**
```python
class RedisClientManager:
    def __init__(self, config):
        # Creates redis.Redis with internal connection pool
        self._client = redis.Redis(
            host=config.host,
            port=config.port,
            max_connections=50,  # TCP connection pool size
            **pool_kwargs
        )
```

### **4. Operation Execution**
```python
# Thread executes Redis operation
result = client.set("key", "value")  # Uses redis-py's TCP connection pool
```

### **5. Client Return**
```python
# Thread returns client to pool for reuse
pool.return_client(client)
```

## Key Relationships

| Component | What It Actually Is | Contains |
|-----------|-------------------|----------|
| `RedisClientPool` | Client Instance Pool | Multiple `RedisClientManager` instances |
| `RedisClientManager` | Redis Client Instance | One `redis.Redis` instance + metrics/retry logic |
| `redis.Redis` | redis-py Client | Internal TCP connection pool |
| TCP Connection Pool | Actual network connections | TCP sockets to Redis server |

## Configuration Impact

- **`--client-instances`**: Number of `RedisClientPool` instances
- **`--connections-per-client`**: Number of `RedisClientManager` per pool
- **`--threads-per-client`**: Number of worker threads per pool
- **`--max-connections`**: TCP connections per `redis.Redis` instance

## Total Connections Calculation

```
Total TCP Connections =
  client_instances × connections_per_client × max_connections

Example: 2 × 3 × 50 = 300 total TCP connections to Redis
```

## Terminology Alignment Diagram

```mermaid
graph TB
    subgraph "Your Terminology"
        A1["Redis Client Instance"]
        A2["SDK Connection Pool"]
        A3["TCP Connections"]
    end

    subgraph "Our Implementation"
        B1["RedisClientManager"]
        B2["redis.Redis internal pool"]
        B3["TCP sockets"]
    end

    subgraph "Our Confusing Names"
        C1["RedisClientPool"]
        C2["connections_per_client"]
    end

    subgraph "Better Names Would Be"
        D1["ClientInstancePool"]
        D2["client_instances_per_pool"]
    end

    A1 -.->|"maps to"| B1
    A2 -.->|"maps to"| B2
    A3 -.->|"maps to"| B3

    C1 -.->|"should be called"| D1
    C2 -.->|"should be called"| D2

    style A1 fill:#e1f5fe
    style A2 fill:#e1f5fe
    style A3 fill:#e1f5fe
    style B1 fill:#f3e5f5
    style B2 fill:#f3e5f5
    style B3 fill:#f3e5f5
```
