-- PostgreSQL/Supabase production policies. SQLite local mode does not enforce RLS.
-- The application must SET LOCAL app.tenant_id before tenant-scoped queries.

DO $$
DECLARE table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'teams','employees','services','customers','incidents','incident_customers',
    'decisions','projects','tickets','documents','document_chunks',
    'organizational_memory','scoped_memory','research_sessions','workflow_events','audit_logs'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format(
      'CREATE POLICY tenant_isolation ON %I USING (tenant_id = current_setting(''app.tenant_id'', true)) WITH CHECK (tenant_id = current_setting(''app.tenant_id'', true))',
      table_name
    );
  END LOOP;
END $$;
