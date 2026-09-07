-- api_platform.api_alerts definition

-- Drop table

-- DROP TABLE api_platform.api_alerts;

CREATE TABLE api_platform.api_alerts (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	organization_id uuid NULL,
	api_key_id uuid NULL,
	"type" text NOT NULL,
	threshold numeric NULL,
	time_window text NULL,
	enabled bool DEFAULT true NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT api_alerts_pkey PRIMARY KEY (id)
);


-- api_platform.api_limits definition

-- Drop table

-- DROP TABLE api_platform.api_limits;

CREATE TABLE api_platform.api_limits (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	plan_id uuid NOT NULL,
	rpm_limit int4 NULL,
	daily_limit int4 NULL,
	monthly_limit int4 NULL,
	burst_limit int4 NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT api_limits_pkey PRIMARY KEY (id)
);


-- api_platform.api_request_logs definition

-- Drop table

-- DROP TABLE api_platform.api_request_logs;

CREATE TABLE api_platform.api_request_logs (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	api_key_id uuid NOT NULL,
	organization_id uuid NOT NULL,
	"method" text NOT NULL,
	endpoint text NOT NULL,
	status_code int4 NOT NULL,
	latency_ms int4 NOT NULL,
	ip inet NULL,
	user_agent text NULL,
	request_size int4 NULL,
	response_size int4 NULL,
	error_code text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT api_request_logs_pkey PRIMARY KEY (id, created_at)
)
PARTITION BY RANGE (created_at);
CREATE INDEX idx_logs_api_key_time ON ONLY api_platform.api_request_logs USING btree (api_key_id, created_at DESC);
CREATE INDEX idx_logs_org_time ON ONLY api_platform.api_request_logs USING btree (organization_id, created_at DESC);


-- api_platform.api_throttle_events definition

-- Drop table

-- DROP TABLE api_platform.api_throttle_events;

CREATE TABLE api_platform.api_throttle_events (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	api_key_id uuid NULL,
	organization_id uuid NULL,
	"type" text NOT NULL,
	limit_value int4 NULL,
	actual_value int4 NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT api_throttle_events_pkey PRIMARY KEY (id)
);


-- api_platform.api_usage_counters definition

-- Drop table

-- DROP TABLE api_platform.api_usage_counters;

CREATE TABLE api_platform.api_usage_counters (
	api_key_id uuid NOT NULL,
	current_minute_count int4 NULL,
	current_day_count int4 NULL,
	current_month_count int4 NULL,
	updated_at timestamptz NOT NULL,
	CONSTRAINT api_usage_counters_pkey PRIMARY KEY (api_key_id)
);


-- api_platform.api_usage_daily definition

-- Drop table

-- DROP TABLE api_platform.api_usage_daily;

CREATE TABLE api_platform.api_usage_daily (
	api_key_id uuid NOT NULL,
	organization_id uuid NULL,
	"day" date NOT NULL,
	request_count int4 NOT NULL,
	error_count int4 NOT NULL,
	CONSTRAINT api_usage_daily_pkey PRIMARY KEY (api_key_id, day)
);


-- api_platform.api_usage_minute definition

-- Drop table

-- DROP TABLE api_platform.api_usage_minute;

CREATE TABLE api_platform.api_usage_minute (
	api_key_id uuid NOT NULL,
	organization_id uuid NULL,
	bucket timestamptz NOT NULL,
	request_count int4 NOT NULL,
	error_count int4 NOT NULL,
	sum_latency int4 NOT NULL,
	max_latency int4 NULL,
	status_2xx int4 NULL,
	status_4xx int4 NULL,
	status_5xx int4 NULL,
	CONSTRAINT api_usage_minute_pkey PRIMARY KEY (api_key_id, bucket)
);


-- api_platform.api_usage_monthly definition

-- Drop table

-- DROP TABLE api_platform.api_usage_monthly;

CREATE TABLE api_platform.api_usage_monthly (
	api_key_id uuid NOT NULL,
	organization_id uuid NULL,
	"month" date NOT NULL,
	request_count int4 NOT NULL,
	error_count int4 NOT NULL,
	CONSTRAINT api_usage_monthly_pkey PRIMARY KEY (api_key_id, month)
);


-- public.accounts definition

-- Drop table

-- DROP TABLE public.accounts;

CREATE TABLE public.accounts (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_name text NOT NULL,
	status text DEFAULT 'ACTIVE'::text NOT NULL,
	billing_email text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT accounts_pkey PRIMARY KEY (id)
);
CREATE UNIQUE INDEX uq_accounts_billing_email ON public.accounts USING btree (billing_email) WHERE (billing_email IS NOT NULL);


-- public.capabilities definition

-- Drop table

-- DROP TABLE public.capabilities;

CREATE TABLE public.capabilities (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	code text NOT NULL,
	description text NOT NULL,
	value_type text NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT capabilities_code_key UNIQUE (code),
	CONSTRAINT capabilities_pkey PRIMARY KEY (id),
	CONSTRAINT capabilities_value_type_check CHECK ((value_type = ANY (ARRAY['int'::text, 'bool'::text, 'text'::text])))
);


-- public.command_templates definition

-- Drop table

-- DROP TABLE public.command_templates;

CREATE TABLE public.command_templates (
	template_id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	payload text NOT NULL,
	description text NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT command_templates_pkey PRIMARY KEY (template_id)
);


-- public.communications_current_state definition

-- Drop table

-- DROP TABLE public.communications_current_state;

CREATE TABLE public.communications_current_state (
	device_id varchar(100) NOT NULL,
	"uuid" varchar(255) NOT NULL,
	backup_battery_voltage numeric(5, 2) NULL,
	cell_id varchar(50) NULL,
	course numeric(6, 2) NULL,
	delivery_type varchar(20) NULL,
	engine_status varchar(10) NULL,
	firmware varchar(20) NULL,
	fix_status varchar(5) NULL,
	gps_datetime timestamp NULL,
	gps_epoch int8 NULL,
	idle_time int4 NULL,
	lac varchar(10) NULL,
	latitude numeric(10, 8) NULL,
	longitude numeric(11, 8) NULL,
	main_battery_voltage numeric(5, 2) NULL,
	mcc varchar(10) NULL,
	mnc varchar(10) NULL,
	model varchar(10) NULL,
	msg_class varchar(20) NOT NULL,
	msg_counter varchar NULL,
	network_status varchar(50) NULL,
	odometer int8 NULL,
	rx_lvl int4 NULL,
	satellites int4 NULL,
	speed numeric(8, 2) NULL,
	speed_time int4 NULL,
	total_distance int8 NULL,
	trip_distance int8 NULL,
	trip_hourmeter int4 NULL,
	bytes_count int4 NULL,
	client_ip text NULL,
	client_port int4 NULL,
	decoded_epoch int8 NULL,
	received_epoch int8 NULL,
	raw_message text NULL,
	received_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	alert_type varchar NULL,
	backup_battery_percent numeric NULL,
	CONSTRAINT communications_current_state_pkey PRIMARY KEY (device_id, msg_class),
	CONSTRAINT communications_current_state_uuid_key UNIQUE (uuid)
);
CREATE INDEX idx_comm_current_decoded_epoch ON public.communications_current_state USING btree (decoded_epoch DESC);
CREATE INDEX idx_comm_current_gps_datetime ON public.communications_current_state USING btree (gps_datetime DESC);


-- public.communications_queclink definition

-- Drop table

-- DROP TABLE public.communications_queclink;

CREATE TABLE public.communications_queclink (
	id bigserial NOT NULL,
	"uuid" varchar(255) NOT NULL,
	device_id varchar(100) NOT NULL,
	backup_battery_voltage numeric(5, 2) NULL,
	cell_id varchar(50) NULL,
	course numeric(6, 2) NULL,
	delivery_type varchar(20) NULL,
	engine_status varchar(10) NULL,
	firmware varchar(20) NULL,
	fix_status varchar(5) NULL,
	gps_datetime timestamp NULL,
	gps_epoch int8 NULL,
	idle_time int4 NULL,
	lac varchar(10) NULL,
	latitude numeric(10, 8) NULL,
	longitude numeric(11, 8) NULL,
	main_battery_voltage numeric(5, 2) NULL,
	mcc varchar(10) NULL,
	mnc varchar(10) NULL,
	model varchar(10) NULL,
	msg_class varchar(20) NULL,
	msg_counter varchar NULL,
	network_status varchar(50) NULL,
	odometer int8 NULL,
	rx_lvl int4 NULL,
	satellites int4 NULL,
	speed numeric(8, 2) NULL,
	speed_time int4 NULL,
	total_distance int8 NULL,
	trip_distance int8 NULL,
	trip_hourmeter int4 NULL,
	bytes_count int4 NULL,
	client_ip text NULL,
	client_port int4 NULL,
	decoded_epoch int8 NULL,
	received_epoch int8 NULL,
	raw_message text NULL,
	received_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	alert_type varchar NULL,
	backup_battery_percent numeric NULL,
	CONSTRAINT communications_queclink_pkey PRIMARY KEY (id),
	CONSTRAINT communications_queclink_uuid_key UNIQUE (uuid)
);
CREATE INDEX idx_comm_created_at_q ON public.communications_queclink USING btree (created_at DESC);
CREATE INDEX idx_comm_decoded_epoch_q ON public.communications_queclink USING btree (decoded_epoch DESC);
CREATE INDEX idx_comm_device_created_q ON public.communications_queclink USING btree (device_id, created_at DESC);
CREATE INDEX idx_comm_device_id_q ON public.communications_queclink USING btree (device_id);
CREATE INDEX idx_comm_gps_datetime_q ON public.communications_queclink USING btree (gps_datetime DESC);
CREATE INDEX idx_comm_msg_class_q ON public.communications_queclink USING btree (msg_class);
CREATE INDEX idx_comm_received_at_q ON public.communications_queclink USING btree (received_at DESC);
CREATE INDEX idx_comm_uuid_q ON public.communications_queclink USING btree (uuid);


-- public.communications_suntech definition

-- Drop table

-- DROP TABLE public.communications_suntech;

CREATE TABLE public.communications_suntech (
	id bigserial NOT NULL,
	"uuid" varchar(255) NOT NULL,
	device_id varchar(100) NOT NULL,
	backup_battery_voltage numeric(5, 2) NULL,
	cell_id varchar(50) NULL,
	course numeric(6, 2) NULL,
	delivery_type varchar(20) NULL,
	engine_status varchar(10) NULL,
	firmware varchar(20) NULL,
	fix_status varchar(5) NULL,
	gps_datetime timestamp NULL,
	gps_epoch int8 NULL,
	idle_time int4 NULL,
	lac varchar(10) NULL,
	latitude numeric(10, 8) NULL,
	longitude numeric(11, 8) NULL,
	main_battery_voltage numeric(5, 2) NULL,
	mcc varchar(10) NULL,
	mnc varchar(10) NULL,
	model varchar(10) NULL,
	msg_class varchar(20) NULL,
	msg_counter varchar NULL,
	network_status varchar(50) NULL,
	odometer int8 NULL,
	rx_lvl int4 NULL,
	satellites int4 NULL,
	speed numeric(8, 2) NULL,
	speed_time int4 NULL,
	total_distance int8 NULL,
	trip_distance int8 NULL,
	trip_hourmeter int4 NULL,
	bytes_count int4 NULL,
	client_ip text NULL,
	client_port int4 NULL,
	decoded_epoch int8 NULL,
	received_epoch int8 NULL,
	raw_message text NULL,
	received_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
	alert_type varchar NULL,
	backup_battery_percent numeric NULL,
	CONSTRAINT communications_suntech_pkey PRIMARY KEY (id),
	CONSTRAINT communications_suntech_uuid_key UNIQUE (uuid)
);
CREATE INDEX idx_comm_created_at ON public.communications_suntech USING btree (created_at DESC);
CREATE INDEX idx_comm_decoded_epoch ON public.communications_suntech USING btree (decoded_epoch DESC);
CREATE INDEX idx_comm_device_created ON public.communications_suntech USING btree (device_id, created_at DESC);
CREATE INDEX idx_comm_device_id ON public.communications_suntech USING btree (device_id);
CREATE INDEX idx_comm_gps_datetime ON public.communications_suntech USING btree (gps_datetime DESC);
CREATE INDEX idx_comm_msg_class ON public.communications_suntech USING btree (msg_class);
CREATE INDEX idx_comm_received_at ON public.communications_suntech USING btree (received_at DESC);
CREATE INDEX idx_comm_uuid ON public.communications_suntech USING btree (uuid);


-- public.device_idle_activity definition

-- Drop table

-- DROP TABLE public.device_idle_activity;

CREATE TABLE public.device_idle_activity (
	idle_id uuid NOT NULL,
	device_id varchar NOT NULL,
	"timestamp" timestamptz NOT NULL,
	lat float8 NULL,
	lon float8 NULL,
	activity_type text NOT NULL,
	raw_code int4 NULL,
	severity int2 DEFAULT 1 NULL,
	metadata jsonb NULL,
	correlation_id uuid NOT NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT device_idle_activity_pkey PRIMARY KEY (device_id, "timestamp", idle_id)
);
CREATE INDEX device_idle_activity_timestamp_idx ON public.device_idle_activity USING btree ("timestamp" DESC);

-- Table Triggers

create trigger ts_insert_blocker before
insert
    on
    public.device_idle_activity for each row execute function _timescaledb_functions.insert_blocker();


-- public.event_types definition

-- Drop table

-- DROP TABLE public.event_types;

CREATE TABLE public.event_types (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	code text NOT NULL,
	description text NULL,
	category text NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT event_types_code_key UNIQUE (code),
	CONSTRAINT event_types_pkey PRIMARY KEY (id)
);


-- public.geofences definition

-- Drop table

-- DROP TABLE public.geofences;

CREATE TABLE public.geofences (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	organization_id uuid NOT NULL,
	created_by uuid NOT NULL,
	"name" text NOT NULL,
	description text NULL,
	is_active bool DEFAULT true NOT NULL,
	config jsonb NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT geofences_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_geofences_org ON public.geofences USING btree (organization_id);

-- Table Triggers

create trigger trg_geofences_updated_at before
update
    on
    public.geofences for each row execute function set_updated_at();


-- public.kafka_checkpoints definition

-- Drop table

-- DROP TABLE public.kafka_checkpoints;

CREATE TABLE public.kafka_checkpoints (
	topic_name text NOT NULL,
	"partition" int4 NOT NULL,
	offset_value int8 NOT NULL,
	updated_at timestamptz DEFAULT now() NULL,
	CONSTRAINT kafka_checkpoints_pkey PRIMARY KEY (topic_name, partition)
);


-- public.orders definition

-- Drop table

-- DROP TABLE public.orders;

CREATE TABLE public.orders (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	total_amount numeric(10, 2) NOT NULL,
	status text NOT NULL,
	payment_id uuid NULL,
	shipped_at timestamp NULL,
	created_at timestamp DEFAULT now() NULL,
	organization_id uuid NULL,
	CONSTRAINT orders_pkey PRIMARY KEY (id),
	CONSTRAINT orders_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'PAID'::text, 'SHIPPED'::text, 'CANCELLED'::text, 'COMPLETED'::text])))
);
CREATE INDEX idx_orders_organization_id ON public.orders USING btree (organization_id);
CREATE INDEX idx_orders_status ON public.orders USING btree (status);


-- public.payment_gateway_events definition

-- Drop table

-- DROP TABLE public.payment_gateway_events;

CREATE TABLE public.payment_gateway_events (
	gateway public.payment_gateway NOT NULL,
	external_event_id text NOT NULL,
	event_type text NOT NULL,
	event_status public.gateway_event_status DEFAULT 'processed'::gateway_event_status NOT NULL,
	payload jsonb NULL,
	error_message text NULL,
	retry_count int4 DEFAULT 0 NOT NULL,
	processed_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT pge_pkey PRIMARY KEY (gateway, external_event_id)
);
CREATE INDEX idx_pge_processed ON public.payment_gateway_events USING btree (processed_at DESC);
CREATE INDEX idx_pge_type ON public.payment_gateway_events USING btree (gateway, event_type);


-- public."plans" definition

-- Drop table

-- DROP TABLE public."plans";

CREATE TABLE public."plans" (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	description text NULL,
	price_monthly numeric(10, 2) DEFAULT 0 NOT NULL,
	price_yearly numeric(10, 2) DEFAULT 0 NOT NULL,
	created_at timestamp DEFAULT now() NULL,
	updated_at timestamp DEFAULT now() NULL,
	code text NOT NULL,
	is_active bool DEFAULT true NULL,
	product_id uuid NULL,
	"version" int4 DEFAULT 1 NOT NULL,
	CONSTRAINT plans_name_key UNIQUE (name),
	CONSTRAINT plans_pkey PRIMARY KEY (id),
	CONSTRAINT plans_unique UNIQUE (code)
);
CREATE UNIQUE INDEX uq_plan_code_version ON public.plans USING btree (code, version);


-- public.products definition

-- Drop table

-- DROP TABLE public.products;

CREATE TABLE public.products (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	code text NOT NULL,
	"name" text NOT NULL,
	description text NULL,
	is_active bool DEFAULT true NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT products_code_key UNIQUE (code),
	CONSTRAINT products_pkey PRIMARY KEY (id)
);


-- public.tax_rates definition

-- Drop table

-- DROP TABLE public.tax_rates;

CREATE TABLE public.tax_rates (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	country bpchar(2) NOT NULL,
	region text NULL,
	rate_percent numeric(6, 4) NOT NULL,
	is_inclusive bool DEFAULT false NOT NULL,
	sat_tax_key text DEFAULT '002'::text NULL,
	is_active bool DEFAULT true NOT NULL,
	valid_from date DEFAULT CURRENT_DATE NOT NULL,
	valid_until date NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT tr_pkey PRIMARY KEY (id)
);


-- public.telemetry_hourly_stats definition

-- Drop table

-- DROP TABLE public.telemetry_hourly_stats;

CREATE TABLE public.telemetry_hourly_stats (
	device_id text NOT NULL,
	bucket timestamptz NOT NULL,
	sum_speed float8 DEFAULT 0 NOT NULL,
	count_speed int4 DEFAULT 0 NOT NULL,
	max_speed float8 NULL,
	sum_main_voltage float8 DEFAULT 0 NOT NULL,
	count_main_voltage int4 DEFAULT 0 NOT NULL,
	min_main_voltage float8 NULL,
	sum_backup_voltage float8 DEFAULT 0 NOT NULL,
	count_backup_voltage int4 DEFAULT 0 NOT NULL,
	min_backup_voltage float8 NULL,
	count_alerts int4 DEFAULT 0 NOT NULL,
	count_comm_fixable int4 DEFAULT 0 NOT NULL,
	count_comm_with_fix int4 DEFAULT 0 NOT NULL,
	comm_first_id uuid NULL,
	comm_last_id uuid NULL,
	samples int4 DEFAULT 0 NOT NULL,
	min_speed float8 NULL,
	max_main_voltage float8 NULL,
	max_backup_voltage float8 NULL,
	first_odometer float8 NULL,
	last_odometer float8 NULL,
	sum_rx_lvl float8 DEFAULT 0 NOT NULL,
	count_rx_lvl int4 DEFAULT 0 NOT NULL,
	min_rx_lvl float8 NULL,
	max_rx_lvl float8 NULL,
	sum_satellites float8 DEFAULT 0 NOT NULL,
	count_satellites int4 DEFAULT 0 NOT NULL,
	min_satellites float8 NULL,
	max_satellites float8 NULL,
	CONSTRAINT telemetry_hourly_stats_pkey PRIMARY KEY (device_id, bucket)
);
CREATE INDEX idx_telemetry_device_time ON public.telemetry_hourly_stats USING btree (device_id, bucket DESC);
CREATE INDEX telemetry_hourly_stats_bucket_idx ON public.telemetry_hourly_stats USING btree (bucket DESC);

-- Table Triggers

create trigger ts_insert_blocker before
insert
    on
    public.telemetry_hourly_stats for each row execute function _timescaledb_functions.insert_blocker();


-- public.telemetry_intelligence_hourly_stats definition

-- Drop table

-- DROP TABLE public.telemetry_intelligence_hourly_stats;

CREATE TABLE public.telemetry_intelligence_hourly_stats (
	device_id text NOT NULL,
	bucket timestamptz NOT NULL,
	samples int4 DEFAULT 0 NOT NULL,
	sum_speed float8 DEFAULT 0 NOT NULL,
	count_speed int4 DEFAULT 0 NOT NULL,
	distance_km float8 DEFAULT 0 NOT NULL,
	last_lat float8 NULL,
	last_lng float8 NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	fuel_consumed_liters float8 DEFAULT 0 NOT NULL,
	moving_minutes float8 DEFAULT 0 NOT NULL,
	idle_minutes float8 DEFAULT 0 NOT NULL,
	CONSTRAINT telemetry_intelligence_hourly_stats_pkey PRIMARY KEY (device_id, bucket)
);
CREATE INDEX idx_telemetry_intelligence_bucket ON public.telemetry_intelligence_hourly_stats USING btree (bucket DESC);
CREATE INDEX idx_telemetry_intelligence_device_time ON public.telemetry_intelligence_hourly_stats USING btree (device_id, bucket DESC);
CREATE INDEX telemetry_intelligence_hourly_stats_bucket_idx ON public.telemetry_intelligence_hourly_stats USING btree (bucket DESC);

-- Table Triggers

create trigger ts_insert_blocker before
insert
    on
    public.telemetry_intelligence_hourly_stats for each row execute function _timescaledb_functions.insert_blocker();


-- public.tokens definition

-- Drop table

-- DROP TABLE public.tokens;

CREATE TABLE public.tokens (
	id uuid NOT NULL,
	"token" varchar NULL,
	revocado bool NULL,
	user_id varchar NULL,
	CONSTRAINT tokens_pkey PRIMARY KEY (id)
);


-- public.trip_alerts definition

-- Drop table

-- DROP TABLE public.trip_alerts;

CREATE TABLE public.trip_alerts (
	alert_id uuid NOT NULL,
	trip_id uuid NOT NULL,
	"timestamp" timestamptz NOT NULL,
	lat float8 NULL,
	lon float8 NULL,
	alert_type text NOT NULL,
	raw_code int4 NULL,
	severity int2 DEFAULT 1 NULL,
	metadata jsonb NULL,
	created_at timestamptz DEFAULT now() NULL,
	device_id varchar NOT NULL,
	correlation_id uuid NULL
)
PARTITION BY RANGE ("timestamp");
CREATE INDEX idx_trip_alert_device ON ONLY public.trip_alerts USING btree (device_id);
CREATE INDEX idx_trip_alert_trip ON ONLY public.trip_alerts USING btree (trip_id);
CREATE UNIQUE INDEX idx_trip_alerts_corr_unique ON ONLY public.trip_alerts USING btree (device_id, correlation_id, "timestamp");
CREATE INDEX idx_trip_alerts_device_time ON ONLY public.trip_alerts USING btree (device_id, "timestamp" DESC);
CREATE INDEX idx_trip_alerts_type ON ONLY public.trip_alerts USING btree (alert_type);


-- public.trip_current_state definition

-- Drop table

-- DROP TABLE public.trip_current_state;

CREATE TABLE public.trip_current_state (
	device_id varchar NOT NULL,
	current_trip_id uuid NULL,
	ignition_on bool DEFAULT false NOT NULL,
	last_point_at timestamptz NULL,
	last_lat float8 NULL,
	last_lng float8 NULL,
	last_speed float8 NULL,
	last_correlation_id uuid NULL,
	last_updated_at timestamptz DEFAULT now() NOT NULL,
	last_odometer_meters int4 NULL,
	CONSTRAINT trip_current_state_pkey PRIMARY KEY (device_id)
);


-- public.trip_events definition

-- Drop table

-- DROP TABLE public.trip_events;

CREATE TABLE public.trip_events (
	event_id uuid NOT NULL,
	trip_id uuid NOT NULL,
	"timestamp" timestamptz NOT NULL,
	lat float8 NULL,
	lon float8 NULL,
	event_type public.event_type_enum NOT NULL,
	"source" varchar(30) DEFAULT 'platform'::character varying NULL,
	rule_id uuid NULL,
	metadata jsonb NULL,
	created_at timestamptz DEFAULT now() NULL,
	device_id varchar NOT NULL
)
PARTITION BY RANGE ("timestamp");
CREATE INDEX idx_trip_events_device_time ON ONLY public.trip_events USING btree (device_id, "timestamp" DESC);


-- public.trip_points definition

-- Drop table

-- DROP TABLE public.trip_points;

CREATE TABLE public.trip_points (
	point_id bigserial NOT NULL,
	trip_id uuid NOT NULL,
	device_id varchar NOT NULL,
	"timestamp" timestamptz NOT NULL,
	lat float8 NOT NULL,
	lng float8 NOT NULL,
	speed float8 NULL,
	heading float8 NULL,
	correlation_id uuid NOT NULL,
	odometer_meters int4 NULL,
	CONSTRAINT trip_points_pkey PRIMARY KEY (device_id, "timestamp", correlation_id)
);
CREATE UNIQUE INDEX idx_trip_points_corr_unique ON public.trip_points USING btree (device_id, correlation_id, "timestamp");
CREATE INDEX idx_trip_points_device_time ON public.trip_points USING btree (device_id, "timestamp" DESC);
CREATE INDEX idx_trip_points_time ON public.trip_points USING btree ("timestamp" DESC);


-- public.trips definition

-- Drop table

-- DROP TABLE public.trips;

CREATE TABLE public.trips (
	trip_id uuid NOT NULL,
	device_id varchar(20) NOT NULL,
	start_time timestamptz NOT NULL,
	end_time timestamptz NULL,
	start_lat float8 NULL,
	start_lng float8 NULL,
	end_lat float8 NULL,
	end_lng float8 NULL,
	distance_meters int4 NULL,
	created_at timestamptz DEFAULT now() NULL,
	start_odometer_meters int4 NULL,
	end_odometer_meters int4 NULL,
	CONSTRAINT trips_pkey PRIMARY KEY (trip_id)
);
CREATE INDEX idx_trips_device_start ON public.trips USING btree (device_id, start_time);
CREATE INDEX idx_trips_start_ts ON public.trips USING btree (start_time);


-- public.units definition

-- Drop table

-- DROP TABLE public.units;

CREATE TABLE public.units (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	description text NULL,
	deleted_at timestamptz NULL,
	organization_id uuid NULL,
	unit_ref uuid DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT units_pkey PRIMARY KEY (id),
	CONSTRAINT uq_units_unit_ref UNIQUE (unit_ref)
);
CREATE INDEX idx_units_deleted_at ON public.units USING btree (deleted_at) WHERE (deleted_at IS NULL);
CREATE INDEX idx_units_organization_id ON public.units USING btree (organization_id);


-- public.users definition

-- Drop table

-- DROP TABLE public.users;

CREATE TABLE public.users (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	cognito_sub text NULL,
	email text NOT NULL,
	full_name text NULL,
	is_master bool DEFAULT false NULL,
	last_login_at timestamp NULL,
	created_at timestamp DEFAULT now() NULL,
	updated_at timestamp DEFAULT now() NULL,
	password_hash text DEFAULT ''::text NULL,
	email_verified bool DEFAULT false NOT NULL,
	organization_id uuid NULL,
	CONSTRAINT users_cognito_sub_key UNIQUE (cognito_sub),
	CONSTRAINT users_email_key UNIQUE (email),
	CONSTRAINT users_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_users_cognito_sub ON public.users USING btree (cognito_sub);
CREATE INDEX idx_users_org_master ON public.users USING btree (organization_id, is_master);


-- public.volume_discounts definition

-- Drop table

-- DROP TABLE public.volume_discounts;

CREATE TABLE public.volume_discounts (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	plan_id uuid NOT NULL,
	"name" text NOT NULL,
	min_units int4 NOT NULL,
	max_units int4 NULL,
	discount_type public.discount_type NOT NULL,
	percent_off numeric(5, 4) NULL,
	amount_off numeric(10, 2) NULL,
	is_active bool DEFAULT true NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT vd_pkey PRIMARY KEY (id),
	CONSTRAINT vd_range_chk CHECK (((max_units IS NULL) OR (max_units > min_units))),
	CONSTRAINT vd_value_chk CHECK ((((percent_off IS NOT NULL) AND (amount_off IS NULL)) OR ((percent_off IS NULL) AND (amount_off IS NOT NULL))))
);
CREATE INDEX idx_vd_plan ON public.volume_discounts USING btree (plan_id);


-- public.account_users definition

-- Drop table

-- DROP TABLE public.account_users;

CREATE TABLE public.account_users (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	user_id uuid NOT NULL,
	"role" text NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT account_users_account_id_user_id_key UNIQUE (account_id, user_id),
	CONSTRAINT account_users_pkey PRIMARY KEY (id),
	CONSTRAINT account_users_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT account_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);


-- public.coupons definition

-- Drop table

-- DROP TABLE public.coupons;

CREATE TABLE public.coupons (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	internal_name text NOT NULL,
	discount_type public.discount_type NOT NULL,
	amount_off numeric(10, 2) NULL,
	currency text DEFAULT 'MXN'::text NULL,
	percent_off numeric(5, 4) NULL,
	coupon_duration public.coupon_duration DEFAULT 'once'::coupon_duration NOT NULL,
	duration_in_months int4 NULL,
	max_redemptions int4 NULL,
	times_redeemed int4 DEFAULT 0 NOT NULL,
	redeem_by timestamptz NULL,
	min_amount numeric(10, 2) NULL,
	first_time_only bool DEFAULT false NOT NULL,
	applies_to_plans _uuid NULL,
	gateway public.payment_gateway NULL,
	gateway_coupon_id text NULL,
	is_active bool DEFAULT true NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_by uuid NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT cp_percent_chk CHECK (((percent_off IS NULL) OR ((percent_off > (0)::numeric) AND (percent_off <= (1)::numeric)))),
	CONSTRAINT cp_pkey PRIMARY KEY (id),
	CONSTRAINT cp_repeating_chk CHECK (((coupon_duration <> 'repeating'::coupon_duration) OR (duration_in_months IS NOT NULL))),
	CONSTRAINT cp_value_chk CHECK ((((amount_off IS NOT NULL) AND (percent_off IS NULL)) OR ((amount_off IS NULL) AND (percent_off IS NOT NULL)))),
	CONSTRAINT cp_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id)
);


-- public.events definition

-- Drop table

-- DROP TABLE public.events;

CREATE TABLE public.events (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	source_type text NOT NULL,
	source_id text NOT NULL,
	source_message_id uuid NULL,
	unit_id uuid NULL,
	event_type_id uuid NOT NULL,
	payload jsonb NULL,
	occurred_at timestamptz NOT NULL,
	received_at timestamptz DEFAULT now() NULL,
	source_epoch int8 NULL,
	CONSTRAINT events_pkey PRIMARY KEY (id),
	CONSTRAINT fk_events_event_type FOREIGN KEY (event_type_id) REFERENCES public.event_types(id) ON DELETE RESTRICT,
	CONSTRAINT fk_events_unit FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE SET NULL
);
CREATE INDEX idx_events_event_type ON public.events USING btree (event_type_id);
CREATE INDEX idx_events_occurred_at ON public.events USING btree (occurred_at DESC);
CREATE INDEX idx_events_payload_gin ON public.events USING gin (payload);
CREATE INDEX idx_events_source ON public.events USING btree (source_type, source_id, occurred_at DESC);
CREATE INDEX idx_events_unit ON public.events USING btree (unit_id, occurred_at DESC);
CREATE INDEX idx_events_unit_id ON public.events USING btree (unit_id);


-- public.fiscal_profiles definition

-- Drop table

-- DROP TABLE public.fiscal_profiles;

CREATE TABLE public.fiscal_profiles (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	rfc text NOT NULL,
	razon_social text NOT NULL,
	regimen_fiscal text NOT NULL,
	codigo_postal bpchar(5) NOT NULL,
	cfdi_use text DEFAULT 'G03'::text NOT NULL,
	is_default bool DEFAULT false NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT fsc_cp_digits CHECK ((codigo_postal ~ '^\d{5}$'::text)),
	CONSTRAINT fsc_pkey PRIMARY KEY (id),
	CONSTRAINT fsc_rfc_length CHECK ((char_length(rfc) = ANY (ARRAY[12, 13]))),
	CONSTRAINT fsc_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE
);
CREATE INDEX idx_fiscal_account ON public.fiscal_profiles USING btree (account_id);
CREATE UNIQUE INDEX uq_fiscal_default ON public.fiscal_profiles USING btree (account_id) WHERE (is_default = true);


-- public.geofence_cells definition

-- Drop table

-- DROP TABLE public.geofence_cells;

CREATE TABLE public.geofence_cells (
	geofence_id uuid NOT NULL,
	h3_index int8 NOT NULL,
	CONSTRAINT geofence_cells_pkey PRIMARY KEY (geofence_id, h3_index),
	CONSTRAINT fk_geofence_cells_geofence FOREIGN KEY (geofence_id) REFERENCES public.geofences(id) ON DELETE CASCADE
);
CREATE INDEX idx_geofence_cells_geofence ON public.geofence_cells USING btree (geofence_id);
CREATE INDEX idx_geofence_cells_h3 ON public.geofence_cells USING btree (h3_index);


-- public.invitations definition

-- Drop table

-- DROP TABLE public.invitations;

CREATE TABLE public.invitations (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	invited_email text NOT NULL,
	invited_by_user_id uuid NOT NULL,
	"token" text NOT NULL,
	expires_at timestamp NOT NULL,
	accepted bool DEFAULT false NULL,
	created_at timestamp DEFAULT now() NULL,
	organization_id uuid NULL,
	CONSTRAINT invitations_pkey PRIMARY KEY (id),
	CONSTRAINT invitations_token_key UNIQUE (token),
	CONSTRAINT invitations_invited_by_user_id_fkey FOREIGN KEY (invited_by_user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_invitations_expires_at ON public.invitations USING btree (expires_at) WHERE (accepted = false);
CREATE INDEX idx_invitations_organization_id ON public.invitations USING btree (organization_id);


-- public.organizations definition

-- Drop table

-- DROP TABLE public.organizations;

CREATE TABLE public.organizations (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	status text DEFAULT 'ACTIVE'::text NULL,
	created_at timestamp DEFAULT now() NULL,
	updated_at timestamp DEFAULT now() NULL,
	billing_email text NULL,
	country text NULL,
	timezone text DEFAULT 'UTC'::text NULL,
	metadata jsonb DEFAULT '{}'::jsonb NULL,
	account_id uuid NOT NULL,
	CONSTRAINT organizations_pkey PRIMARY KEY (id),
	CONSTRAINT organizations_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'ACTIVE'::text, 'SUSPENDED'::text, 'DELETED'::text]))),
	CONSTRAINT organizations_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE
);
CREATE INDEX idx_org_account ON public.organizations USING btree (account_id);
CREATE INDEX idx_organizations_account_id ON public.organizations USING btree (account_id);


-- public.payment_gateway_customers definition

-- Drop table

-- DROP TABLE public.payment_gateway_customers;

CREATE TABLE public.payment_gateway_customers (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	gateway public.payment_gateway NOT NULL,
	external_customer_id text NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT pgc_account_gateway_key UNIQUE (account_id, gateway),
	CONSTRAINT pgc_external_key UNIQUE (gateway, external_customer_id),
	CONSTRAINT pgc_pkey PRIMARY KEY (id),
	CONSTRAINT pgc_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE
);
CREATE INDEX idx_pgc_account ON public.payment_gateway_customers USING btree (account_id);
CREATE INDEX idx_pgc_gateway ON public.payment_gateway_customers USING btree (gateway, external_customer_id);


-- public.payment_methods definition

-- Drop table

-- DROP TABLE public.payment_methods;

CREATE TABLE public.payment_methods (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	gateway public.payment_gateway NOT NULL,
	method_type public.payment_method_type DEFAULT 'card'::payment_method_type NOT NULL,
	external_token text NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	brand text NULL,
	last4 bpchar(4) NULL,
	exp_month int2 NULL,
	exp_year int2 NULL,
	fingerprint text NULL,
	is_default bool DEFAULT false NOT NULL,
	is_active bool DEFAULT true NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT pm_exp_month_chk CHECK (((exp_month IS NULL) OR ((exp_month >= 1) AND (exp_month <= 12)))),
	CONSTRAINT pm_exp_year_chk CHECK (((exp_year IS NULL) OR (exp_year >= 2024))),
	CONSTRAINT pm_external_key UNIQUE (gateway, external_token),
	CONSTRAINT pm_pkey PRIMARY KEY (id),
	CONSTRAINT pm_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE
);
CREATE INDEX idx_pm_account ON public.payment_methods USING btree (account_id);
CREATE INDEX idx_pm_account_gateway ON public.payment_methods USING btree (account_id, gateway);
CREATE INDEX idx_pm_gateway ON public.payment_methods USING btree (gateway, external_token);
CREATE UNIQUE INDEX uq_pm_default ON public.payment_methods USING btree (account_id) WHERE (is_default = true);


-- public.plan_capabilities definition

-- Drop table

-- DROP TABLE public.plan_capabilities;

CREATE TABLE public.plan_capabilities (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	plan_id uuid NOT NULL,
	capability_id uuid NOT NULL,
	value_int int4 NULL,
	value_bool bool NULL,
	value_text text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT plan_capabilities_pkey PRIMARY KEY (id),
	CONSTRAINT plan_capabilities_plan_id_capability_id_key UNIQUE (plan_id, capability_id),
	CONSTRAINT plan_capabilities_capability_id_fkey FOREIGN KEY (capability_id) REFERENCES public.capabilities(id) ON DELETE CASCADE
);
CREATE INDEX idx_plan_capabilities_cap ON public.plan_capabilities USING btree (capability_id);
CREATE INDEX idx_plan_capabilities_plan ON public.plan_capabilities USING btree (plan_id);


-- public.promotion_codes definition

-- Drop table

-- DROP TABLE public.promotion_codes;

CREATE TABLE public.promotion_codes (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	coupon_id uuid NOT NULL,
	code text NOT NULL,
	max_redemptions int4 NULL,
	times_redeemed int4 DEFAULT 0 NOT NULL,
	expires_at timestamptz NULL,
	restricted_to_account uuid NULL,
	is_active bool DEFAULT true NOT NULL,
	gateway public.payment_gateway NULL,
	gateway_promo_id text NULL,
	created_by uuid NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT pc_code_key UNIQUE (code),
	CONSTRAINT pc_pkey PRIMARY KEY (id),
	CONSTRAINT pc_account_fkey FOREIGN KEY (restricted_to_account) REFERENCES public.accounts(id),
	CONSTRAINT pc_coupon_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id),
	CONSTRAINT pc_created_fkey FOREIGN KEY (created_by) REFERENCES public.users(id)
);
CREATE UNIQUE INDEX idx_promo_code_lower ON public.promotion_codes USING btree (lower(code));


-- public.referral_codes definition

-- Drop table

-- DROP TABLE public.referral_codes;

CREATE TABLE public.referral_codes (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	code text NOT NULL,
	max_uses int4 NULL,
	total_uses int4 DEFAULT 0 NOT NULL,
	is_active bool DEFAULT true NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT rc_account_key UNIQUE (account_id),
	CONSTRAINT rc_code_key UNIQUE (code),
	CONSTRAINT rc_pkey PRIMARY KEY (id),
	CONSTRAINT rc_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id)
);
CREATE UNIQUE INDEX idx_rc_code_lower ON public.referral_codes USING btree (lower(code));


-- public.subscriptions definition

-- Drop table

-- DROP TABLE public.subscriptions;

CREATE TABLE public.subscriptions (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	organization_id uuid NOT NULL,
	plan_id uuid NOT NULL,
	status text NOT NULL,
	started_at timestamp DEFAULT now() NOT NULL,
	expires_at timestamp NOT NULL,
	cancelled_at timestamp NULL,
	renewed_from uuid NULL,
	auto_renew bool DEFAULT true NULL,
	created_at timestamp DEFAULT now() NULL,
	updated_at timestamp DEFAULT now() NULL,
	external_id text NULL,
	billing_cycle text DEFAULT 'MONTHLY'::text NULL,
	current_period_start timestamptz NULL,
	current_period_end timestamptz NULL,
	product_id uuid NULL,
	dunning_attempt_count int4 DEFAULT 0 NOT NULL,
	dunning_last_attempt timestamptz NULL,
	dunning_next_attempt timestamptz NULL,
	active_units int4 DEFAULT 1 NOT NULL,
	credit_balance numeric(10, 2) DEFAULT 0 NOT NULL,
	paused_at timestamptz NULL,
	resumes_at timestamptz NULL,
	pause_reason text NULL,
	CONSTRAINT subscriptions_pkey PRIMARY KEY (id),
	CONSTRAINT subscriptions_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'CANCELLED'::text, 'EXPIRED'::text, 'TRIAL'::text]))),
	CONSTRAINT subscriptions_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id),
	CONSTRAINT subscriptions_renewed_from_fkey FOREIGN KEY (renewed_from) REFERENCES public.subscriptions(id) ON DELETE SET NULL
);
CREATE INDEX idx_sub_external ON public.subscriptions USING btree (external_id) WHERE (external_id IS NOT NULL);
CREATE INDEX idx_subscriptions_client ON public.subscriptions USING btree (organization_id);
CREATE INDEX idx_subscriptions_organization_id ON public.subscriptions USING btree (organization_id);
CREATE INDEX idx_subscriptions_status ON public.subscriptions USING btree (status);


-- public.tokens_confirmacion definition

-- Drop table

-- DROP TABLE public.tokens_confirmacion;

CREATE TABLE public.tokens_confirmacion (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	"token" varchar NOT NULL,
	expires_at timestamp DEFAULT (now() + '01:00:00'::interval) NOT NULL,
	used bool DEFAULT false NOT NULL,
	"type" varchar DEFAULT 'email_verification'::character varying NOT NULL,
	user_id uuid NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	email varchar(255) NULL,
	full_name varchar(255) NULL,
	password_temp varchar(255) NULL,
	organization_id uuid NULL,
	CONSTRAINT tokens_confirmacion_pkey PRIMARY KEY (id),
	CONSTRAINT tokens_confirmacion_token_key UNIQUE (token),
	CONSTRAINT tokens_confirmacion_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_tokens_confirmacion_org_id ON public.tokens_confirmacion USING btree (organization_id);
CREATE INDEX idx_tokens_confirmacion_token ON public.tokens_confirmacion USING btree (token);


-- public.trials definition

-- Drop table

-- DROP TABLE public.trials;

CREATE TABLE public.trials (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	subscription_id uuid NOT NULL,
	organization_id uuid NOT NULL,
	trial_type text DEFAULT 'free'::text NOT NULL,
	trial_starts_at timestamptz DEFAULT now() NOT NULL,
	trial_ends_at timestamptz NOT NULL,
	trial_amount numeric(10, 2) DEFAULT 0 NULL,
	trial_currency text DEFAULT 'MXN'::text NULL,
	requires_payment_method bool DEFAULT false NOT NULL,
	end_behavior text DEFAULT 'convert'::text NOT NULL,
	extension_count int4 DEFAULT 0 NOT NULL,
	last_extended_by uuid NULL,
	last_extended_at timestamptz NULL,
	extension_reason text NULL,
	reminder_3d_sent_at timestamptz NULL,
	reminder_1d_sent_at timestamptz NULL,
	converted_at timestamptz NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT tri_pkey PRIMARY KEY (id),
	CONSTRAINT tri_sub_key UNIQUE (subscription_id),
	CONSTRAINT tri_ext_fkey FOREIGN KEY (last_extended_by) REFERENCES public.users(id),
	CONSTRAINT tri_org_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id),
	CONSTRAINT tri_sub_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscriptions(id)
);
CREATE INDEX idx_tri_ends ON public.trials USING btree (trial_ends_at) WHERE (converted_at IS NULL);
CREATE INDEX idx_tri_org ON public.trials USING btree (organization_id);


-- public.trip_stats definition

-- Drop table

-- DROP TABLE public.trip_stats;

CREATE TABLE public.trip_stats (
	trip_id uuid NOT NULL,
	point_count int4 NULL,
	alert_count int4 NULL,
	event_count int4 NULL,
	avg_speed float4 NULL,
	max_speed float4 NULL,
	distance_meters int4 NULL,
	driving_score float4 NULL,
	harsh_accel_count int4 NULL,
	harsh_brake_count int4 NULL,
	idle_time_seconds int4 NULL,
	overspeed_segments int4 NULL,
	created_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz DEFAULT now() NULL,
	CONSTRAINT trip_stats_pkey PRIMARY KEY (trip_id),
	CONSTRAINT trip_stats_trip_id_fkey FOREIGN KEY (trip_id) REFERENCES public.trips(trip_id)
);


-- public.unit_fuel_profile definition

-- Drop table

-- DROP TABLE public.unit_fuel_profile;

CREATE TABLE public.unit_fuel_profile (
	profile_id uuid DEFAULT gen_random_uuid() NOT NULL,
	unit_id uuid NOT NULL,
	fuel_type public.fuel_type_t DEFAULT 'UNKNOWN'::text NOT NULL,
	vehicle_class public.vehicle_class_t DEFAULT 'UNKNOWN'::text NOT NULL,
	estimation_method public.fuel_estimation_method_t DEFAULT 'DISTANCE_PROFILE'::text NOT NULL,
	km_per_liter numeric(8, 2) NULL,
	idle_liters_per_hour numeric(8, 2) NULL,
	min_movement_meters int4 DEFAULT 100 NOT NULL,
	min_speed_kph numeric(6, 2) DEFAULT 2.0 NOT NULL,
	traffic_penalty_factor numeric(6, 3) DEFAULT 1.20 NOT NULL,
	highway_penalty_factor numeric(6, 3) DEFAULT 1.10 NOT NULL,
	confidence_base numeric(4, 3) DEFAULT 0.55 NOT NULL,
	is_custom bool DEFAULT false NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT unit_fuel_profile_pkey PRIMARY KEY (profile_id),
	CONSTRAINT unit_fuel_profile_unit_id_key UNIQUE (unit_id),
	CONSTRAINT unit_fuel_profile_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE CASCADE
);
CREATE INDEX idx_unit_fuel_profile_unit_id ON public.unit_fuel_profile USING btree (unit_id);

-- Table Triggers

create trigger trg_unit_fuel_profile_updated_at before
update
    on
    public.unit_fuel_profile for each row execute function update_updated_at_column();


-- public.unit_profile definition

-- Drop table

-- DROP TABLE public.unit_profile;

CREATE TABLE public.unit_profile (
	profile_id uuid DEFAULT gen_random_uuid() NOT NULL,
	unit_id uuid NOT NULL,
	unit_type text NOT NULL,
	icon_type text NULL,
	description text NULL,
	brand text NULL,
	model text NULL,
	serial text NULL,
	color text NULL,
	"year" int4 NULL,
	created_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz DEFAULT now() NULL,
	CONSTRAINT unit_profile_pkey PRIMARY KEY (profile_id),
	CONSTRAINT unit_profile_unit_id_key UNIQUE (unit_id),
	CONSTRAINT fk_unit_profile_unit FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE CASCADE
);
CREATE INDEX idx_unit_profile_type ON public.unit_profile USING btree (unit_type);


-- public.usage_events definition

-- Drop table

-- DROP TABLE public.usage_events;

CREATE TABLE public.usage_events (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	organization_id uuid NOT NULL,
	subscription_id uuid NOT NULL,
	metric_name text NOT NULL,
	quantity numeric(14, 4) DEFAULT 1 NOT NULL,
	unit_label text NULL,
	period_start timestamptz NOT NULL,
	period_end timestamptz NOT NULL,
	resource_id uuid NULL,
	resource_type text NULL,
	idempotency_key text NULL,
	recorded_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT ue_idem_key UNIQUE (idempotency_key),
	CONSTRAINT ue_pkey PRIMARY KEY (id),
	CONSTRAINT ue_org_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id),
	CONSTRAINT ue_sub_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscriptions(id)
);
CREATE INDEX idx_ue_org_metric ON public.usage_events USING btree (organization_id, metric_name, period_start);
CREATE INDEX idx_ue_sub ON public.usage_events USING btree (subscription_id, period_start);


-- public.user_devices definition

-- Drop table

-- DROP TABLE public.user_devices;

CREATE TABLE public.user_devices (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	user_id uuid NOT NULL,
	device_token text NOT NULL,
	platform text NOT NULL,
	endpoint_arn text NULL,
	is_active bool DEFAULT true NULL,
	last_seen_at timestamptz DEFAULT now() NULL,
	created_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz DEFAULT now() NULL,
	CONSTRAINT user_devices_pkey PRIMARY KEY (id),
	CONSTRAINT fk_user_devices_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_devices_active ON public.user_devices USING btree (is_active);
CREATE INDEX idx_user_devices_last_seen ON public.user_devices USING btree (last_seen_at);
CREATE INDEX idx_user_devices_user ON public.user_devices USING btree (user_id);
CREATE UNIQUE INDEX uq_user_devices_token ON public.user_devices USING btree (device_token);


-- public.user_units definition

-- Drop table

-- DROP TABLE public.user_units;

CREATE TABLE public.user_units (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	user_id uuid NOT NULL,
	unit_id uuid NOT NULL,
	granted_by uuid NULL,
	granted_at timestamptz DEFAULT now() NULL,
	"role" text DEFAULT 'viewer'::text NOT NULL,
	CONSTRAINT check_user_units_role CHECK ((role = ANY (ARRAY['viewer'::text, 'editor'::text, 'admin'::text]))),
	CONSTRAINT uq_user_units_user_unit UNIQUE (user_id, unit_id),
	CONSTRAINT user_units_pkey PRIMARY KEY (id),
	CONSTRAINT user_units_granted_by_fkey FOREIGN KEY (granted_by) REFERENCES public.users(id) ON DELETE SET NULL,
	CONSTRAINT user_units_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE CASCADE,
	CONSTRAINT user_units_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_units_role ON public.user_units USING btree (role);
CREATE INDEX idx_user_units_unit_id ON public.user_units USING btree (unit_id);
CREATE INDEX idx_user_units_user_id ON public.user_units USING btree (user_id);


-- public.vehicle_profile definition

-- Drop table

-- DROP TABLE public.vehicle_profile;

CREATE TABLE public.vehicle_profile (
	unit_id uuid NOT NULL,
	plate text NULL,
	vin text NULL,
	fuel_type text NULL,
	passengers int4 NULL,
	created_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz DEFAULT now() NULL,
	CONSTRAINT vehicle_profile_pkey PRIMARY KEY (unit_id),
	CONSTRAINT fk_vehicle_unit FOREIGN KEY (unit_id) REFERENCES public.unit_profile(unit_id) ON DELETE CASCADE
);
CREATE INDEX idx_vehicle_plate ON public.vehicle_profile USING btree (plate);


-- api_platform.api_keys definition

-- Drop table

-- DROP TABLE api_platform.api_keys;

CREATE TABLE api_platform.api_keys (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	organization_id uuid NOT NULL,
	product_id uuid NOT NULL,
	"name" text NOT NULL,
	key_hash text NOT NULL,
	prefix text NOT NULL,
	status text DEFAULT 'ACTIVE'::text NOT NULL,
	created_at timestamptz DEFAULT now() NULL,
	last_used_at timestamptz NULL,
	expires_at timestamptz NULL,
	revoked_at timestamptz NULL,
	metadata jsonb DEFAULT '{}'::jsonb NULL,
	CONSTRAINT api_keys_key_hash_key UNIQUE (key_hash),
	CONSTRAINT api_keys_pkey PRIMARY KEY (id),
	CONSTRAINT api_keys_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'REVOKED'::text, 'EXPIRED'::text]))),
	CONSTRAINT api_keys_org_fk FOREIGN KEY (organization_id) REFERENCES public.organizations(id),
	CONSTRAINT api_keys_product_fk FOREIGN KEY (product_id) REFERENCES public.products(id)
);


-- public.account_events definition

-- Drop table

-- DROP TABLE public.account_events;

CREATE TABLE public.account_events (
	id uuid NOT NULL,
	account_id uuid NOT NULL,
	organization_id uuid NULL,
	actor_user_id uuid NULL,
	actor_type text NOT NULL,
	event_type text NOT NULL,
	target_type text NOT NULL,
	target_id uuid NULL,
	metadata jsonb NULL,
	ip_address inet NULL,
	user_agent text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT account_events_pkey PRIMARY KEY (id),
	CONSTRAINT account_events_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT account_events_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id),
	CONSTRAINT account_events_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id)
);
CREATE INDEX idx_account_events_account ON public.account_events USING btree (account_id, created_at DESC);
CREATE INDEX idx_account_events_org ON public.account_events USING btree (organization_id, created_at DESC);
CREATE INDEX idx_account_events_type ON public.account_events USING btree (event_type);


-- public.alert_rules definition

-- Drop table

-- DROP TABLE public.alert_rules;

CREATE TABLE public.alert_rules (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	organization_id uuid NOT NULL,
	created_by uuid NOT NULL,
	"name" text NOT NULL,
	"type" text NOT NULL,
	config jsonb NOT NULL,
	is_active bool DEFAULT true NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	fingerprint text NOT NULL,
	CONSTRAINT alert_rules_pkey PRIMARY KEY (id),
	CONSTRAINT fk_alert_rules_org FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE,
	CONSTRAINT fk_alert_rules_user FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL
);
CREATE INDEX idx_alert_rules_org_active ON public.alert_rules USING btree (organization_id, is_active);
CREATE UNIQUE INDEX uniq_alert_rules_fingerprint ON public.alert_rules USING btree (fingerprint) WHERE (is_active = true);


-- public.alerts definition

-- Drop table

-- DROP TABLE public.alerts;

CREATE TABLE public.alerts (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	organization_id uuid NOT NULL,
	rule_id uuid NULL,
	unit_id uuid NOT NULL,
	source_type text NOT NULL,
	source_id text NULL,
	"type" text NOT NULL,
	payload jsonb NULL,
	occurred_at timestamptz NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT alerts_pkey PRIMARY KEY (id),
	CONSTRAINT fk_alerts_org FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE,
	CONSTRAINT fk_alerts_rule FOREIGN KEY (rule_id) REFERENCES public.alert_rules(id) ON DELETE SET NULL,
	CONSTRAINT fk_alerts_unit FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE CASCADE
);
CREATE INDEX idx_alerts_org_time ON public.alerts USING btree (organization_id, occurred_at DESC);
CREATE INDEX idx_alerts_org_unit_time ON public.alerts USING btree (organization_id, unit_id, occurred_at DESC);


-- public.devices definition

-- Drop table

-- DROP TABLE public.devices;

CREATE TABLE public.devices (
	device_id text NOT NULL,
	brand text NULL,
	model text NULL,
	firmware_version text NULL,
	status text DEFAULT 'nuevo'::text NOT NULL,
	last_comm_at timestamptz NULL,
	created_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz DEFAULT now() NULL,
	last_assignment_at timestamptz NULL,
	notes text NULL,
	organization_id uuid NULL,
	device_ref uuid DEFAULT gen_random_uuid() NOT NULL,
	CONSTRAINT devices_pkey PRIMARY KEY (device_id),
	CONSTRAINT devices_status_check CHECK ((status = ANY (ARRAY['nuevo'::text, 'preparado'::text, 'enviado'::text, 'entregado'::text, 'asignado'::text, 'devuelto'::text, 'inactivo'::text]))),
	CONSTRAINT uq_devices_device_ref UNIQUE (device_ref),
	CONSTRAINT devices_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id)
);
CREATE INDEX idx_devices_brand_model ON public.devices USING btree (brand, model);
CREATE INDEX idx_devices_organization_id ON public.devices USING btree (organization_id);
CREATE INDEX idx_devices_status ON public.devices USING btree (status);


-- public.invoices definition

-- Drop table

-- DROP TABLE public.invoices;

CREATE TABLE public.invoices (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	organization_id uuid NOT NULL,
	subscription_id uuid NULL,
	gateway public.payment_gateway NULL,
	external_invoice_id text NULL,
	invoice_number text NOT NULL,
	invoice_status public.invoice_status DEFAULT 'DRAFT'::invoice_status NOT NULL,
	subtotal numeric(10, 2) NOT NULL,
	discount_amount numeric(10, 2) DEFAULT 0 NOT NULL,
	tax_amount numeric(10, 2) DEFAULT 0 NOT NULL,
	total_amount numeric(10, 2) NOT NULL,
	currency text DEFAULT 'MXN'::text NOT NULL,
	period_start timestamptz NULL,
	period_end timestamptz NULL,
	due_at timestamptz NULL,
	paid_at timestamptz NULL,
	voided_at timestamptz NULL,
	invoice_pdf_url text NULL,
	fiscal_profile_id uuid NULL,
	receiver_rfc text NULL,
	receiver_razon_social text NULL,
	receiver_regimen text NULL,
	receiver_cp bpchar(5) NULL,
	cfdi_use text NULL,
	cfdi_payment_form text NULL,
	cfdi_payment_method text DEFAULT 'PUE'::text NULL,
	cfdi_uuid text NULL,
	cfdi_xml_url text NULL,
	cfdi_pdf_url text NULL,
	cfdi_stamped_at timestamptz NULL,
	provider_response jsonb NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT inv_cfdi_uuid_key UNIQUE (cfdi_uuid),
	CONSTRAINT inv_number_key UNIQUE (invoice_number),
	CONSTRAINT inv_pkey PRIMARY KEY (id),
	CONSTRAINT inv_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT inv_fiscal_fkey FOREIGN KEY (fiscal_profile_id) REFERENCES public.fiscal_profiles(id),
	CONSTRAINT inv_org_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id),
	CONSTRAINT inv_sub_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscriptions(id)
);
CREATE INDEX idx_inv_account ON public.invoices USING btree (account_id);
CREATE INDEX idx_inv_cfdi ON public.invoices USING btree (cfdi_uuid) WHERE (cfdi_uuid IS NOT NULL);
CREATE INDEX idx_inv_due_open ON public.invoices USING btree (due_at) WHERE (invoice_status = 'OPEN'::invoice_status);
CREATE INDEX idx_inv_org ON public.invoices USING btree (organization_id);
CREATE INDEX idx_inv_status ON public.invoices USING btree (invoice_status);
CREATE INDEX idx_inv_sub ON public.invoices USING btree (subscription_id);


-- public.order_items definition

-- Drop table

-- DROP TABLE public.order_items;

CREATE TABLE public.order_items (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	order_id uuid NOT NULL,
	device_id text NULL,
	item_type text NULL,
	description text NULL,
	quantity int4 DEFAULT 1 NOT NULL,
	unit_price numeric(10, 2) NOT NULL,
	total_price numeric(10, 2) GENERATED ALWAYS AS ((quantity::numeric * unit_price)) STORED NULL,
	CONSTRAINT order_items_item_type_check CHECK ((item_type = ANY (ARRAY['DEVICE'::text, 'ACCESSORY'::text, 'SERVICE'::text]))),
	CONSTRAINT order_items_pkey PRIMARY KEY (id),
	CONSTRAINT order_items_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id) ON DELETE SET NULL,
	CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE
);
CREATE INDEX idx_order_items_order ON public.order_items USING btree (order_id);


-- public.organization_capabilities definition

-- Drop table

-- DROP TABLE public.organization_capabilities;

CREATE TABLE public.organization_capabilities (
	id uuid NOT NULL,
	organization_id uuid NOT NULL,
	capability_id uuid NOT NULL,
	value_int int4 NULL,
	value_bool bool NULL,
	value_text text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT organization_capabilities_organization_id_capability_id_key UNIQUE (organization_id, capability_id),
	CONSTRAINT organization_capabilities_pkey PRIMARY KEY (id),
	CONSTRAINT organization_capabilities_capability_id_fkey FOREIGN KEY (capability_id) REFERENCES public.capabilities(id),
	CONSTRAINT organization_capabilities_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id)
);


-- public.organization_users definition

-- Drop table

-- DROP TABLE public.organization_users;

CREATE TABLE public.organization_users (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	organization_id uuid NOT NULL,
	user_id uuid NOT NULL,
	"role" text DEFAULT 'member'::text NOT NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT org_user_role_check CHECK ((role = ANY (ARRAY['owner'::text, 'admin'::text, 'billing'::text, 'member'::text]))),
	CONSTRAINT organization_users_pkey PRIMARY KEY (id),
	CONSTRAINT uq_org_user UNIQUE (organization_id, user_id),
	CONSTRAINT organization_users_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE,
	CONSTRAINT organization_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);


-- public.payments definition

-- Drop table

-- DROP TABLE public.payments;

CREATE TABLE public.payments (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	invoice_id uuid NOT NULL,
	account_id uuid NOT NULL,
	organization_id uuid NOT NULL,
	gateway public.payment_gateway NOT NULL,
	gateway_payment_id text NULL,
	idempotency_key text NULL,
	payment_method_type public.payment_method_type NOT NULL,
	payment_method_id uuid NULL,
	payment_method_meta jsonb DEFAULT '{}'::jsonb NOT NULL,
	amount numeric(10, 2) NOT NULL,
	currency text DEFAULT 'MXN'::text NOT NULL,
	refunded_amount numeric(10, 2) DEFAULT 0 NOT NULL,
	installments int4 NULL,
	installment_amount numeric(10, 2) NULL,
	payment_status public.payment_status DEFAULT 'PENDING'::payment_status NOT NULL,
	authorized_at timestamptz NULL,
	captured_at timestamptz NULL,
	initiated_at timestamptz NULL,
	succeeded_at timestamptz NULL,
	failed_at timestamptz NULL,
	canceled_at timestamptz NULL,
	refunded_at timestamptz NULL,
	failure_code text NULL,
	failure_message text NULL,
	is_disputed bool DEFAULT false NOT NULL,
	dispute_id text NULL,
	dispute_reason text NULL,
	dispute_status text NULL,
	dispute_due_at timestamptz NULL,
	dispute_resolved_at timestamptz NULL,
	risk_score int4 NULL,
	risk_level text NULL,
	client_ip inet NULL,
	device_session_id text NULL,
	provider_response jsonb NULL,
	registered_by uuid NULL,
	registration_notes text NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT pay_installments_chk CHECK ((((installments IS NULL) AND (installment_amount IS NULL)) OR ((installments IS NOT NULL) AND (installment_amount IS NOT NULL)))),
	CONSTRAINT pay_manual_chk CHECK (((gateway <> 'manual'::payment_gateway) OR (registered_by IS NOT NULL))),
	CONSTRAINT pay_pkey PRIMARY KEY (id),
	CONSTRAINT pay_refunded_chk CHECK (((refunded_amount >= (0)::numeric) AND (refunded_amount <= amount))),
	CONSTRAINT pay_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT pay_invoice_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id),
	CONSTRAINT pay_method_fkey FOREIGN KEY (payment_method_id) REFERENCES public.payment_methods(id) ON DELETE SET NULL,
	CONSTRAINT pay_org_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id),
	CONSTRAINT pay_registered_by_fkey FOREIGN KEY (registered_by) REFERENCES public.users(id)
);
CREATE INDEX idx_pay_account ON public.payments USING btree (account_id);
CREATE INDEX idx_pay_disputed ON public.payments USING btree (is_disputed) WHERE (is_disputed = true);
CREATE UNIQUE INDEX idx_pay_gateway_id ON public.payments USING btree (gateway_payment_id) WHERE (gateway_payment_id IS NOT NULL);
CREATE UNIQUE INDEX idx_pay_idempotency ON public.payments USING btree (idempotency_key) WHERE (idempotency_key IS NOT NULL);
CREATE INDEX idx_pay_invoice ON public.payments USING btree (invoice_id);
CREATE INDEX idx_pay_method ON public.payments USING btree (payment_method_id) WHERE (payment_method_id IS NOT NULL);
CREATE INDEX idx_pay_status ON public.payments USING btree (payment_status);


-- public.referral_rewards definition

-- Drop table

-- DROP TABLE public.referral_rewards;

CREATE TABLE public.referral_rewards (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	referrer_account_id uuid NOT NULL,
	referral_code_id uuid NOT NULL,
	referred_account_id uuid NOT NULL,
	referrer_reward_type text NOT NULL,
	referrer_reward_value numeric(10, 2) NOT NULL,
	referrer_coupon_id uuid NULL,
	referred_reward_type text NOT NULL,
	referred_reward_value numeric(10, 2) NOT NULL,
	referred_coupon_id uuid NULL,
	reward_status text DEFAULT 'PENDING'::text NOT NULL,
	qualifying_payment_id uuid NULL,
	earned_at timestamptz NULL,
	applied_at timestamptz NULL,
	expires_at timestamptz NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT rr_pkey PRIMARY KEY (id),
	CONSTRAINT rr_code_fkey FOREIGN KEY (referral_code_id) REFERENCES public.referral_codes(id),
	CONSTRAINT rr_payment_fkey FOREIGN KEY (qualifying_payment_id) REFERENCES public.payments(id),
	CONSTRAINT rr_red_coupon_fkey FOREIGN KEY (referred_coupon_id) REFERENCES public.coupons(id),
	CONSTRAINT rr_ref_coupon_fkey FOREIGN KEY (referrer_coupon_id) REFERENCES public.coupons(id),
	CONSTRAINT rr_referred_fkey FOREIGN KEY (referred_account_id) REFERENCES public.accounts(id),
	CONSTRAINT rr_referrer_fkey FOREIGN KEY (referrer_account_id) REFERENCES public.accounts(id)
);
CREATE INDEX idx_rr_referred ON public.referral_rewards USING btree (referred_account_id);
CREATE INDEX idx_rr_referrer ON public.referral_rewards USING btree (referrer_account_id);


-- public.refunds definition

-- Drop table

-- DROP TABLE public.refunds;

CREATE TABLE public.refunds (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	payment_id uuid NOT NULL,
	account_id uuid NOT NULL,
	gateway_refund_id text NULL,
	refund_amount numeric(10, 2) NOT NULL,
	currency text DEFAULT 'MXN'::text NOT NULL,
	reason text DEFAULT 'requested_by_customer'::text NOT NULL,
	refund_status text DEFAULT 'PENDING'::text NOT NULL,
	authorized_by uuid NOT NULL,
	notes text NULL,
	provider_response jsonb NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT ref_amount_chk CHECK ((refund_amount > (0)::numeric)),
	CONSTRAINT ref_pkey PRIMARY KEY (id),
	CONSTRAINT pay_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT ref_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT ref_auth_by_fkey FOREIGN KEY (authorized_by) REFERENCES public.users(id),
	CONSTRAINT ref_payment_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id)
);
CREATE INDEX idx_ref_account ON public.refunds USING btree (account_id);
CREATE INDEX idx_ref_payment ON public.refunds USING btree (payment_id);


-- public.sim_cards definition

-- Drop table

-- DROP TABLE public.sim_cards;

CREATE TABLE public.sim_cards (
	sim_id uuid DEFAULT gen_random_uuid() NOT NULL,
	device_id text NULL,
	carrier text DEFAULT 'KORE'::text NOT NULL,
	iccid varchar NOT NULL,
	imsi varchar NULL,
	msisdn varchar NULL,
	status text DEFAULT 'active'::text NOT NULL,
	metadata jsonb NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT sim_cards_pkey PRIMARY KEY (sim_id),
	CONSTRAINT unique_active_sim_per_device UNIQUE (device_id) DEFERRABLE,
	CONSTRAINT sim_cards_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id)
);
CREATE INDEX idx_sim_cards_device ON public.sim_cards USING btree (device_id);
CREATE INDEX idx_sim_cards_iccid ON public.sim_cards USING btree (iccid);


-- public.sim_kore_profiles definition

-- Drop table

-- DROP TABLE public.sim_kore_profiles;

CREATE TABLE public.sim_kore_profiles (
	sim_id uuid NOT NULL,
	kore_sim_id text NOT NULL,
	kore_account_id text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NULL,
	CONSTRAINT sim_kore_profiles_pkey PRIMARY KEY (sim_id),
	CONSTRAINT sim_kore_profiles_sim_id_fkey FOREIGN KEY (sim_id) REFERENCES public.sim_cards(sim_id)
);


-- public.subscription_plan_changes definition

-- Drop table

-- DROP TABLE public.subscription_plan_changes;

CREATE TABLE public.subscription_plan_changes (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	subscription_id uuid NOT NULL,
	previous_plan_id uuid NOT NULL,
	new_plan_id uuid NOT NULL,
	change_type text NOT NULL,
	proration_amount numeric(10, 2) NULL,
	proration_invoice_id uuid NULL,
	effective_at timestamptz DEFAULT now() NOT NULL,
	changed_by uuid NULL,
	notes text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT spc_pkey PRIMARY KEY (id),
	CONSTRAINT spc_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id),
	CONSTRAINT spc_inv_fkey FOREIGN KEY (proration_invoice_id) REFERENCES public.invoices(id),
	CONSTRAINT spc_sub_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscriptions(id)
);
CREATE INDEX idx_spc_sub ON public.subscription_plan_changes USING btree (subscription_id);


-- public.support_billing_cases definition

-- Drop table

-- DROP TABLE public.support_billing_cases;

CREATE TABLE public.support_billing_cases (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	payment_id uuid NULL,
	invoice_id uuid NULL,
	reason text NOT NULL,
	description text NOT NULL,
	case_status text DEFAULT 'open'::text NOT NULL,
	assigned_to uuid NULL,
	resolution text NULL,
	resolved_at timestamptz NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT sbc_pkey PRIMARY KEY (id),
	CONSTRAINT sbc_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT sbc_assigned_fkey FOREIGN KEY (assigned_to) REFERENCES public.users(id),
	CONSTRAINT sbc_invoice_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id),
	CONSTRAINT sbc_payment_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id)
);
CREATE INDEX idx_sbc_account ON public.support_billing_cases USING btree (account_id);
CREATE INDEX idx_sbc_status ON public.support_billing_cases USING btree (case_status);


-- public.unit_devices definition

-- Drop table

-- DROP TABLE public.unit_devices;

CREATE TABLE public.unit_devices (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	unit_id uuid NOT NULL,
	device_id text NOT NULL,
	assigned_at timestamptz DEFAULT now() NULL,
	unassigned_at timestamptz NULL,
	is_active bool GENERATED ALWAYS AS (unassigned_at IS NULL) STORED NULL,
	CONSTRAINT unit_devices_pkey PRIMARY KEY (id),
	CONSTRAINT uq_unit_devices_unit_device UNIQUE (unit_id, device_id),
	CONSTRAINT unit_devices_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id) ON DELETE CASCADE,
	CONSTRAINT unit_devices_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE CASCADE
);
CREATE INDEX idx_unit_devices_active_lookup ON public.unit_devices USING btree (device_id) WHERE (unassigned_at IS NULL);
CREATE INDEX idx_unit_devices_device_id ON public.unit_devices USING btree (device_id);
CREATE INDEX idx_unit_devices_is_active ON public.unit_devices USING btree (is_active);
CREATE INDEX idx_unit_devices_unit_id ON public.unit_devices USING btree (unit_id);


-- public.alert_rule_units definition

-- Drop table

-- DROP TABLE public.alert_rule_units;

CREATE TABLE public.alert_rule_units (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	rule_id uuid NOT NULL,
	unit_id uuid NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT alert_rule_units_pkey PRIMARY KEY (id),
	CONSTRAINT uq_rule_unit UNIQUE (rule_id, unit_id),
	CONSTRAINT fk_rule_units_rule FOREIGN KEY (rule_id) REFERENCES public.alert_rules(id) ON DELETE CASCADE,
	CONSTRAINT fk_rule_units_unit FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE CASCADE
);
CREATE INDEX idx_rule_units_unit ON public.alert_rule_units USING btree (unit_id);


-- public.billing_notifications definition

-- Drop table

-- DROP TABLE public.billing_notifications;

CREATE TABLE public.billing_notifications (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	organization_id uuid NULL,
	invoice_id uuid NULL,
	payment_id uuid NULL,
	notification_type text NOT NULL,
	channel text NOT NULL,
	recipient text NOT NULL,
	delivery_status text DEFAULT 'PENDING'::text NOT NULL,
	sent_at timestamptz NULL,
	delivered_at timestamptz NULL,
	failed_at timestamptz NULL,
	failure_reason text NULL,
	provider_message_id text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT bn_pkey PRIMARY KEY (id),
	CONSTRAINT bn_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT bn_invoice_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id),
	CONSTRAINT bn_org_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id),
	CONSTRAINT bn_payment_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id)
);
CREATE INDEX idx_bn_account ON public.billing_notifications USING btree (account_id);
CREATE INDEX idx_bn_invoice ON public.billing_notifications USING btree (invoice_id);
CREATE INDEX idx_bn_type ON public.billing_notifications USING btree (notification_type, sent_at);


-- public.commands definition

-- Drop table

-- DROP TABLE public.commands;

CREATE TABLE public.commands (
	command_id uuid DEFAULT gen_random_uuid() NOT NULL,
	template_id uuid NULL,
	command text NOT NULL,
	media text NOT NULL,
	request_user_id uuid NULL,
	request_user_email text NOT NULL,
	device_id text NOT NULL,
	requested_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz DEFAULT now() NULL,
	status text DEFAULT 'pending'::text NOT NULL,
	metadata jsonb NULL,
	CONSTRAINT commands_pkey PRIMARY KEY (command_id),
	CONSTRAINT commands_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id),
	CONSTRAINT commands_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.command_templates(template_id)
);


-- public.credits definition

-- Drop table

-- DROP TABLE public.credits;

CREATE TABLE public.credits (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	credit_source text NOT NULL,
	amount numeric(10, 2) NOT NULL,
	currency text DEFAULT 'MXN'::text NOT NULL,
	remaining_amount numeric(10, 2) NOT NULL,
	expires_at timestamptz NULL,
	referral_reward_id uuid NULL,
	payment_id uuid NULL,
	notes text NULL,
	created_by uuid NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT cre_amount_chk CHECK ((amount > (0)::numeric)),
	CONSTRAINT cre_pkey PRIMARY KEY (id),
	CONSTRAINT cre_remaining_chk CHECK (((remaining_amount >= (0)::numeric) AND (remaining_amount <= amount))),
	CONSTRAINT cre_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT cre_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id),
	CONSTRAINT cre_payment_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id),
	CONSTRAINT cre_reward_fkey FOREIGN KEY (referral_reward_id) REFERENCES public.referral_rewards(id)
);
CREATE INDEX idx_cre_account ON public.credits USING btree (account_id);
CREATE INDEX idx_cre_active ON public.credits USING btree (account_id, remaining_amount) WHERE (remaining_amount > (0)::numeric);


-- public.device_events definition

-- Drop table

-- DROP TABLE public.device_events;

CREATE TABLE public.device_events (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	device_id text NOT NULL,
	event_type text NOT NULL,
	old_status text NULL,
	new_status text NULL,
	performed_by uuid NULL,
	event_details text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT check_event_type CHECK ((event_type = ANY (ARRAY['creado'::text, 'preparado'::text, 'enviado'::text, 'entregado'::text, 'asignado'::text, 'devuelto'::text, 'firmware_actualizado'::text, 'nota'::text, 'estado_cambiado'::text]))),
	CONSTRAINT device_events_pkey PRIMARY KEY (id),
	CONSTRAINT device_events_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id) ON DELETE CASCADE,
	CONSTRAINT device_events_performed_by_fkey FOREIGN KEY (performed_by) REFERENCES public.users(id) ON DELETE SET NULL
);
CREATE INDEX idx_device_events_created_at ON public.device_events USING btree (created_at);
CREATE INDEX idx_device_events_device_id ON public.device_events USING btree (device_id);
CREATE INDEX idx_device_events_event_type ON public.device_events USING btree (event_type);


-- public.device_profile definition

-- Drop table

-- DROP TABLE public.device_profile;

CREATE TABLE public.device_profile (
	profile_id uuid DEFAULT gen_random_uuid() NOT NULL,
	device_id text NOT NULL,
	ignition_source public.ignition_source_t DEFAULT 'VIRTUAL'::text NOT NULL,
	virtual_ignition_on_seconds int4 DEFAULT 60 NOT NULL,
	virtual_ignition_off_seconds int4 DEFAULT 180 NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT device_profile_device_id_key UNIQUE (device_id),
	CONSTRAINT device_profile_pkey PRIMARY KEY (profile_id),
	CONSTRAINT device_profile_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id) ON DELETE CASCADE
);
CREATE INDEX idx_device_profile_device_id ON public.device_profile USING btree (device_id);

-- Table Triggers

create trigger trg_device_profile_updated_at before
update
    on
    public.device_profile for each row execute function update_updated_at_column();


-- public.discounts definition

-- Drop table

-- DROP TABLE public.discounts;

CREATE TABLE public.discounts (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	coupon_id uuid NOT NULL,
	promotion_code_id uuid NULL,
	account_id uuid NOT NULL,
	subscription_id uuid NULL,
	invoice_id uuid NULL,
	applied_amount_off numeric(10, 2) NULL,
	applied_percent_off numeric(5, 4) NULL,
	starts_at timestamptz DEFAULT now() NOT NULL,
	ends_at timestamptz NULL,
	gateway public.payment_gateway NULL,
	gateway_discount_id text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT dc_pkey PRIMARY KEY (id),
	CONSTRAINT dc_target_chk CHECK ((((subscription_id IS NOT NULL) AND (invoice_id IS NULL)) OR ((subscription_id IS NULL) AND (invoice_id IS NOT NULL)))),
	CONSTRAINT dc_account_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id),
	CONSTRAINT dc_coupon_fkey FOREIGN KEY (coupon_id) REFERENCES public.coupons(id),
	CONSTRAINT dc_invoice_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id),
	CONSTRAINT dc_promo_fkey FOREIGN KEY (promotion_code_id) REFERENCES public.promotion_codes(id),
	CONSTRAINT dc_sub_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscriptions(id)
);
CREATE INDEX idx_dc_account ON public.discounts USING btree (account_id);
CREATE INDEX idx_dc_invoice ON public.discounts USING btree (invoice_id);
CREATE INDEX idx_dc_sub ON public.discounts USING btree (subscription_id);


-- public.invoice_line_items definition

-- Drop table

-- DROP TABLE public.invoice_line_items;

CREATE TABLE public.invoice_line_items (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	invoice_id uuid NOT NULL,
	description text NOT NULL,
	line_type text NOT NULL,
	quantity numeric(10, 4) DEFAULT 1 NOT NULL,
	unit_amount numeric(10, 2) NOT NULL,
	discount_amount numeric(10, 2) DEFAULT 0 NOT NULL,
	tax_amount numeric(10, 2) DEFAULT 0 NOT NULL,
	total_amount numeric(10, 2) NOT NULL,
	period_start timestamptz NULL,
	period_end timestamptz NULL,
	plan_id uuid NULL,
	sat_product_key text NULL,
	sat_unit_key text DEFAULT 'E48'::text NULL,
	sort_order int4 DEFAULT 0 NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT li_pkey PRIMARY KEY (id),
	CONSTRAINT li_invoice_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE CASCADE
);
CREATE INDEX idx_li_invoice ON public.invoice_line_items USING btree (invoice_id);


-- public.invoice_line_item_taxes definition

-- Drop table

-- DROP TABLE public.invoice_line_item_taxes;

CREATE TABLE public.invoice_line_item_taxes (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	line_item_id uuid NOT NULL,
	tax_rate_id uuid NOT NULL,
	taxable_amount numeric(10, 2) NOT NULL,
	tax_amount numeric(10, 2) NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT lit_pkey PRIMARY KEY (id),
	CONSTRAINT lit_line_fkey FOREIGN KEY (line_item_id) REFERENCES public.invoice_line_items(id) ON DELETE CASCADE,
	CONSTRAINT lit_tax_rate_fkey FOREIGN KEY (tax_rate_id) REFERENCES public.tax_rates(id)
);
CREATE INDEX idx_lit_line ON public.invoice_line_item_taxes USING btree (line_item_id);