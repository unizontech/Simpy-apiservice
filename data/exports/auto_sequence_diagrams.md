# Request Flow Sequence Diagrams

Auto-generated from execution traces.

## Simple Read Pattern

```mermaid
sequenceDiagram
    title Simple Read Request Flow

    participant Nginx
    participant APP1
    participant Service
    participant APP2

    participant Client

    Client->>+Nginx: Request (simple_read)
    Note over Nginx: Process 10ms
    Nginx->>+APP1: Process
    Note over APP1: Process 54ms
    APP1->>+Service: Process
    Note over Service: Process 80ms
    Service->>+APP2: Process
    Note over APP2: Process 35ms
    APP2-->>-Service: Response
    Service-->>-APP1: Response
    APP1-->>-Nginx: Response
    Nginx-->>-Client: Response (179ms total)
```

## User Auth Pattern

```mermaid
sequenceDiagram
    title User Auth Request Flow

    participant Nginx
    participant APP1
    participant Auth
    participant Policy
    participant Service
    participant APP2

    participant Client

    Client->>+Nginx: Request (user_auth)
    Note over Nginx: Process 8ms
    Nginx->>+APP1: Process
    Note over APP1: Process 45ms
    APP1->>+Auth: Process
    Note over Auth: Process 54ms
    Auth->>+Policy: Process
    Note over Policy: Process 48ms
    Policy->>+Service: Process
    Note over Service: Process 43ms
    Service->>+APP2: Process
    Note over APP2: Process 33ms
    APP2-->>-Service: Response
    Service-->>-Policy: Response
    Policy-->>-Auth: Response
    Auth-->>-APP1: Response
    APP1-->>-Nginx: Response
    Nginx-->>-Client: Response (232ms total)
```

## Data Processing Pattern

```mermaid
sequenceDiagram
    title Data Processing Request Flow

    participant Nginx
    participant APP1
    participant Service
    participant DB
    participant ServiceHub
    participant APP2

    participant Client

    Client->>+Nginx: Request (data_processing)
    Note over Nginx: Process 10ms
    Nginx->>+APP1: Process
    Note over APP1: Process 51ms
    APP1->>+Service: Process
    Note over Service: Process 96ms
    Service->>+DB: Process
    Note over DB: Process 225ms
    DB->>+ServiceHub: Process
    Note over ServiceHub: Process 66ms
    ServiceHub->>+APP2: Process
    Note over APP2: Process 64ms
    APP2-->>-ServiceHub: Response
    ServiceHub-->>-DB: Response
    DB-->>-Service: Response
    Service-->>-APP1: Response
    APP1-->>-Nginx: Response
    Nginx-->>-Client: Response (511ms total)
```

## File Upload Pattern

```mermaid
sequenceDiagram
    title File Upload Request Flow

    participant Nginx
    participant APP1
    participant Auth
    participant Service
    participant S3
    participant Logger
    participant APP2

    participant Client

    Client->>+Nginx: Request (file_upload)
    Note over Nginx: Process 17ms
    Nginx->>+APP1: Process
    Note over APP1: Process 89ms
    APP1->>+Auth: Process
    Note over Auth: Process 40ms
    Auth->>+Service: Process
    Note over Service: Process 132ms
    Service->>+S3: Process
    Note over S3: Process 31ms
    S3->>+Logger: Process
    Note over Logger: Process 27ms
    Logger->>+APP2: Process
    Note over APP2: Process 47ms
    APP2-->>-Logger: Response
    Logger-->>-S3: Response
    S3-->>-Service: Response
    Service-->>-Auth: Response
    Auth-->>-APP1: Response
    APP1-->>-Nginx: Response
    Nginx-->>-Client: Response (383ms total)
```

## Analytics Pattern

```mermaid
sequenceDiagram
    title Analytics Request Flow

    participant Nginx
    participant APP1
    participant Service
    participant DB
    participant ServiceHub
    participant APP2
    participant Logger

    participant Client

    Client->>+Nginx: Request (analytics)
    Note over Nginx: Process 12ms
    Nginx->>+APP1: Process
    Note over APP1: Process 114ms
    APP1->>+Service: Process
    Note over Service: Process 300ms
    Service->>+DB: Process
    Note over DB: Process 440ms
    DB->>+ServiceHub: Process
    Note over ServiceHub: Process 178ms
    ServiceHub->>+APP2: Process
    Note over APP2: Process 81ms
    APP2->>+Logger: Process
    Note over Logger: Process 25ms
    Logger-->>-APP2: Response
    APP2-->>-ServiceHub: Response
    ServiceHub-->>-DB: Response
    DB-->>-Service: Response
    Service-->>-APP1: Response
    APP1-->>-Nginx: Response
    Nginx-->>-Client: Response (1148ms total)
```

## Admin Task Pattern

```mermaid
sequenceDiagram
    title Admin Task Request Flow

    participant Nginx
    participant APP1
    participant Auth
    participant Policy
    participant Service
    participant DB
    participant ServiceHub
    participant S3
    participant Logger
    participant APP2

    participant Client

    Client->>+Nginx: Request (admin_task)
    Note over Nginx: Process 18ms
    Nginx->>+APP1: Process
    Note over APP1: Process 147ms
    APP1->>+Auth: Process
    Note over Auth: Process 64ms
    Auth->>+Policy: Process
    Note over Policy: Process 106ms
    Policy->>+Service: Process
    Note over Service: Process 207ms
    Service->>+DB: Process
    Note over DB: Process 273ms
    DB->>+ServiceHub: Process
    Note over ServiceHub: Process 183ms
    ServiceHub->>+S3: Process
    Note over S3: Process 56ms
    S3->>+Logger: Process
    Note over Logger: Process 47ms
    Logger->>+APP2: Process
    Note over APP2: Process 99ms
    APP2-->>-Logger: Response
    Logger-->>-S3: Response
    S3-->>-ServiceHub: Response
    ServiceHub-->>-DB: Response
    DB-->>-Service: Response
    Service-->>-Policy: Response
    Policy-->>-Auth: Response
    Auth-->>-APP1: Response
    APP1-->>-Nginx: Response
    Nginx-->>-Client: Response (1198ms total)
```

## Parallel Processing Examples

### User Auth Parallel Flow

```mermaid
sequenceDiagram
    title User Auth - Parallel Processing

    participant APP1
    participant APP2
    participant Auth
    participant Nginx
    participant Policy
    participant Service

    participant Client

    Client->>+Nginx: Request
    par Parallel Processing
        Processing on Nginx
        and Processing on APP1
    end
    Note over Auth: Sequential Processing
    Note over Policy: Sequential Processing
    Note over Service: Sequential Processing
    Note over APP2: Sequential Processing
    Nginx-->>-Client: Response
```

### Analytics Parallel Flow

```mermaid
sequenceDiagram
    title Analytics - Parallel Processing

    participant APP1
    participant APP2
    participant DB
    participant Logger
    participant Nginx
    participant Service
    participant ServiceHub

    participant Client

    Client->>+Nginx: Request
    Note over Nginx: Sequential Processing
    Note over APP1: Sequential Processing
    Note over Service: Sequential Processing
    Note over DB: Sequential Processing
    Note over ServiceHub: Sequential Processing
    Note over APP2: Sequential Processing
    Note over Logger: Sequential Processing
    Nginx-->>-Client: Response
```

### File Upload Parallel Flow

```mermaid
sequenceDiagram
    title File Upload - Parallel Processing

    participant APP1
    participant APP2
    participant Auth
    participant Logger
    participant Nginx
    participant S3
    participant Service

    participant Client

    Client->>+Nginx: Request
    Note over Nginx: Sequential Processing
    Note over APP1: Sequential Processing
    Note over Auth: Sequential Processing
    Note over Service: Sequential Processing
    Note over S3: Sequential Processing
    Note over Logger: Sequential Processing
    Note over APP2: Sequential Processing
    Nginx-->>-Client: Response
```

## Pattern Comparison

```mermaid
graph TD
    title Request Pattern Comparison

    Start0[simple_read]
    simple_read_0[Nginx]
    Start0 --> simple_read_0
    simple_read_1[APP1]
    simple_read_0 --> simple_read_1
    simple_read_2[Service]
    simple_read_1 --> simple_read_2
    simple_read_3[APP2]
    simple_read_2 --> simple_read_3
    End0[Response]
    simple_read_3 --> End0

    Start1[user_auth]
    user_auth_0[Nginx]
    Start1 --> user_auth_0
    user_auth_1[APP1]
    user_auth_0 --> user_auth_1
    user_auth_2[Auth]
    user_auth_1 --> user_auth_2
    user_auth_3[Policy]
    user_auth_2 --> user_auth_3
    user_auth_4[Service]
    user_auth_3 --> user_auth_4
    user_auth_5[APP2]
    user_auth_4 --> user_auth_5
    End1[Response]
    user_auth_5 --> End1

    Start2[data_processing]
    data_processing_0[Nginx]
    Start2 --> data_processing_0
    data_processing_1[APP1]
    data_processing_0 --> data_processing_1
    data_processing_2[Service]
    data_processing_1 --> data_processing_2
    data_processing_3[DB]
    data_processing_2 --> data_processing_3
    data_processing_4[ServiceHub]
    data_processing_3 --> data_processing_4
    data_processing_5[APP2]
    data_processing_4 --> data_processing_5
    End2[Response]
    data_processing_5 --> End2

    Start3[file_upload]
    file_upload_0[Nginx]
    Start3 --> file_upload_0
    file_upload_1[APP1]
    file_upload_0 --> file_upload_1
    file_upload_2[Auth]
    file_upload_1 --> file_upload_2
    file_upload_3[Service]
    file_upload_2 --> file_upload_3
    file_upload_4[S3]
    file_upload_3 --> file_upload_4
    file_upload_5[Logger]
    file_upload_4 --> file_upload_5
    file_upload_6[APP2]
    file_upload_5 --> file_upload_6
    End3[Response]
    file_upload_6 --> End3

    Start4[analytics]
    analytics_0[Nginx]
    Start4 --> analytics_0
    analytics_1[APP1]
    analytics_0 --> analytics_1
    analytics_2[Service]
    analytics_1 --> analytics_2
    analytics_3[DB]
    analytics_2 --> analytics_3
    analytics_4[ServiceHub]
    analytics_3 --> analytics_4
    analytics_5[APP2]
    analytics_4 --> analytics_5
    analytics_6[Logger]
    analytics_5 --> analytics_6
    End4[Response]
    analytics_6 --> End4

    Start5[admin_task]
    admin_task_0[Nginx]
    Start5 --> admin_task_0
    admin_task_1[APP1]
    admin_task_0 --> admin_task_1
    admin_task_2[Auth]
    admin_task_1 --> admin_task_2
    admin_task_3[Policy]
    admin_task_2 --> admin_task_3
    admin_task_4[Service]
    admin_task_3 --> admin_task_4
    admin_task_5[DB]
    admin_task_4 --> admin_task_5
    admin_task_6[ServiceHub]
    admin_task_5 --> admin_task_6
    admin_task_7[S3]
    admin_task_6 --> admin_task_7
    admin_task_8[Logger]
    admin_task_7 --> admin_task_8
    admin_task_9[APP2]
    admin_task_8 --> admin_task_9
    End5[Response]
    admin_task_9 --> End5

```

## Bottleneck Analysis

```mermaid
graph TD
    title System Bottlenecks Analysis

    Nginx[Nginx<br/>12.7ms]
    style Nginx fill:#99ff99
    APP1[APP1<br/>81.3ms]
    style APP1 fill:#99ff99
    Service[Service<br/>149.8ms]
    style Service fill:#ffcc99
    APP2[APP2<br/>58.2ms]
    style APP2 fill:#99ff99
    Auth[Auth<br/>55.0ms]
    style Auth fill:#99ff99
    Policy[Policy<br/>81.4ms]
    style Policy fill:#99ff99
    DB[DB<br/>304.7ms]
    style DB fill:#ff9999
    ServiceHub[ServiceHub<br/>146.0ms]
    style ServiceHub fill:#ffcc99
    S3[S3<br/>40.4ms]
    style S3 fill:#99ff99
    Logger[Logger<br/>30.9ms]
    style Logger fill:#99ff99

    classDef bottleneck fill:#ff9999,stroke:#ff0000
```
