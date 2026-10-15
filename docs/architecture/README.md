# Blue Bayelsa Invest: architecture diagrams

Standard notations: C4 model (context, containers) and UML (use case, component, deployment, sequence, state machine, activity), plus an entity-relationship diagram. Sources are Mermaid (`*.mmd`) and render directly on GitHub. Regenerate with `python docs/architecture/diagrams.py`.

## 1. System context (C4 level 1)

*C4 model: system context.* Who uses the platform and which outside systems it depends on. The blue box is the system we are building; grey boxes are external.

```mermaid
flowchart TB
    inv["Investor<br/><i>finds and compares opportunities</i>"]:::person
    gov["Government agency<br/><i>monitors sectors and gaps</i>"]:::person
    res["Researcher<br/><i>downloads datasets</i>"]:::person
    ent["Enterprise<br/><i>is listed in the directory</i>"]:::person
    pub["Public visitor<br/><i>explores communities and map</i>"]:::person
    staff["Project staff<br/><i>data entry, reviewers, administrators</i>"]:::person

    sys["Blue Bayelsa Invest<br/>Web and Android platform for blue-economy<br/>data, enterprises and investment opportunities"]:::system

    kobo["KoboToolbox<br/>Field survey collection"]:::ext
    osm["OpenStreetMap<br/>Basemap data for Bayelsa"]:::ext
    le["Let's Encrypt<br/>Free HTTPS certificates"]:::ext
    bk["Off-site backup storage"]:::ext
    play["Google Play Store<br/>Android distribution"]:::ext

    inv & gov & res & ent & pub -- "browse, search, download<br/>(HTTPS)" --> sys
    staff -- "enter, upload, review, approve<br/>(HTTPS, login)" --> sys
    kobo -. "survey exports (Excel)<br/>uploaded by staff" .-> sys
    osm -. "one-off basemap extract" .-> sys
    le -. "certificates" .-> sys
    sys -- "nightly encrypted backup" --> bk
    play -. "installs Android app" .-> pub

    classDef person fill:#0b4f6c,stroke:#063247,color:#ffffff
    classDef system fill:#1f7a9c,stroke:#0b4f6c,color:#ffffff,font-weight:bold
    classDef ext fill:#e3e8ec,stroke:#8a99a6,color:#1d2a33
```

## 2. Containers (C4 level 2)

*C4 model: container diagram.* The deployable parts. Everything server-side runs on one affordable cloud server. The web app and Android app share one codebase and one API.

```mermaid
flowchart LR
    subgraph clients["Clients"]
        web["Web application<br/><b>React + TypeScript</b><br/>public site and admin portal"]:::built_planned
        apk["Android application<br/><b>Capacitor</b> (same React code)<br/>offline cache of viewed data"]:::planned
    end

    subgraph server["Single cloud server (Docker Compose)"]
        nginx["Web server<br/><b>Nginx</b><br/>HTTPS, compression, static files"]:::built
        api["API application<br/><b>Django + Django REST Framework</b><br/>business rules, permissions, scoring"]:::built
        db[("Database<br/><b>PostgreSQL + PostGIS</b><br/>records, locations, audit log")]:::built
        files[("Private file store<br/>uploaded Excel/CSV, photos")]:::built
        tiles[("Basemap file<br/><b>PMTiles</b> extract of Bayelsa")]:::planned
    end

    web -- "JSON over HTTPS<br/>/api/v1/public, /api/v1/admin" --> nginx
    apk -- "JSON over HTTPS<br/>/api/v1/public" --> nginx
    web & apk -- "map tiles" --> nginx
    nginx -- "proxy /api" --> api
    nginx -. "serves" .-> tiles
    api -- "SQL / spatial queries" --> db
    api -- "read / write" --> files

    classDef built fill:#1f7a9c,stroke:#0b4f6c,color:#ffffff
    classDef built_planned fill:#1f7a9c,stroke:#0b4f6c,color:#ffffff,stroke-dasharray:5 3
    classDef planned fill:#ffffff,stroke:#1f7a9c,color:#0b4f6c,stroke-dasharray:5 3
```

## 3. Use cases

*UML use case diagram.* What each role can do. Each role includes everything the role above it can do. Public browsing needs no account.

```mermaid
flowchart LR
    visitor(["Public visitor"]):::actor
    reg(["Registered user<br/>investor, government,<br/>researcher, partner"]):::actor
    dataentry(["Data entry officer"]):::actor
    reviewer(["Reviewer"]):::actor
    admin(["Administrator"]):::actor

    subgraph system["Blue Bayelsa Invest"]
        uc1(["Explore communities and map"])
        uc2(["Search enterprise directory"])
        uc3(["View opportunities and scores"])
        uc4(["View dashboard"])
        uc5(["Download filtered data"])
        uc6(["Send enquiry or partnership request"])
        uc7(["Enter records manually"])
        uc8(["Upload Excel / CSV"])
        uc9(["Correct rows and submit"])
        uc10(["Approve, return or reject records"])
        uc11(["Configure scoring criteria and weights"])
        uc12(["Manage indicators"])
        uc13(["Manage users and roles"])
        uc14(["Manage reference data"])
        uc15(["View audit log"])
        uc16(["Archive records"])
    end

    visitor --- uc1 & uc2 & uc3 & uc4
    reg --- uc5 & uc6
    reg -. "inherits" .-> visitor
    dataentry --- uc7 & uc8 & uc9
    reviewer --- uc10 & uc11 & uc12
    reviewer -. "inherits" .-> dataentry
    admin --- uc13 & uc14 & uc15 & uc16
    admin -. "inherits" .-> reviewer

    classDef actor fill:#0b4f6c,stroke:#063247,color:#ffffff
```

## 4. Backend components

*UML component diagram.* Modules inside the API application. Solid boxes are built and tested; dashed boxes are planned and depend on the field questionnaire.

```mermaid
flowchart TB
    subgraph api["Django API application"]
        direction TB
        router["API router<br/>public / admin / auth"]:::built

        subgraph core["Core services (built)"]
            accounts["accounts<br/>users, roles, capabilities"]:::built
            governance["governance<br/>workflow, data sources, GPS checks"]:::built
            audit["audit<br/>append-only log"]:::built
            geo["geo<br/>LGAs, communities, sectors, activities"]:::built
            imports["imports<br/>templates, file checks, row validation"]:::built
        end

        subgraph domain["Domain modules (Phase 3 to 8)"]
            enterprises["enterprises<br/>profiles, directory"]:::planned
            indicators["indicators<br/>definitions, values"]:::planned
            infra["infrastructure<br/>jetties, cold rooms, markets"]:::planned
            opps["opportunities<br/>+ scoring engine"]:::planned
            dash["dashboard<br/>statistics"]:::planned
            reports["reports<br/>CSV / Excel export"]:::planned
        end
    end

    router --> accounts & geo & imports
    imports --> governance & geo
    governance --> accounts & audit
    domain -. "all inherit the publication workflow" .-> governance
    imports -. "one importer per record type" .-> domain
    opps -. "scores from" .-> indicators
    dash -. "reads published records" .-> opps

    classDef built fill:#1f7a9c,stroke:#0b4f6c,color:#ffffff
    classDef planned fill:#ffffff,stroke:#1f7a9c,color:#0b4f6c,stroke-dasharray:5 3
```

## 5. Deployment

*UML deployment diagram.* Where each part runs in production. One virtual server of about 2 vCPU and 4 GB RAM is enough for the pilot.

```mermaid
flowchart LR
    subgraph user["User devices"]
        b["Web browser<br/>desktop or phone"]
        a["Android phone<br/>Blue Bayelsa app"]
    end

    subgraph vps["Cloud VPS: Ubuntu Linux, Docker Engine"]
        subgraph compose["docker compose"]
            c1["web container<br/>nginx:1.27-alpine<br/>ports 80, 443"]
            c2["api container<br/>Python 3.12, Gunicorn, Django"]
            c3["db container<br/>postgis/postgis:16-3.4"]
        end
        v1[("volume: pgdata")]
        v2[("volume: private_uploads")]
        v3[("volume: static, media")]
        cron["cron: nightly backup script"]
    end

    gh["GitHub<br/>Chinwe-D/blue-bayelsa<br/>source code"]
    ci["GitHub Actions<br/>tests, Android build"]
    le["Let's Encrypt"]
    store["Off-site object storage<br/>encrypted backups, 30 days"]
    mon["Uptime monitor<br/>email alerts"]
    gplay["Google Play Store"]

    b & a -- "HTTPS 443" --> c1
    c1 --> c2 --> c3
    c3 --- v1
    c2 --- v2 & v3
    c1 --- v3
    cron -- "pg_dump + files" --> store
    gh -- "git pull, docker compose up" --> vps
    gh --> ci -- "signed .aab" --> gplay
    le -- "certificate renewal" --> c1
    mon -- "checks /api/health/" --> c1
```

## 6. Bulk upload and approval

*UML sequence diagram.* What happens when staff upload a spreadsheet. Nothing reaches the public until a second person approves it.

```mermaid
sequenceDiagram
    autonumber
    actor DE as Data entry officer
    participant UI as Admin portal
    participant API as Django API
    participant IMP as Importer
    participant DB as PostgreSQL
    actor RV as Reviewer

    DE->>UI: Download template
    UI->>API: GET /admin/importers/{type}/template/
    API-->>UI: Excel file with dropdowns and instructions
    DE->>UI: Upload filled file
    UI->>API: POST /admin/imports/ (file)
    API->>API: Check file type, size, row limit
    API->>IMP: Check every row
    IMP->>DB: Look up LGAs, communities, existing records
    IMP-->>API: Errors, warnings, duplicates per row
    API->>DB: Save batch and rows in staging tables
    API-->>UI: Summary: ready / errors / duplicates
    loop Until no problems remain
        DE->>UI: Correct or skip a row
        UI->>API: PATCH /admin/imports/{id}/rows/{row}/
        API->>IMP: Re-check rows
        API-->>UI: Updated row status
    end
    DE->>UI: Import
    UI->>API: POST /admin/imports/{id}/commit/
    API->>DB: Create records as Draft, write audit log
    DE->>UI: Submit drafts for approval
    RV->>UI: Open approval queue
    RV->>API: Approve (not own records)
    API->>DB: Status Approved, record approver and time
    Note over API,DB: Only approved records are returned by /api/v1/public/
```

## 7. Record publication workflow

*UML state machine diagram.* Every enterprise, indicator value, opportunity and infrastructure record follows this life cycle. It is enforced on the server and every transition is logged.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Draft: created manually or by upload
    Draft --> Submitted: submit [data entry]
    Submitted --> Approved: approve [reviewer, not the creator]
    Submitted --> Returned: return with reason [reviewer]
    Submitted --> Rejected: reject with reason [reviewer]
    Returned --> Submitted: correct and resubmit
    Approved --> Archived: archive with reason [administrator]
    Draft --> Archived: archive [administrator]
    Returned --> Archived: archive [administrator]
    Rejected --> Archived: archive [administrator]
    Archived --> [*]
    note right of Approved
        Published: visible on the
        public website and Android app
    end note
```

## 8. Data flow from field to public

*UML activity diagram.* The end-to-end path of research data, from the community to the dashboard.

```mermaid
flowchart TB
    start((" ")):::startend --> a1["Enumerator interviews enterprise<br/>KoboCollect on phone, GPS captured"]
    a1 --> a2["Forms upload to KoboToolbox<br/>when network is available"]
    a2 --> a3["Project staff export survey data<br/>as Excel"]
    a3 --> a4["Upload to Blue Bayelsa admin portal"]
    a4 --> d1{"All rows pass checks?"}
    d1 -- "no" --> a5["Correct or skip rows<br/>in the browser"]
    a5 --> d1
    d1 -- "yes" --> a6["Import as Draft records<br/>linked to data source and file"]
    a6 --> a7["Submit for approval"]
    a7 --> d2{"Reviewer decision"}
    d2 -- "return" --> a8["Data entry corrects record"]
    a8 --> a7
    d2 -- "reject" --> stop1((" ")):::startend
    d2 -- "approve" --> a9["Record published"]
    a9 --> par["Scores recalculated<br/>dashboard and map updated"]
    par --> stop2((" ")):::startend

    classDef startend fill:#0b4f6c,stroke:#0b4f6c,color:#0b4f6c
```

## 9. Current data model

*Entity-relationship diagram (crow's foot).* Tables built so far. Enterprises, indicators, infrastructure, opportunities and scoring tables will be added in Phase 3 once the questionnaire is available.

```mermaid
erDiagram
    USER }o--o{ ROLE : "has"
    USER ||--o{ AUDIT_LOG : "performs"
    USER ||--o{ IMPORT_BATCH : "uploads"
    LGA ||--|{ COMMUNITY : "contains"
    SECTOR |o--o{ ACTIVITY : "groups"
    DATA_SOURCE |o--o{ IMPORT_BATCH : "describes"
    IMPORT_BATCH ||--|{ IMPORT_ROW : "holds"
    USER ||--o{ APPROVAL_RECORD : "decides"

    USER {
        int id PK
        string username
        string email
        string organisation
    }
    ROLE {
        int id PK
        string name "Data entry officer, Reviewer, Administrator"
    }
    LGA {
        int id PK
        string name
        multipolygon boundary
    }
    COMMUNITY {
        int id PK
        int lga_id FK
        string name
        point location "WGS84"
        string location_source
        bool is_survey_community
    }
    SECTOR {
        int id PK
        string name
        int display_order
    }
    ACTIVITY {
        int id PK
        int sector_id FK
        string name
    }
    DATA_SOURCE {
        int id PK
        string name
        string organisation
        string responsible_person
        date collection_start
        date collection_end
    }
    IMPORT_BATCH {
        uuid id PK
        string importer
        string original_filename
        string status
        int uploaded_by FK
        datetime committed_at
    }
    IMPORT_ROW {
        int id PK
        uuid batch_id FK
        int row_number
        json raw
        json errors
        string status
    }
    APPROVAL_RECORD {
        int id PK
        string record_type
        string record_id
        string action
        string from_status
        string to_status
        datetime timestamp
    }
    AUDIT_LOG {
        int id PK
        datetime timestamp
        string action
        string target
        json details
        string ip_address
    }
```
