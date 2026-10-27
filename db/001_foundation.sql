CREATE TABLE IF NOT EXISTS raw_capture (
 id text PRIMARY KEY, body bytea NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS ingestion_run (
 id uuid PRIMARY KEY, indicator_id text NOT NULL, captured_at timestamptz NOT NULL,
 source_uri text NOT NULL, raw_hash text NOT NULL REFERENCES raw_capture(id),
 mode text NOT NULL CHECK (mode IN ('fixture','source')),
 status text NOT NULL CHECK (status IN ('accepted','quarantined','unchanged')), error text
);
CREATE TABLE IF NOT EXISTS vintage (
 id uuid PRIMARY KEY, run_id uuid NOT NULL REFERENCES ingestion_run(id),
 published_at timestamptz, known_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 methodology_version text NOT NULL, quality_status text NOT NULL,
 UNIQUE(run_id)
);
CREATE TABLE IF NOT EXISTS observation (
 id uuid PRIMARY KEY, indicator_id text NOT NULL, reference_period date NOT NULL,
 value numeric NOT NULL, unit text NOT NULL, vintage_id uuid NOT NULL REFERENCES vintage(id),
 supersedes uuid REFERENCES observation(id), mode text NOT NULL CHECK (mode IN ('fixture','source')),
 UNIQUE(indicator_id, reference_period, vintage_id)
);
CREATE INDEX IF NOT EXISTS observation_lookup ON observation(indicator_id, mode, reference_period);
CREATE TABLE IF NOT EXISTS outbox (
 id uuid PRIMARY KEY, event_type text NOT NULL, payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 processed_at timestamptz, attempts integer NOT NULL DEFAULT 0, last_error text,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processed','dead_letter'))
);
CREATE TABLE IF NOT EXISTS scenario_run (
 id text PRIMARY KEY, scenario_id text NOT NULL, model_version text NOT NULL,
 inputs jsonb NOT NULL, outputs jsonb NOT NULL, event_id uuid NOT NULL REFERENCES outbox(id),
 mode text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS alert (
 id text PRIMARY KEY, scenario_run_id text NOT NULL REFERENCES scenario_run(id),
 severity text NOT NULL, owner_role text NOT NULL, sla_hours integer NOT NULL,
 status text NOT NULL DEFAULT 'new', review_status text NOT NULL DEFAULT 'pending_human_review',
 evidence jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE OR REPLACE FUNCTION reject_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'append-only evidence: updates and deletes are forbidden'; END;
$$ LANGUAGE plpgsql;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['raw_capture','ingestion_run','vintage','observation','scenario_run'] LOOP
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'immutable_' || t) THEN
   EXECUTE format('CREATE TRIGGER immutable_%I BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION reject_mutation()',t,t);
  END IF;
 END LOOP;
END $$;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='bdf_reader') THEN
  CREATE ROLE bdf_reader LOGIN PASSWORD 'local-reader-only';
 END IF;
END $$;
GRANT USAGE ON SCHEMA public TO bdf_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bdf_reader;
