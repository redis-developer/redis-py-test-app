# Redis Test Application - Code Flow Diagram

## Application Startup and Execution Flow

```mermaid
flowchart TD
    A[main.py Entry Point] --> B[CLI Interface]
    B --> C{Command Type}
    
    C -->|run| D[Load Configuration]
    C -->|test-connection| E[Test Connection Only]
    
    D --> F[Environment Variables]
    D --> G[CLI Arguments]
    D --> H[Default Values]
    
    F --> I[Merge Configuration]
    G --> I
    H --> I
    
    I --> J[Validate Configuration]
    J --> K[Create RunnerConfig]
    
    K --> L[Initialize TestRunner]
    L --> M[Setup Logging]
    L --> N[Setup Metrics]
    
    M --> O[Create Logger Instance]
    N --> P[Initialize MetricsCollector]
    P --> Q[Setup OpenTelemetry]
    P --> R[Setup Prometheus]
    
    L --> S[TestRunner.run()]
    
    S --> T[Create Client Pools]
    T --> U[Initialize Redis Connections]
    U --> V{Connection Success?}
    
    V -->|No| W[Retry Connection]
    W --> V
    V -->|Yes| X[Start Worker Threads]
    
    X --> Y[Start Stats Reporter]
    X --> Z[Create Workload Instances]
    
    Z --> AA[WorkloadFactory.create_workload()]
    AA --> BB{Workload Type}
    
    BB -->|basic_rw| CC[BasicWorkload]
    BB -->|high_throughput| DD[HighThroughputWorkload]
    BB -->|list_operations| EE[ListOperationsWorkload]
    BB -->|set_operations| FF[SetOperationsWorkload]
    BB -->|sorted_set_operations| GG[SortedSetOperationsWorkload]
    BB -->|hash_operations| HH[HashOperationsWorkload]
    BB -->|pipeline| II[PipelineWorkload]
    BB -->|pub_sub| JJ[PubSubWorkload]
    
    CC --> KK[Execute Operations Loop]
    DD --> KK
    EE --> KK
    FF --> KK
    GG --> KK
    HH --> KK
    II --> KK
    JJ --> KK
    
    KK --> LL[Generate Keys/Values]
    LL --> MM[Execute Redis Command]
    MM --> NN[Record Metrics]
    NN --> OO{Continue?}
    
    OO -->|Yes| LL
    OO -->|No| PP[Cleanup Resources]
    
    PP --> QQ[Export Metrics]
    QQ --> RR[Application Exit]
    
    E --> SS[Create Test Connection]
    SS --> TT[Ping Redis]
    TT --> UU{Connection OK?}
    UU -->|Yes| VV[Success Message]
    UU -->|No| WW[Error Message]
    VV --> RR
    WW --> RR
```

## Thread Architecture Flow

```mermaid
flowchart TD
    A[TestRunner Main Thread] --> B[Create Client Pools]
    B --> C[Pool 1: connections_per_client connections]
    B --> D[Pool 2: connections_per_client connections]
    B --> E[Pool N: client_instances pools]
    
    A --> F[Start Stats Reporter Thread]
    F --> G[Collect Metrics Every 5s]
    G --> H[Display Statistics]
    H --> I{Continue Running?}
    I -->|Yes| G
    I -->|No| J[Stats Thread Exit]
    
    A --> K[Start Worker Threads]
    
    C --> L[Worker Thread 1-1]
    C --> M[Worker Thread 1-2]
    C --> N[Worker Thread 1-N]
    
    D --> O[Worker Thread 2-1]
    D --> P[Worker Thread 2-2]
    D --> Q[Worker Thread 2-N]
    
    E --> R[Worker Thread N-1]
    E --> S[Worker Thread N-2]
    E --> T[Worker Thread N-N]
    
    L --> U[Get Client from Pool]
    M --> U
    N --> U
    O --> U
    P --> U
    Q --> U
    R --> U
    S --> U
    T --> U
    
    U --> V[Create Workload Instance]
    V --> W[Execute Workload Loop]
    W --> X[Generate Operation]
    X --> Y[Execute Redis Command]
    Y --> Z[Record Metrics]
    Z --> AA{Rate Limit Check}
    AA -->|Sleep Needed| BB[Sleep]
    AA -->|Continue| CC{Duration Check}
    BB --> CC
    CC -->|Continue| X
    CC -->|Stop| DD[Return Client to Pool]
    DD --> EE[Thread Exit]
```

## Redis Operations Flow

```mermaid
flowchart TD
    A[Worker Thread] --> B[Get Redis Client]
    B --> C[Create Workload Instance]
    C --> D{Workload Type}

    D -->|BasicWorkload| E[Choose Operation: SET/GET/DEL/INCR]
    D -->|HighThroughputWorkload| F[Optimized Operations]
    D -->|ListOperationsWorkload| G[LPUSH/RPOP/LLEN Operations]
    D -->|SetOperationsWorkload| H[SADD/SREM/SCARD Operations]
    D -->|SortedSetOperationsWorkload| I[ZADD/ZREM/ZCARD Operations]
    D -->|HashOperationsWorkload| J[HSET/HGET/HDEL Operations]
    D -->|PipelineWorkload| K[Batch Operations in Pipeline]
    D -->|PubSubWorkload| L[PUBLISH/SUBSCRIBE Operations]

    E --> M[Generate Key]
    F --> M
    G --> M
    H --> M
    I --> M
    J --> M

    K --> N[Create Pipeline]
    N --> O[Add Multiple Operations]
    O --> P[Execute Pipeline]
    P --> Q[Record Batch Metrics]

    L --> R[Setup PubSub]
    R --> S[Start Subscriber Thread]
    S --> T[Publish Messages]
    T --> U[Record PubSub Metrics]

    M --> V[Generate Value if needed]
    V --> W[Execute Redis Command]
    W --> X{Command Success?}

    X -->|Yes| Y[Record Success Metric]
    X -->|No| Z[Record Error Metric]

    Y --> AA[Record Latency]
    Z --> BB[Record Error Type]
    AA --> CC[Update Counters]
    BB --> CC

    CC --> DD[Send to OpenTelemetry]
    CC --> EE[Update Prometheus Metrics]

    DD --> FF{Continue Operations?}
    EE --> FF
    Q --> FF
    U --> FF

    FF -->|Yes| M
    FF -->|No| GG[Cleanup Resources]
    GG --> HH[Return Client to Pool]
```

## Metrics Collection Flow

```mermaid
flowchart TD
    A[Operation Executed] --> B[MetricsCollector.record_operation()]
    B --> C[Update Internal Counters]
    C --> D[Store Latency Data]
    D --> E[Update Error Counts]

    E --> F{OpenTelemetry Enabled?}
    F -->|Yes| G[Update OTEL Counters]
    F -->|No| H[Skip OTEL]

    G --> I[otel_operations_counter.add()]
    G --> J[otel_operation_duration.record()]

    I --> K{Prometheus Enabled?}
    J --> K
    H --> K

    K -->|Yes| L[Update Prometheus Metrics]
    K -->|No| M[Skip Prometheus]

    L --> N[prom_operations_total.inc()]
    L --> O[prom_operation_duration.observe()]

    N --> P[Export to OTLP Collector]
    O --> P
    M --> P

    P --> Q[Collector Processes Metrics]
    Q --> R[Expose Prometheus Endpoint]
    Q --> S[Send to Jaeger/Other Backends]

    R --> T[Grafana Scrapes Metrics]
    S --> U[Distributed Tracing]

    T --> V[Display in Dashboard]
    U --> W[Trace Analysis]
```
