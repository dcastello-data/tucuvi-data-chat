# Configuration of BigQuery Datasets

Tucuvi leverages **BigQuery** to store and organize anonymized data. Centralized in the `tucuvi-dev` project, these datasets house all necessary events to extract business intelligence.

> Important: All datasets must be located in the region europe-west1. Otherwise, it will not be possible to cross-join tables or integrate them within the same Dataform pipeline.
> 
1. **Partitioning**: Since the data volume is far from "Big Data," tables are not partitioned. Partitioning could degrade performance for Tucuvi's data structure and usage patterns.
2. **Clustering**: To optimize query performance, clustering is applied. Typical clustering fields include:
    - Event date (e.g., `started_at`, `created_at`, or `date`).
    - `client_id`
    - `work_unit_id`.

This setup ensures efficient query execution and streamlined analysis for all stakeholders.

**Note:** When designing the pipeline in Dataform, or when creating queries in Looker Studio, use these dimensions as they will optimize query performance.

For more information visit: 

- Google BigQuery Clustered tables: [https://cloud.google.com/bigquery/docs/clustered-tables](https://cloud.google.com/bigquery/docs/clustered-tables)
- Google BigQuery Partitioning tables: [https://cloud.google.com/bigquery/docs/partitioned-tables](https://cloud.google.com/bigquery/docs/partitioned-tables)

# Dataset: `tucuvi_data`

The `tucuvi_data` dataset stores domain events related to core operational entities such as **conversations, calls, patients, and practitioners**.

### ETL-Populated Tables

These tables are populated through the **Domain Events Transformer** (Cloud Run function `domain-event-transformers`):

- `actions`
- `alerts`
- `calls`
- `care_plans`
- `clinical_notes`
- `comments`
- `conversations`
- `patients`
- `phone_visit_summaries`
- `phone_visits`
- `practitioners`

### Firestore-Synchronized Tables

These tables are populated by the **Tucuvi Data Quality** pipeline (Cloud Run function `domain-event-tucuvi_data_quality`), executed daily:

- `conversations_classification`
- `origins`
- `protocols`
- `protocols_display`
- `sms`
- `work_units`

# Dataset: Iterations

Iteration datasets capture granular interaction data between LOLA and patients. Each dataset reflects a specific context, enabling in-depth analysis and comparison.

### Iteration Contexts

1. **`real_time_iterations`**: Data captured by LOLA during live conversations.
2. **`manual_review_iterations`**: Annotations and corrections made during manual review.
3. **`post_processed_iterations`**: Finalized data processed through automated workflows.
4. **`automatic_reviewer_iterations`**: Evaluations by the automatic reviewer to flag conversations for review or mark them as successful.
5. **`flow_displays`**: Final displays shown to practitioners in the Tucuvi Dashboard.

### Key Iteration Tables

- **`iterations`**: Populated by the ETL and stores:
    - `real_time_iterations`
    - `post_processed_iterations`
    - `authentication_iterations`: Data specific to authentication flows.
- **`tucuvi_data_iterations`**: Updated hourly by the `tucuvi-data-firestore-etl` Cloud Run function, loading data from Firestore into:
    - `real_time_iterations`
    - `manual_review_iterations`
    - `post_processed_iterations`
    - `automatic_reviewer_iterations`
    - `flow_displays`
    - `conversations_helper`: Supplemental data from Firestore.

> Note: The `tucuvi_data_iterations` dataset serves as a provisional duplicate of `Iterations`. As the Iterations dataset is not yet fully operational and lacks complete ETL integration, `tucuvi_data_iterations` ensures that iteration data can still be retrieved directly from Firestore.
> 

# Dataset: `tucuvi_dashboard`

This dataset tracks user interactions within the Tucuvi Dashboard. Data is uploaded twice daily through **Segment** and includes:

- Event tracking of user activities.
- Metrics on how practitioners interact with dashboard tools and flows.

<aside>
⚠️

REQUIRES MORE DETAILS

</aside>

# Data pipelines in Dataform

Dataform is a powerful tool for managing data workflows and transformations in BigQuery. At its core, it uses `sqlx` files, which are SQL queries combined with a defined configuration to create BigQuery tables or views. This structure enables seamless data transformations and reporting.

### **Project Structure**

A typical Dataform project is organized into the following folders:

1. **Sources**

- Define connections to existing BigQuery tables.
- Serve as the foundational data for subsequent transformations.

2. **Staging**

- Stage data from sources using Dataform models.
- Clean data and remove duplicates to ensure consistency and reliability.

3. **Analytics**

- Combine staging tables into dimension tables.
- Provide data structures optimized for reporting and analysis.

4. **Other Folders**

- Additional folders can be created for specific tasks, such as data handling automations or specialized transformations.

As a general rule, we work with SQLX models in Dataform. There are three different types of models

- Sources (`src_`): These declare the direct connection to the BQ table
- Staging (`stg_`): These models load the data from the sources and apply simple direct transformations to perform data cleaning, such as removing duplicates or modifying field formats.
- Analytics (`dim_`): These models perform more complex operations, joining and transforming staged models. The output of these models results in tables ready to be used in reporting for production.

### **Production Releases**

Each Dataform project includes a production release process:

1. **Release:** The release process compiles the code from the default branch into a production-ready state.

2. **Workflow:** The workflow executes the default pipeline, running the transformations and updating the target tables or views in BigQuery.

**Note**: We are setting our workflows to run with full refresh: because our models use logic that requires analysis of historical data, all models are built from scratch every time the pipeline runs.

### Repository Management

Dataform integrates an intuitive repository management system, enabling effective collaboration and version control:

1. **Development Workspace**

- Developers can work on changes in a dedicated development workspace.
- Changes can be pushed to the default branch once finalized.
- Projects are configured to create the Dataform models in datasets with the _dev suffix. When running a pipeline in the development workspace, the models will be created in these folders instead of the production folders.

2. **Versioning and Synchronization**

- To maintain accurate version tracking, Dataform can synchronize with external repositories, such as GitLab.
- Currently, only the `tucuvi_data_pipeline_workspace` is synchronized with a GitLab repository.

### **Project configuration**

The main file configuring the pipeline is `workflow_settings.yaml`

```yaml
defaultProject: tucuvi-dev # MUST ALWAYS BE tucuvi-dev
defaultLocation: europe-west1 # MUST ALWAYS BE europe-west1
defaultDataset: dataform # This is the name of the default BQ dataset
defaultAssertionDataset: dataform_assertions # Where assertions will be stored
dataformCoreVersion: 3.0.0-beta.4 # Dataform version
```

Additionally, each model will have a configuration header at the top of the file that can override the default configuration settings:

```yaml
config {
    type: "table", # Set view or table. It is recommended to use 'table' for reporting tables
    schema: "dataform_reporting", # Dataset where the model will be stored
    description: "Main alert information for reporting.", # Description metadata
    bigquery: {
      clusterBy: ["created_at", "work_unit_id"] # clustering fields: at minimum, always date field and work_unit_id
      },
    dependencies: [ 
      "op_create_es_demos", 
      "op_create_en_demos"
    ] # If we need to force the model to run after other models, we can define a dependency. When the models are referenced in the model, Dataform detects it automatically.
}
```

# Managing properties in Dataform

We always use the most relevant date field and `work_unit_id` for queries and joins. This is to optimize query performance. However, later in the workflow, specially in Looker Studio, we might use other properties to filter the data. Because in one report we might be using multiple tables, we want to centralize these properties so that they are shared between all report tables. These tables are:

- `pp_general_properties`: properties associated to the patients, these include the following fields:
    - `patient_id`
    - `work_unit_id`
    - `clinic_id`
    - `origin`
    - `patient_gender`
    - `HCP_responsible`
    - `birth_date`
    - `HCP_responsible_name`
    - `work_unit_display`
    - `is_active_client`
    - `is_active_work_unit`
    - `is_demo_work_unit`
    - `hospital`
    - `origin_display`
    - `patient_age`
- `pp_conversation_properties`: properties associated to the conversations, these include the following fields:
    - `conversation_id`
    - `work_unit_id`
    - `protocol_id`
    - `protocol_name`
    - `patient_id`
    - `str_month`
    - `last_day_of_month`
    - `conversation_number`
    - `protocol_conversation_number`
    - `first_conversation_date`
    - `month_number`
    - `protocol_names`
    - `origin_displays`
    - `conversa`
    - `clean_protocol_name`
    - `patient_care_pathways`
    - `specialties`
    - `care_delivery_phases`
    - `clean_protocol_name_display`
    - `patient_care_pathways_display`
    - `specialties_display`
    - `care_delivery_phases_display`
    - `clean_protocol_name_display_es`
    - `patient_care_pathways_display_es`
    - `specialties_display_es`
    - `care_delivery_phases_display_es`
    - `str_patient_care_pathways`
    - `str_specialties`
    - `str_care_delivery_phases`
    - `str_patient_care_pathways_display`
    - `str_specialties_display`
    - `str_care_delivery_phases_display`
    - `str_patient_care_pathways_display_es`
    - `str_specialties_display_es`
    - `str_care_delivery_phases_display_es`

# Managing duplicates

As a general rule, duplicates are managed by selecting a unique identifier, which can be a field or a combination of fields, and using the latest row by `inserted_at`, a default field that must be in all raw BQ tables that indicates when the row was last inserted.

# Pipelines: Iterations

- `iterations_pipeline_workspace`: Processes iteration tables to generate report ready tables for iterations and flows.
    - Source tables loaded from BQ:
        - from `tucuvi_data_iterations` dataset:
            - `real_time_iterations`
            - `manual_review_iterations`
            - `post_processed_iterations`
            - `automatic_reviewer_iterations`
            - `flow_displays`
        - from `tucuvi_data` dataset:
            - `work_units`
            - `protocols`
        - form `dataform` dataset:
            - `pp_conversation_properties`
            - `pp_general_properties`
    - Staging tables at `dataform_iterations` dataset:
        - `map_iteration_ids`: This table is used to map the iteration IDs constructed by `tucuvi_data_firestore_etl`  with the iteration IDs in the dataset `Iterations`.  It is a provisional measure to use data directly sent by Domain Events Transformers.
        - `stg_automatic_reviewer_iterations`
        - `stg_flow_displays`
        - `stg_manual_review_iterations`
        - `stg_post_processed_iterations`
        - `stg_pp_conversation_properties`
        - `stg_pp_general_properties`
        - `stg_protocols`
        - `stg_real_time_iterations`
    - Reporting tables at `dataform_iterations_reporting` dataset:
        - `dim_iterations`: Resulting tables with all iteration data
            - The model `create_levenshtein_udf` is used to create a function (routine stored in the dataset `dataform_iterations`) compute how much the asr has changed from post processed to manual review context.
            
            ```sql
            `dataform_iterations.levenshtein`(pp.asr_used_post_processed, mr.asr_manual_review) AS asr_similarity
            ```
            
        - `dim_flows`: Resulting tables with all flow data
        - `dim_iterations_500`: Final table of iterations containing only the iterations of the last 500 flows, grouped by conversa.
        - `dim_flows_500`: Final table of flows containg only the last 500 flows of each flow grouped by conversa

# Pipelines: Tucuvi Data

- `tucuvi_data_pipeline_workspace`: Processes data to generate report ready tables for all operational and clinical metrics.
    - Source tables directly loaded from BQ:
        - from `tucuvi_data` dataset:
            - `actions`
            - `alerts`
            - `calls`
            - `care_plans`
            - `clinical_notes`
            - `comments`
            - `conversations`
            - `patients`
            - `phone_visit_summaries`
            - `phone_visits`
            - `practitioners`
            - `conversations_classification`
            - `origins`
            - `protocols`
            - `protocols_display`
            - `sms`
            - `work_units`
        - from `dataform_iterations_reporting` dataset:
            - `dim_iterations`
            - `dim_flows`
    - Staging tables at `dataform` dataset:
        - `assertion_conversations_unanswered` : returns unanswered conversations with less than 4 call attempts.
        - `protocol_entities` : This table is used to define **entities** that should be stored in conversations. Each protocol specifies a list of flows from which entities will be extracted. Conversations associated with the protocol will store these entities for the selected flows.
        
        ```sql
        -- Selecting the entities in staging/protocol entities
        
        SELECT
          'Gestión de demanda: Valencia' AS protocol_name, # Protocol
          ['asksip', 'sipready', 'callreason'] AS extract_entities # Flows to extract
        ```
        
        ```sql
        
        -- For the selected protocols
        -- Entities structured in analytics/dim_conversations_entities.sqlx
        SELECT
          conversation_id,
          work_unit_id,
          protocol_name,
          ARRAY_AGG(
            STRUCT(
              parent_flow AS parent_flow,
              entity_names_array AS entity_names_array,
              str_entity_values_array AS str_entity_values_array
            )
          ) AS entity
        FROM parent_flow_aggregates
        GROUP BY
          conversation_id,
          work_unit_id,
          protocol_name
        ```
        
        - `protocol_objectives`: This table defines the **display flows** (objectives) that should be stored in conversations. Similar to `protocol_entities`, it allows for selecting specific protocols and their relevant objectives.
        
        ```sql
        -- Selecting the entities in staging/protocol entities
        
        SELECT
          'Seguimiento CPAP ECOSTAR' AS protocol_name, -- Protocol
          ['Horas de uso por noche', 'Horas de la turbina'] AS objectives -- Objectives to store
        UNION ALL
        SELECT
          'Adherencia CPAP' AS protocol_name, -- Protocol
          ['Horas de uso por noche', 'Tiempo de uso'] AS objectives -- Objectives to store
        ```
        
        ```sql
        
        -- For the selected protocols
        -- Entities structured in analytics/dim_conversations_objectives.sqlx
        SELECT
          conversation_id,
          work_unit_id,
          protocol_name,
          ARRAY_AGG(STRUCT(flow_title, flow_display)) AS objective
        FROM 
          filtered_flows
        GROUP BY 
          conversation_id, work_unit_id, protocol_name
        ```
        
        - `stg_actions`
        - `stg_alerts`
        - `stg_calls`
        - `stg_care_plans`
        - `stg_clinical_notes`
        - `stg_comments`
        - `stg_conversations_classification`
        - `stg_conversations`
        - `stg_dim_flows`
        - `stg_dim_iterations`
        - `stg_origins`
        - `stg_patient_events`
        - `stg_patients`
        - `stg_phone_visit_summaries`
        - `stg_phone_visits`
        - `stg_practitioners`
        - `stg_protocols_display`
        - `stg_protocols_flattened`
        - `stg_protocols`
        - `stg_sms`
        - `stg_work_units`
    - Automations at `automations:`
        - `js_generate_synthetic_data` : Defines the functions to copy data from a work unit, VHE-W-0002, and change certain values to create synthetic data. This work unit was selected because they have a good management of THM.
        - `op_create_es_demos`: Inserts the data in the necessary staging tables.
        - `js_generate_en_translations`: Function to translate the necessary data to create synthetic data in english. It translates the data generated with `js_generate_synthetic_data`
        - `op_create_en_demos`: Inserts the english data in the necessary staging tables.
    - Reporting tables at `analytics`:
        - `dim_actions`
        - `dim_alerts`
        - `dim_calls`
        - `dim_care_plans`
        - `dim_clinical_notes`
        - `dim_concurrence`
        - `dim_conversations_clinical_analysis`
        - `dim_conversations_entities`
        - `dim_conversations_objectives`
        - `dim_conversations_sms`
        - `dim_conversations_valencia`
        - `dim_conversations`
        - `dim_patient_events`
        - `dim_patients`
        - `dim_phone_visits`
        - `dim_practitioners`
        - `dim_sms`
        - `dim_work_units`
    - Add empty date rows to allow visualization of empty date intervals in Looker Studio in `date_mockups`:
        - `insert_temp_dates_alerts`
        - `insert_temp_dates_conversations`
        - `insert_temp_dates_patient_events`
        - `temp_dates_alerts`
        - `temp_dates_patient_events`
        - `temp_dates`
    
    To ensure consistent time-series visualization in Looker Studio, empty date rows are added to tables like `conversations`, `alerts`, and `patient_events` for all dates of the year. Aggregated fields, such as protocol names, origins, and alert names, are generated to allow filtering while preserving these empty rows. Temporary tables (`temp_dates_*`) are created with enriched aggregated data and joined with the original tables to support filters without losing visibility of empty dates. This approach ensures complete date intervals are displayed, improving trend analysis and user experience in Looker Studio.
    
    ```sql
      -- aggregate fields for dim_alerts
      
      aggregated_fields AS (
        SELECT
          work_unit_id,
          ARRAY_AGG(DISTINCT IFNULL(CAST(protocol_name AS STRING), '') IGNORE NULLS) AS protocol_names,
          ARRAY_AGG(DISTINCT IFNULL(CAST(origin_display AS STRING), '') IGNORE NULLS) AS origin_displays,
          ARRAY_AGG(DISTINCT alert_name) AS alert_names
        FROM
          ${ref("dim_alerts")}
        WHERE
          work_unit_id IS NOT NULL
        GROUP BY
          work_unit_id
      ),
    ```
    

# Tucuvi Dashboard

- `thm_pipeline_workspace`: This pipeline process all event information from `tucuvi_dashboard` dataset.
    - Staging tables: dynamically defined
    - Reporting tables:
        - `dim_thm_events`: Table storing all events sent by Segment.
        - `dim_thm_sessions`: Table grouping all events by sessions, computed with logic.
        - `dim_thm_reviews`: Table containing all ‘patient_review’ events
        

<aside>
⚠️

REQUIRES MORE DETAILS

</aside>

# Looker Studio

Looker Studio is a dashboard crafting platform that natively integrates with BigQuery, allowing seamless visualization of data. It supports extensive customization options, ranging from personalized UI design to creating calculated fields, filters, and parameters. Tucuvi uses the **PRO version** within the GCP project `tucuvi-test`, where all Looker Studio dashboards are organized under the **Dashboards** section.

## Data Sources

Looker Studio connects data to dashboards through **data sources**, which establish connections to BigQuery tables or views. These sources store calculated fields and parameters, and their naming follows a structured format to ensure consistency and manageability.

### Naming Convention for Data Sources

The naming format for data sources is as follows:

```
{dataform_table_name}_{technical_context}_{language}_{version}
```

- **Dataform Table Name**: Name of the Dataform table connected to the data source.
- **Technical Context**: A broad categorization, ranging from production (`prod`) and development (`dev`) to specific contexts like client-specific dashboards. The context `url_prod` indicates production data sources using URL parameters for filtering.
- **Language**: Sources are separated by language to manage fields and parameters efficiently.
- **Version**: Tracks updates in the Dataform pipeline and ensures compatibility.

### Examples:

- `dim_conversations_prod_es_v2`
- `dim_alerts_url_prod_en_v2`
- `dim_actions_dev_v2`

### Configuring the Data Source

1. **Connection to BigQuery**: Data sources are connected using a **Custom Query**.
2. **Data Freshness**: Set to update every hour, ensuring dashboards reflect recent data.
3. **Field Editing**: Field editing in dashboards is enabled by default for flexibility. However, changes to fields in a data source impact all dashboards using the same source.

### Using URL Parameters

To allow a single data source to serve multiple clients, **URL parameters** can be used to dynamically filter queries based on the client's needs. For example:

```sql
-- Example: table dim_care_plans_url_prod_pt_v2
SELECT * FROM dataform_reporting.dim_care_plans
WHERE
  work_unit_id = @work_unit_param
```

### Steps to Configure URL Parameters:

1. **Create a Parameter**: In the data source, define a parameter such as `work_unit_param`.
2. **Modify the Query**: Use the parameter in the query to filter data dynamically.
3. **Send Parameters via URL**: When loading a Looker Studio report, pass parameter values through the URL. For detailed steps, refer to the [Google documentation on URL parameters](https://developers.google.com/looker-studio/connector/data-source-parameters#set_url_parameters).

This setup allows the same data source to securely and efficiently serve different queries for various clients, maintaining flexibility and scalability.

https://developers.google.com/looker-studio/connector/data-source-parameters#set_url_parameters

## Filters

Filters in Looker Studio are typically added using **Controls**, such as a **Drop-down list** filter. While there are other types of controls available (e.g., advanced filters, sliders, checkboxes), the drop-down filter is one of the simplest and most versatile ways to help users interactively refine the data displayed in your reports.

**Where to Apply Filters:**

- **Page-Level Filters:**
    
    These filters affect only the currently selected page. If you have multiple pages in your report, a page-level filter will not impact the data shown on other pages.
    
- **Report-Level Filters:**
    
    These filters apply to every page within the report. To use a filter at the report level, right-click on the filter control and select **"Make report-level"** (or similar wording depending on your version). This ensures that the filter’s criteria will influence all pages simultaneously.
    

**How Filters Work:**

When you create a filter, it will query all data sources present on the page. Importantly, filters match fields based on their **Field ID**, not their display name. That means if multiple data sources contain a field with the same Field ID, applying a filter on that field will also affect every other data source with the same ID.

**Best Practices:**

- **Choose the Correct Field ID:**
    
    When adding or creating fields, ensure that the Field ID is consistent with your intended filters. Inconsistent or incorrect Field IDs can lead to unintended filtering across multiple data sources.
    
- **Use Clear Naming Conventions:**
    
    While the display name does not control filtering, it’s still helpful to give your fields meaningful names so you and your team can easily understand what each field represents.
    
- **Test Your Filters:**
    
    After setting up filters, check your visualizations to confirm they’re filtering as intended. Adjust field IDs, filter settings, or data source configurations if you notice unexpected results.
    

By carefully managing filters and their associated Field IDs, you can create interactive, user-friendly reports that allow viewers to drill down into the data that matters most to them.

## **Calculated Fields**

Looker Studio allows the creation of calculated fields at the data source level using SQL formulas. These fields enable additional logic, metrics, and visual enhancements for dashboards.

### Examples of Use Cases

### 1. **Creating Additional Logic**

Calculated fields can incorporate conditional logic to classify or transform data.

Example:

```sql
CASE
  WHEN total_alerts = 0 THEN 'Without alert'
  WHEN total_alerts > 0 AND total_high_alerts + total_medium_alerts = 0 THEN 'LOW'
  WHEN total_medium_alerts > 0 AND total_high_alerts = 0 THEN 'MEDIUM'
  WHEN total_high_alerts > 0 THEN 'HIGH'
END
```

### 2. **Aggregated Metrics**

Calculated fields can aggregate data for advanced reporting.

Example:

```sql
COUNT_DISTINCT(CASE WHEN is_answered = TRUE THEN patient_id ELSE NULL END)
```

### 3. **Display Decorators**

These fields enhance visualizations by adding descriptive or contextual labels.

Example:

```sql
ASE
  WHEN Categoría = 'all' AND actions_array_dynamic IS NULL THEN 'Sin acción'
  WHEN Categoría = 'actions' AND actions_array_dynamic IS NULL THEN 'Sin acciones ni derivaciones'
  WHEN Categoría = 'diagnostic_methods' AND actions_array_dynamic IS NULL THEN 'Sin métodos diagnósticos'
  WHEN Categoría = 'treatments' AND actions_array_dynamic IS NULL THEN 'Sin tratamientos'
  WHEN Categoría = 'assessments' AND actions_array_dynamic IS NULL THEN 'Sin valoraciones'
  ELSE actions_array_dynamic
END
```

# Creating Views and Tables

In Looker Studio, every visualization is built around **dimensions** and **metrics**. **Dimensions** determine how data is grouped (e.g., by date, alert name, or category), while **metrics** are aggregated values (e.g., counts, sums, averages) associated with those dimensions.

When you create a view or table in Looker Studio, the platform typically handles most dimension groupings automatically. However, you can customize these groupings and define key settings to refine your visualization.

**Key Components to Consider:**

1. **Date Range Dimension:**
    
    This field filters the displayed data according to a chosen date range. It is the primary reference used to limit the timeframe of the data that appears in your view or table.
    
2. **Dimension:**
    
    This is the primary grouping field for your data. For example, if you select "Date" as your dimension, your data will be grouped by days, weeks, or months. You can also group by other fields like category names, alert types, or any other string-based dimension.
    
3. **Breakdown Dimension:**
    
    When you want to add a secondary level of grouping within your primary dimension, use the breakdown dimension. For example, if your main dimension is "Date," the breakdown dimension could be "Category" to see how different categories perform over time.
    
4. **Metric:**
    
    The metric represents the aggregated data you want to display, such as the total number of alerts, average values, sum of clicks, or any other measurable quantity. It’s the numeric value that will appear in your table or chart.
    
5. **Sort:**
    
    Sorting fields determine the order in which data is displayed. You might sort your table by a metric (e.g., highest to lowest count), or by a dimension (e.g., alphabetical order).
    
6. **Secondary Sort:**
    
    A secondary sort is applied after the primary sort. For example, if you first sort by date, you might then apply a secondary sort by a related metric to fine-tune the order of your results.
    
7. **Filter:**
    
    Filters allow you to include or exclude certain data points from your view or table. For example, you might filter your table to only show data from a specific region or category.
    

**Additional Settings:**

Depending on the type of view or table you select (e.g., scorecards, pie charts, time series, or geo charts), you may see additional configuration options. These can include changing the visualization type, formatting the data display, adding comparisons to previous periods, or customizing colors and styles.

Use these guidelines as a general reference when setting up your views and tables. Experimenting with different dimensions, metrics, and filters will help you create meaningful, insightful visualizations that effectively communicate your data’s story.

# **Reports**

Looker Studio dashboards are referred to as **Reports**. These are created in the `tucuvi-test → Dashboards` project by licensed users, such as [d.castello@tucuvi.com](mailto:d.castello@tucuvi.com) or [marcos@tucuvi.com](mailto:marcos@tucuvi.com). Once created, reports can be edited by other team members in the organization.

### **Managing the UI**

All production dashboards follow a standard template. If you wish to make changes to the template, please contact [a.plana@tucuvi.com](mailto:a.plana@tucuvi.com).

### **Publishing the Report**

For production reports, it is recommended to activate **Report Publishing** (via `File → Publishing settings`). This feature allows:

- Version history tracking.
- Working on drafts.
- Publishing only when the report is finalized.

### **Sharing the Report**

Report sharing is managed through Google accounts and offers two options:

1. **Unlisted Sharing**: Allows anyone with the link to access the report, though it will not appear in online searches. This is the most straightforward option for sharing with clients.
2. **Secure Sharing**: Define permissions for specific Google accounts.
    - If the client does not use a Google account, they can link their work account to Google following the provided procedure.

https://docs.google.com/document/d/1GCiDwBjsbDLgxEa2k9NUGlep9YhGrp19oeMfMC-s0Xw/edit?tab=t.0#heading=h.ciccrnjcpcjz

# Tucuvi Data Quality

This documentation describes the **Tucuvi Data Quality** system, responsible for ensuring data consistency and synchronization between Firestore and BigQuery in the `tucuvi-dev` project.

- **Repository**: [Tucuvi Data Quality](https://gitlab.com/tucuvi/tucuvi-data/tucuvi-data-quality)
- **Cloud Run Function**: [tucuvi_data_quality](https://console.cloud.google.com/functions/details/europe-west1/tucuvi_data_quality?env=gen2&hl=en&inv=1&invt=Abjv_Q&project=tucuvi-dev)
- **Scheduler**: [tucuvi_data_quality_check](https://console.cloud.google.com/cloudscheduler/jobs/edit/europe-west1/tucuvi-data-quality-check?hl=en&project=tucuvi-dev&inv=1&invt=Abjv_Q)

This system supports:

1. Syncing Firestore data with BigQuery.
2. Updating critical datasets in the BigQuery project `tucuvi_data`.
3. Performing health checks on the ETL pipeline.

## Repository Features

### 1. Sync Firestore Data with BigQuery

This function ensures synchronization between Firestore and BigQuery by updating the following datasets:

- **Protocols**
- **Work Units**
- **Origins**
- **SMS Data**

### 2. Run LLM classification

- **Conversations Classification**:
    - Uses OpenAI API to classify conversations based on specific criteria (currently set up for Valencia C-0042).
    - Results are stored in the BigQuery dataset `tucuvi_data`, table `conversations_classification`.
    - The logic is as follows:
        1. We query the conversations that we want to classify and assign them a ‘bucket’. We then query the entire transcripts to use them as input for the LLM. (in the code, the query is defined in the folder llm_library). Note: this can contain personal data, so make sure to use mask_data.py accordingly. 
        2. We classify each conversation through the logic defined in azure_openai.py which will select the prompt according to the bucket.
    
    ```sql
    ```
    LÓGICA DE CLASIFICACIÓN CON PARA VALENCIA LLMs
    
    1. El paciente no se ha autenticado (bucket = 'no_auth' -> call_output = 'Paciente no identificado'):
        prompt_no_auth.txt 
    
    2. El paciente se ha autenticado, y llega al final de la conversación sin haber entrado en negociación de citas 
    (bucket='unknown' -> call_output = 'Flujograma no contemplado' AND str_flows_array LIKE "%startscheduleappointment%")
        prompt_unknown.txt 
    
    3. El paciente cuelga en algún momento o la conversación termina sin cita agendada habiendo negociado una cita.
    (bucket = 'hanged_or_negotiation' 
        -> call_output = 'Paciente cuelga' 
        OR str_flows_array LIKE "%startscheduleappointment%" AND call_output != 'Cita agendada'). 
        prompt_hanged_or_negotiation.txt
    ```
    ```
    

Note: To fully comprehend this LLM classification or use it to classify conversations in another project, use the notebook `upload_llm_classification.ipynb`

### 3. ETL Health Checks

The function verifies data consistency for critical tables, identifying missing records or discrepancies in key fields.

### **Conversations**

- **Purpose**: Ensures all Firestore documents exist in BigQuery and compares fields.
- **Field Comparisons**:
    - `is_answered`
    - `is_completed`
    - `is_HCP_reviewed`
    - `total_alerts`

### **Calls**

- **Purpose**: Verifies future scheduled calls match between Firestore and BigQuery.
- **Field Comparison**:
    - `next_call_at`

### **Patients**

- **Purpose**: Ensures all patient records are present in BigQuery and checks for status alignment.
- **Field Comparison**:
    - `status`

## Logging and Monitoring

- **Logging**: Each operation logs progress and results for debugging. Logs include confirmation messages after updates and discrepancies identified during health checks.
- **Notifications**: A daily email summary of results is sent to:
    - [d.castello@tucuvi.com](mailto:d.castello@tucuvi.com)
    - [marcos@tucuvi.com](mailto:marcos@tucuvi.com)

This ensures transparency, efficient monitoring, and rapid issue resolution.

# Tucuvi Data Firestore ETL

- **Repository**: [Tucuvi Data Firestore ETL](https://gitlab.com/tucuvi/tucuvi-data/firestore-etl)
- **Cloud Run Function**: [tucuvi-data-firestore-etl](https://console.cloud.google.com/functions/details/europe-west1/tucuvi-data-firestore-etl?env=gen1&hl=en&project=tucuvi-dev)
- **Scheduler**: [tucuvi_data_firestore_etl_trigger](https://console.cloud.google.com/cloudscheduler/jobs/edit/europe-west1/tucuvi-data-firestore-etl-trigger?hl=en&project=tucuvi-dev)

The `iteration_tables_script` is designed to extract, transform, and load detailed information about conversation “iterations” into a BigQuery dataset. Each iteration represents a single step or exchange in a conversation (e.g., one prompt and one response). This structured approach simplifies downstream analytics, enabling clearer insights into conversational flows, user responses, and system behavior.

Key Steps:

1. **Fetching and Preparing Data:**
This script retrieves data from conversations that have not yet been processed to create both the real-time iterations and manual review iterations datasets. Only documents that have been pushed to production are included, determined by the presence of the `asrUpdated` field. Post-processed iteration data is obtained from the `iterations` collection, while Automated Review (AR) context comes from the `ar-results` collection. Flow displays are extracted from the `conversations` collection, specifically from the `observations` field.
    
    **AR Processing Note:** Because the format of the AR collection has evolved, the script employs two different processing approaches, depending on the conversation date:
    `ar_migration_date = datetime.datetime(2024, 8, 7, 0, 0, 0, tzinfo=datetime.timezone.utc)`
    
2. **Avoiding Duplicates and Ensuring Data Quality:**
    
    Only iterations from conversations not previously loaded into BigQuery are processed, verified against the `manual_review_iterations` table, preventing duplication. The script will load all conversations since the previous day at 00:00 UTC
    
3. **Processing Frequency:**
    - The script runs hourly, ensuring data is frequently updated without manual intervention.

Key Outputs:

- **Real-time Iterations Table:** Detailed records of each conversation turn as it occurred.
- **Manual Review Table:** Information about which iterations were reviewed, corrected, or validated by human reviewers.
- **Automatic Reviewer Table:** Indicators and flags from automated systems that highlight iterations needing further attention.
- **Post-processed Iterations Table:** Results from advanced batch processes (e.g., improved speech recognition, intent classification).
- **Flow Displays Table:** A record of the conversation flow views (displays) as observed by healthcare professionals (HCPs).
- **Helper/Metadata Tables:** Additional contextual data such as conversation variables, lists of displayed flows, and other supporting information.

By consolidating this information, the `iteration_tables_script` facilitates clear, reliable, and maintainable data analytics pipelines, supporting informed decision-making and continuous improvement of conversation flows.

# Editing data in BQ

When the data stored in the raw tables in BQ is corrupted or we need to update it, there are different approaches. 

- Taking advantadge of Dataform duplicates logic: When two duplicate records (for example two rows with the same conversation_id) are present in BQ, Dataform will take the one with the latest inserted_at date.
- Directly updating BQ. This is specially useful for data migrtions (changing the name of an alert), or editing displays.
    
    ```sql
    UPDATE `tucuvi_data.actions`
    SET action_display = 'Hospitalización'
    WHERE action_display = 'Re-ingreso hospital'
    ```
    

# Valencia: Gestión de la demanda

How are we reporting metrics in Valencia. This is a special project because we need to classify the conversations by analzying the specif flows that the converations went through. 

The ground truth of the metrics we are working with for the project are defined in Dataform, tucuvi_data_pipeline_workspace, model: analytics/personalized/dim_conversations_valencia.sqlx

## Metrics

1. **Authentication Metrics**
    - **is_correctly_authenticated**: Boolean indicating if the patient was successfully identified.
        
        Checked by looking for specific intent/flow patterns that confirm correct authentication and ensuring no invalid SIP flows are present.
        
    - **is_authentication_failed**: Boolean indicating the authentication explicitly failed.
        
        True if `str_transition_flows` includes `%byeinvalidsip%`.
        
    - **authentication_bucket**: Categorizes how authentication concluded:
        - "Paciente identificado" if successfully authenticated.
        - "Doble fallback" if conversation ended due to repeated errors or alerts.
        - "Autenticación fallida" if explicit authentication failure occurred.
        - "Paciente cuelga" if none of the above conditions are met and the patient presumably hung up.
2. **Appointment-Related Metrics**
    - **is_appointment_already_exists**: Checks if the system detected an existing appointment.
        
        True if `str_transition_flows` includes `%appointmentexistsinagenda%`.
        
    - **is_appointment_confirmed**: Indicates if an appointment was successfully confirmed.
        
        True if the confirmation intent was detected and no API errors (`byeapierror`) occurred.
        
3. **Call Outcome / Resolution Metrics**
    - **is_admin_bye**: Indicates if the call ended by sending a message to an administrative desk or in a manner that implies admin intervention.
        
        Derived from authenticated calls ending with `messagesenttoadmin` or certain recognized "admin bye" patterns not blocked by known negative conditions.
        
    - **is_bye_resolved**: Indicates if the call concluded in a resolved state without sending a message to admin or hitting error states.
        
        True if conversation ended with a known set of "bye" patterns representing a resolved scenario (e.g., reminding appointment, no available appointments, etc.) and without API errors or invalid SIP.
        
    - **is_silence**: Indicates the call had no user input or engagement.
        
        True if `is_answered = FALSE` or `str_intents_array` is NULL.
        
    - **is_patient_hanged**: Indicates that the patient presumably hung up before resolution.
        
        True if the conversation did not lead to a known resolution, admin escalation, confirmed appointment, or a recognized error, implying the patient disconnected prematurely.
        
    - **call_functional_results**: High-level functional categorization of the call’s end state:
        - "Cita agendada " if an appointment was confirmed.
        - "Enviada a mostrador" if escalated to admin.
        - "Gestionada sin mensaje a mostrador" if resolved without admin message.
        - "Sin gestionar" if none of the above (unresolved).
4. **Negotiation Metrics**
    - **negotiation_bucket**: Classifies how appointment negotiation proceeded:
        - "Sin negociación" if no scheduling attempt occurred.
        - "Rechaza negociar" if patient refused to schedule.
        - "Accede a negociar" if patient agreed to schedule.
        - "Sin negociación - Cuelga sin contestar" if patient hung up without negotiation.
5. **Detailed Outcome Classification**
    - **call_output**: A granular, final classification describing the outcome of the call based on `str_transition_flows` and other indicators.Examples include: "Paciente no identificado", "Error - API", "Cita agendada", "Cita cancelada", "Urgencias", "Centro erróneo", "Cita no identificada", "Negociación fallida", "Paciente cuelga", "No hay citas en los próximos 15 días", etc.
6. **Unresolved/Error Metrics**
    - **is_bye_not_resolved**: Indicates if the conversation ended in an unresolved manner due to errors, invalid SIP, an API error, an alert, or the patient hanging up.
7. **Overall Resolution Bucket**
    - **call_bucket**: Summarizes calls into "Resuelta" or "No resuelta":
        - "No resuelta" if the call ended with patient not identified, API errors, or patient hang-up.
        - "Resuelta" otherwise.

**Extra:**

- **call_reason and call_general_reason**: calculated with the classification of intents detailed here: https://docs.google.com/spreadsheets/d/1SolnvRRNMvWKJoVumFB1RdKMiLfRjwAmgeDtP1W9JEA/edit?gid=874470377#gid=874470377 and building a calculated field in Looker Studio.

## Reporting

We report to the client with the dashboard: Valencia: Gestión de la demanda - es https://lookerstudio.google.com/reporting/f032d814-61af-43b6-9223-e2f2e582a373/page/p_7vwyy4bend/edit

The output of the call is shown with the decorator call_output_reporting, a Looker Studio calculated field that decorates call_output.

## Debugging

For debugging in the Valencia project we use: Valencia: Gestión de la demanda - es https://lookerstudio.google.com/reporting/cfa7c616-ef6c-4080-96af-d7dbadcd3e63/page/p_4kn4vfotnd/edit

In the page ‘Debugging’ we can query the conversations according to the defined Valencia metrics. This is useful to find specific conversations or test the metrics: is the logic correct?

To understand how the LLM classification is performed, please refer to Tucuvi Data Quality.