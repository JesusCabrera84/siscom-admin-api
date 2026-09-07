-- DROP SCHEMA mobility;

CREATE SCHEMA mobility AUTHORIZATION pgadmin;

-- DROP SCHEMA mobility;

CREATE SCHEMA mobility AUTHORIZATION pgadmin;

-- Drop table

-- DROP TABLE mobility.current_locations;

CREATE TABLE mobility.current_locations (
	device_id uuid NOT NULL,
	customer_id uuid NULL,
	user_id uuid NULL,
	recorded_at timestamptz NOT NULL,
	received_at timestamptz DEFAULT now() NOT NULL,
	lat float8 NOT NULL,
	lon float8 NOT NULL,
	speed_kmh float8 NULL,
	accuracy_m float8 NULL,
	heading float8 NULL,
	altitude_m float8 NULL,
	battery_level float8 NULL,
	h3_index text NOT NULL,
	h3_resolution int4 DEFAULT 10 NOT NULL,
	"source" text DEFAULT 'mobility'::text NOT NULL,
	metadata jsonb NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT current_locations_pkey PRIMARY KEY (device_id)
);
CREATE INDEX idx_current_locations_customer ON mobility.current_locations USING btree (customer_id);
CREATE INDEX idx_current_locations_h3 ON mobility.current_locations USING btree (h3_index);
CREATE INDEX idx_current_locations_updated_at ON mobility.current_locations USING btree (updated_at);

-- Drop table

-- DROP TABLE mobility.devices;

CREATE TABLE mobility.devices (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	user_id uuid NOT NULL,
	device_type text NOT NULL,
	platform text NULL,
	device_name text NULL,
	external_device_id text NULL,
	app_version text NULL,
	os_version text NULL,
	last_seen_at timestamptz NULL,
	is_active bool DEFAULT true NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	notification_device_id uuid NULL,
	CONSTRAINT chk_device_type CHECK ((device_type = ANY (ARRAY['PHONE'::text, 'WATCH'::text, 'BLE_TAG'::text, 'WEARABLE'::text]))),
	CONSTRAINT devices_pkey PRIMARY KEY (id),
	CONSTRAINT devices_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE,
	CONSTRAINT mobility_devices_notification_device_id_fkey FOREIGN KEY (notification_device_id) REFERENCES public.user_devices(id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX uq_mobility_devices_notification_device ON mobility.devices USING btree (notification_device_id) WHERE (notification_device_id IS NOT NULL);

-- Drop table

-- DROP TABLE mobility.locations;

CREATE TABLE mobility.locations (
	id bigserial NOT NULL,
	device_id uuid NOT NULL,
	lat float8 NOT NULL,
	lon float8 NOT NULL,
	h3_cell varchar(32) NULL,
	accuracy_m float8 NULL,
	speed_kmh float8 NULL,
	heading float8 NULL,
	altitude_m float8 NULL,
	battery_level int2 NULL,
	motion_state text DEFAULT 'UNKNOWN'::text NOT NULL,
	recorded_at timestamptz NOT NULL,
	received_at timestamptz DEFAULT now() NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	CONSTRAINT locations_pkey PRIMARY KEY (id, recorded_at),
	CONSTRAINT locations_device_id_fkey FOREIGN KEY (device_id) REFERENCES mobility.devices(id) ON DELETE CASCADE
);
CREATE INDEX idx_locations_device_recorded_at ON mobility.locations USING btree (device_id, recorded_at DESC);
CREATE INDEX idx_locations_h3_cell ON mobility.locations USING btree (h3_cell);
CREATE INDEX idx_locations_recorded_at ON mobility.locations USING btree (recorded_at DESC);
CREATE INDEX locations_recorded_at_idx ON mobility.locations USING btree (recorded_at DESC);

-- Table Triggers

create trigger ts_insert_blocker before
insert
    on
    mobility.locations for each row execute function _timescaledb_functions.insert_blocker();