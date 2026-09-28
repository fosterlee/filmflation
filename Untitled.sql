-- Streamlit apps are schema-level objects in Snowflake.
-- Therefore, they are located in a schema under a database.
-- They also rely on virtual warehouses to provide the compute resource.
-- We recommend starting with X-SMALL warehouses and upgrade when needed.

-- To help your team create Streamlit apps successfully, consider running the following script.
-- Please note that this is an example setup.
-- You can modify the script to suit your needs.

-- If you want to create a new database for Streamlit Apps, run
CREATE DATABASE STREAMLIT_APPS;
-- If you want to create a specific schema under the database, run
CREATE SCHEMA <SCHEMA_NAME>;
-- Or, you can use the PUBLIC schema that was automatically created with the database.

-- If you want all roles to create Streamlit apps in the PUBLIC schema, run
GRANT USAGE ON DATABASE STREAMLIT_APPS TO ROLE PUBLIC;
GRANT USAGE ON SCHEMA STREAMLIT_APPS.PUBLIC TO ROLE PUBLIC;
GRANT CREATE STREAMLIT ON SCHEMA STREAMLIT_APPS.PUBLIC TO ROLE PUBLIC;
GRANT CREATE STAGE ON SCHEMA STREAMLIT_APPS.PUBLIC TO ROLE PUBLIC;

-- Don't forget to grant USAGE on a warehouse.
GRANT USAGE ON WAREHOUSE <WAREHOUSE_NAME> TO ROLE PUBLIC;

-- If you only want certain roles to create Streamlit apps,
-- or want to enable a different location to store the Streamlit apps,
-- change the database, schema, and role names in the above commands.