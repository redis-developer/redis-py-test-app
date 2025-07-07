# Redis Test Application - System Architecture Diagram

## Overall System Architecture

```mermaid
graph TB
    subgraph "Redis Test Application"
        subgraph "CLI Layer"
            A[main.py] --> B[cli.py]
            B --> C[Click Commands]
        end
        
        subgraph "Configuration Layer"
            D[config.py] --> E[RunnerConfig]
            E --> F[RedisConnectionConfig]
            E --> G[TestConfig]
            E --> H[WorkloadConfig]
            I[.env File] --> D
            J[Environment Variables] --> D
            K[CLI Arguments] --> D
        end
        
        subgraph "Core Engine"
            L[TestRunner] --> M[Thread Management]
            L --> N[Client Pool Management]
            L --> O[Statistics Reporting]
        end
        
        subgraph "Redis Connectivity"
            P[RedisClientManager] --> Q[Connection Handling]
            P --> R[Retry Logic]
            P --> S[Health Monitoring]
            T[RedisClientPool] --> P
            N --> T
        end
        
        subgraph "Workload Engine"
            U[WorkloadFactory] --> V[BaseWorkload]
            V --> W[BasicWorkload]
            V --> X[HighThroughputWorkload]
            V --> Y[ListOperationsWorkload]
            V --> Z[SetOperationsWorkload]
            V --> AA[SortedSetOperationsWorkload]
            V --> BB[HashOperationsWorkload]
            V --> CC[PipelineWorkload]
            V --> DD[PubSubWorkload]
        end
        
        subgraph "Observability Layer"
            EE[MetricsCollector] --> FF[OpenTelemetry]
            EE --> GG[Prometheus]
            HH[RedisTestLogger] --> II[File Logging]
            HH --> JJ[Console Logging]
        end
    end
    
    subgraph "External Systems"
        subgraph "Redis Infrastructure"
            KK[Redis Standalone]
            LL[Redis Cluster]
            MM[Redis Sentinel]
        end
        
        subgraph "Observability Stack"
            NN[OpenTelemetry Collector]
            OO[Prometheus Server]
            PP[Grafana Dashboard]
            QQ[Jaeger Tracing]
        end
    end
    
    %% Connections
    C --> L
    D --> L
    L --> U
    P --> KK
    P --> LL
    P --> MM
    FF --> NN
    GG --> OO
    NN --> PP
    NN --> QQ
    OO --> PP
    EE --> NN
    W --> P
    X --> P
    Y --> P
    Z --> P
    AA --> P
    BB --> P
    CC --> P
    DD --> P
```

## Component Interaction Architecture

```mermaid
graph TD
    subgraph "Application Startup"
        A[main.py] --> B[CLI Parsing]
        B --> C[Configuration Loading]
        C --> D[Validation]
        D --> E[TestRunner Creation]
    end
    
    subgraph "Runtime Architecture"
        E --> F[Logger Setup]
        E --> G[Metrics Setup]
        E --> H[Client Pool Creation]
        
        H --> I[Redis Connection Pool 1]
        H --> J[Redis Connection Pool 2]
        H --> K[Redis Connection Pool N]
        
        I --> L[RedisClientManager 1-1]
        I --> M[RedisClientManager 1-2]
        I --> N[RedisClientManager 1-N]
        
        J --> O[RedisClientManager 2-1]
        J --> P[RedisClientManager 2-2]
        J --> Q[RedisClientManager 2-N]
        
        K --> R[RedisClientManager N-1]
        K --> S[RedisClientManager N-2]
        K --> T[RedisClientManager N-N]
    end
    
    subgraph "Worker Thread Architecture"
        E --> U[Worker Thread Pool]
        U --> V[Worker Thread 1]
        U --> W[Worker Thread 2]
        U --> X[Worker Thread N]
        
        V --> Y[Get Client from Pool]
        W --> Y
        X --> Y
        
        Y --> Z[Create Workload Instance]
        Z --> AA[Execute Operations Loop]
        AA --> BB[Record Metrics]
        BB --> CC[Return Client to Pool]
    end
    
    subgraph "Metrics Flow"
        BB --> DD[MetricsCollector]
        DD --> EE[OpenTelemetry Export]
        DD --> FF[Prometheus Export]
        
        EE --> GG[OTLP Collector]
        FF --> HH[Prometheus Server]
        
        GG --> II[Grafana Visualization]
        HH --> II
        GG --> JJ[Jaeger Tracing]
    end
    
    subgraph "Redis Operations"
        L --> KK[Redis Instance/Cluster]
        M --> KK
        N --> KK
        O --> KK
        P --> KK
        Q --> KK
        R --> KK
        S --> KK
        T --> KK
    end
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Environment"
        subgraph "Application Containers"
            A[redis-test-basic-rw]
            B[redis-test-high-throughput]
            C[redis-test-list-operations]
            D[redis-test-set-operations]
            E[redis-test-hash-operations]
            F[redis-test-pipeline]
            G[redis-test-pubsub]
        end

        subgraph "Redis Infrastructure"
            H[Redis Standalone Container]
            I[Redis Cluster Node 1]
            J[Redis Cluster Node 2]
            K[Redis Cluster Node 3]
        end

        subgraph "Observability Stack"
            L[OpenTelemetry Collector]
            M[Prometheus Server]
            N[Grafana Dashboard]
            O[Jaeger Tracing]
        end

        subgraph "Shared Resources"
            P[Docker Network: redis-test-network]
            Q[Shared Volumes: ./logs]
            R[Environment Files: .env.docker]
        end
    end

    %% Application to Redis connections
    A --> H
    B --> H
    C --> H
    D --> H
    E --> H
    F --> H
    G --> H

    A --> I
    B --> I
    C --> I

    %% Metrics flow
    A --> L
    B --> L
    C --> L
    D --> L
    E --> L
    F --> L
    G --> L

    L --> M
    L --> O
    M --> N

    %% Network and volume connections
    A -.-> P
    B -.-> P
    C -.-> P
    D -.-> P
    E -.-> P
    F -.-> P
    G -.-> P
    H -.-> P
    I -.-> P
    J -.-> P
    K -.-> P
    L -.-> P
    M -.-> P
    N -.-> P
    O -.-> P

    A -.-> Q
    B -.-> Q
    C -.-> Q
    D -.-> Q
    E -.-> Q
    F -.-> Q
    G -.-> Q

    A -.-> R
    B -.-> R
    C -.-> R
    D -.-> R
    E -.-> R
    F -.-> R
    G -.-> R
```

## Error Handling and Resilience Architecture

```mermaid
graph TD
    A[Redis Operation] --> B{Connection Available?}

    B -->|No| C[Connection Pool Exhausted]
    B -->|Yes| D[Execute Command]

    C --> E[Wait for Available Connection]
    E --> F{Timeout Reached?}
    F -->|Yes| G[Operation Failed]
    F -->|No| B

    D --> H{Command Success?}
    H -->|Yes| I[Record Success Metrics]
    H -->|No| J[Analyze Error Type]

    J --> K{Connection Error?}
    K -->|Yes| L[Trigger Reconnection]
    K -->|No| M[Record Application Error]

    L --> N[Exponential Backoff]
    N --> O[Reconnection Attempt]
    O --> P{Reconnection Success?}

    P -->|Yes| Q[Reset Backoff]
    P -->|No| R[Increase Backoff]

    Q --> S[Update Connection Metrics]
    R --> T{Max Retries Reached?}

    T -->|Yes| U[Mark Connection Failed]
    T -->|No| N

    S --> V[Resume Operations]
    U --> W[Remove from Pool]
    M --> X[Log Error Details]
    G --> X

    I --> Y[Continue Operations]
    X --> Z[Error Metrics Recording]
    V --> Y
    W --> AA[Pool Rebalancing]

    Z --> BB[Alert Generation]
    AA --> CC[Create New Connection]
    CC --> DD[Add to Pool]
```
