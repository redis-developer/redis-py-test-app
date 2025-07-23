# Redis Test Application - Code Flow Diagram

## Application Startup and Execution Flow

```mermaid
flowchart TD
    A["main.py Entry Point"] --> B["cli.py - Click Interface"]
    B --> C{Command Type}

    C -->|run| D[Load Configuration]
    C -->|test-connection| E[Test Connection Only]
    C -->|list-profiles| F[List Workload Profiles]
    C -->|describe-profile| G[Describe Profile Details]

    D --> H{Config File Provided?}
    H -->|Yes| I["load_config_from_file()"]
    H -->|No| J["_build_config_from_args()"]

    J --> K[Environment Variables + CLI Args + Defaults]
    K --> L[Parse CLI Arguments]
    L --> M[Build RedisConnectionConfig]
    L --> N[Build WorkloadConfig]
    L --> O[Build TestConfig]

    M --> P[Merge into RunnerConfig]
    N --> P
    O --> P
    I --> P

    P --> Q["_validate_config()"]
    Q --> R[Initialize TestRunner]
    R --> S[Setup Logging]
    R --> T[Setup Metrics - OpenTelemetry Only]

    S --> U[Create Logger Instance]
    T --> V[Initialize MetricsCollector]
    V --> W[Setup OpenTelemetry OTLP Exporter]

    R --> X["TestRunner.start()"]

    X --> Y[Create Client Pools]
    Y --> Z[Initialize Redis Connections]
    Z --> AA{Connection Success?}

    AA -->|No| BB[Retry Connection]
    BB --> AA
    AA -->|Yes| CC[Start Worker Threads]

    CC --> DD[Start Stats Reporter Thread]
    CC --> EE[Create Workload Instances per Thread]

    EE --> FF["WorkloadFactory.create_workload()"]
    FF --> GG{Workload Type or Profile}

    GG -->|basic_rw| HH[BasicWorkload]
    GG -->|high_throughput + pipeline| II[PipelineWorkload]
    GG -->|list_operations| JJ[ListWorkload]
    GG -->|transaction_heavy| KK[TransactionWorkload]
    GG -->|pubsub_heavy| LL[PubSubWorkload]
    GG -->|custom operations| MM[BasicWorkload - Default]

    HH --> NN[Execute Operations Loop]
    II --> NN
    JJ --> NN
    KK --> NN
    LL --> NN
    MM --> NN

    NN --> OO[Generate Keys/Values]
    OO --> PP[Execute Redis Command via RedisClientManager]
    PP --> QQ[Record Metrics - OpenTelemetry Only]
    QQ --> RR{Continue?}

    RR -->|Yes| OO
    RR -->|No| SS[Cleanup Resources]

    SS --> TT[Export Final Metrics]
    TT --> UU[Application Exit]

    E --> VV[Create Test Connection]
    VV --> WW[Ping Redis]
    WW --> XX{Connection OK?}
    XX -->|Yes| YY[Success Message]
    XX -->|No| ZZ[Error Message]
    YY --> UU
    ZZ --> UU

    F --> AAA["WorkloadProfiles.list_profiles()"]
    AAA --> UU

    G --> BBB["WorkloadProfiles.get_profile()"]
    BBB --> UU
```

## Thread Architecture and CLI Args Flow

```mermaid
flowchart TD
    A[CLI Arguments] --> B[Configuration Mapping]

    B --> C["--client-instances (clients)"]
    B --> D["--connections-per-client"]
    B --> E["--threads-per-client (threads_per_connection)"]
    B --> F["--workload-profile or custom options"]

    C --> G["TestConfig.clients = N"]
    D --> H["TestConfig.connections_per_client = M"]
    E --> I["TestConfig.threads_per_connection = T"]
    F --> J[WorkloadConfig with profile or custom operations]

    G --> K["TestRunner.start()"]
    H --> K
    I --> K
    J --> K

    K --> L[Create N Client Pools]
    L --> M[Pool 1: M connections]
    L --> N[Pool 2: M connections]
    L --> O[Pool N: M connections]

    K --> P[Start Stats Reporter Thread]
    P --> Q[Collect Metrics Every metrics_interval seconds]
    Q --> R[Display Statistics]
    R --> S{Continue Running?}
    S -->|Yes| Q
    S -->|No| T[Stats Thread Exit]

    K --> U[Start Worker Threads]
    U --> V[Total Threads = N × T]

    M --> W[T Worker Threads for Pool 1]
    N --> X[T Worker Threads for Pool 2]
    O --> Y[T Worker Threads for Pool N]

    W --> Z[Worker Thread 1-1]
    W --> AA[Worker Thread 1-2]
    W --> BB[Worker Thread 1-T]

    X --> CC[Worker Thread 2-1]
    X --> DD[Worker Thread 2-2]
    X --> EE[Worker Thread 2-T]

    Y --> FF[Worker Thread N-1]
    Y --> GG[Worker Thread N-2]
    Y --> HH[Worker Thread N-T]

    Z --> II[Get Client from Pool 1]
    AA --> II
    BB --> II
    CC --> JJ[Get Client from Pool 2]
    DD --> JJ
    EE --> JJ
    FF --> KK[Get Client from Pool N]
    GG --> KK
    HH --> KK

    II --> LL[Create Workload Instance]
    JJ --> LL
    KK --> LL

    LL --> MM[Execute Workload Loop]
    MM --> NN[Generate Operation]
    NN --> OO["Execute Redis Command via RedisClientManager._execute_with_metrics"]
    OO --> PP[Record Metrics to OpenTelemetry]
    PP --> QQ{Rate Limit Check}
    QQ -->|Sleep Needed| RR[Sleep]
    QQ -->|Continue| SS{Duration Check}
    RR --> SS
    SS -->|Continue| NN
    SS -->|Stop| TT[Return Client to Pool]
    TT --> UU[Thread Exit]
```

## Redis Operations Flow

```mermaid
flowchart TD
    A[Worker Thread] --> B[Get Redis Client from Pool]
    B --> C[Create Workload Instance via WorkloadFactory]
    C --> D{Workload Type Determination}

    D -->|basic_rw or default| E[BasicWorkload: SET/GET/DEL/INCR]
    D -->|high_throughput + usePipeline| F[PipelineWorkload: Batch Operations]
    D -->|list_operations or LPUSH/LRANGE/LPOP in operations| G[ListWorkload: List Operations]
    D -->|transaction_heavy or MULTI in operations| H[TransactionWorkload: MULTI/EXEC]
    D -->|pubsub_heavy or PUBLISH/SUBSCRIBE in operations| I[PubSubWorkload: Pub/Sub Operations]

    E --> J[Choose Operation Based on Weights]
    G --> J

    F --> K[Create Pipeline]
    K --> L[Add Multiple Operations to Pipeline]
    L --> M[Execute Pipeline]
    M --> N[Record Individual Operation Metrics]

    H --> O[Create Transaction]
    O --> P[Add Operations to Transaction]
    P --> Q[Execute MULTI/EXEC]
    Q --> R[Record Transaction Metrics]

    I --> S[Setup PubSub Connection]
    S --> T[Start Subscriber Thread]
    T --> U[Publish Messages]
    U --> V[Record PubSub Metrics with Unified Counter]

    J --> W["Generate Key using _generate_key()"]
    W --> X["Generate Value if needed using _generate_value()"]
    X --> Y["Execute Redis Command via RedisClientManager"]

    Y --> Z["RedisClientManager._execute_with_metrics()"]
    Z --> AA[Execute Actual Redis Operation]
    AA --> BB{Command Success?}

    BB -->|Yes| CC[Record Success Metric]
    BB -->|No| DD[Record Error Metric with Error Type]

    CC --> EE[Record Latency in Milliseconds]
    DD --> FF[Record Error Type]
    EE --> GG[Update Internal Counters]
    FF --> GG

    GG --> HH[Send to OpenTelemetry OTLP Endpoint]
    N --> HH
    R --> HH
    V --> HH

    HH --> II{Continue Operations?}
    II -->|Yes| J
    II -->|No| JJ[Cleanup Resources]
    JJ --> KK[Return Client to Pool]
```

## Simplified Metrics Collection Flow (OpenTelemetry Only)

```mermaid
flowchart TD
    A[Operation Executed] --> B["RedisClientManager._execute_with_metrics()"]
    B --> C[Execute Redis Operation]
    C --> D[Measure Duration]
    D --> E["MetricsCollector.record_operation()"]

    E --> F[Update Internal Counters with RLock]
    F --> G[Store Latency Data in Deque]
    G --> H[Update Error Counts by Type]

    H --> I[Update OpenTelemetry Metrics]
    I --> J["otel_operations_counter.add() with Labels"]
    I --> K["otel_operation_duration.record() in Milliseconds"]

    J --> L["Labels: operation, status, app_name, instance_id, run_id, version, error_type"]
    K --> M["Labels: operation, status, app_name, instance_id, run_id, version"]

    L --> N[PeriodicExportingMetricReader]
    M --> N

    N --> O[Export to OTLP Collector Every otel_export_interval_ms]
    O --> P[OpenTelemetry Collector Processes Metrics]

    P --> Q[Collector Exposes Prometheus Endpoint]
    P --> R[Send to Other Backends if Configured]

    Q --> S[Grafana Scrapes Prometheus Endpoint]
    R --> T[Jaeger/Other Observability Tools]

    S --> U[Display in Grafana Dashboard]
    T --> V[Distributed Tracing Analysis]

    %% Special handling for PubSub
    W[PubSub Operation] --> X["MetricsCollector.record_pubsub_operation()"]
    X --> Y["otel_pubsub_operations_counter.add()"]
    Y --> Z["Labels: app_name, instance_id, version, run_id, channel, operation_type, subscriber_id, status"]
    Z --> N

    %% Connection metrics
    AA[Connection Event] --> BB["MetricsCollector.record_connection_attempt()"]
    BB --> CC["otel_connections_counter.add()"]
    CC --> N

    DD[Connection Drop] --> EE["MetricsCollector.record_connection_drop()"]
    EE --> FF["otel_connection_drops_counter.add()"]
    FF --> N

    GG[Reconnection] --> HH["MetricsCollector.record_reconnection()"]
    HH --> II["otel_reconnection_duration.record()"]
    II --> N
```
