-- DROP SCHEMA team;

CREATE SCHEMA team AUTHORIZATION pgadmin;

-- DROP SCHEMA team;

CREATE SCHEMA team AUTHORIZATION pgadmin;

-- Drop table

-- DROP TABLE team.emergency_events;

CREATE TABLE team.emergency_events (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	team_id uuid NOT NULL,
	triggered_by_user_id uuid NOT NULL,
	emergency_type text NOT NULL,
	status text DEFAULT 'ACTIVE'::text NOT NULL,
	started_at timestamptz DEFAULT now() NOT NULL,
	ended_at timestamptz NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	CONSTRAINT emergency_events_pkey PRIMARY KEY (id),
	CONSTRAINT emergency_events_team_id_fkey FOREIGN KEY (team_id) REFERENCES team.teams(id) ON DELETE CASCADE,
	CONSTRAINT emergency_events_triggered_by_user_id_fkey FOREIGN KEY (triggered_by_user_id) REFERENCES public.users(id)
);

-- Drop table

-- DROP TABLE team.invites;

CREATE TABLE team.invites (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	team_id uuid NOT NULL,
	created_by_user_id uuid NOT NULL,
	invite_method text NOT NULL,
	invited_role text NOT NULL,
	token_hash text NOT NULL,
	expires_at timestamptz NOT NULL,
	max_uses int4 DEFAULT 1 NOT NULL,
	used_count int4 DEFAULT 0 NOT NULL,
	is_active bool DEFAULT true NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT chk_invite_method CHECK ((invite_method = ANY (ARRAY['QR'::text, 'LINK'::text, 'EMAIL'::text, 'PHONE'::text]))),
	CONSTRAINT invites_pkey PRIMARY KEY (id),
	CONSTRAINT invites_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE CASCADE,
	CONSTRAINT invites_team_id_fkey FOREIGN KEY (team_id) REFERENCES team.teams(id) ON DELETE CASCADE
);
CREATE INDEX idx_team_invites_team ON team.invites USING btree (team_id);
CREATE UNIQUE INDEX uq_team_invite_token ON team.invites USING btree (token_hash);

-- Drop table

-- DROP TABLE team.members;

CREATE TABLE team.members (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	team_id uuid NOT NULL,
	user_id uuid NOT NULL,
	"role" text NOT NULL,
	invited_by_user_id uuid NULL,
	joined_at timestamptz DEFAULT now() NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	CONSTRAINT chk_member_role CHECK ((role = ANY (ARRAY['OWNER'::text, 'ADMIN'::text, 'MEMBER'::text, 'DEPENDENT'::text, 'EMPLOYEE'::text, 'VIEWER'::text, 'EMERGENCY_CONTACT'::text, 'GUEST'::text]))),
	CONSTRAINT members_pkey PRIMARY KEY (id),
	CONSTRAINT uq_team_member UNIQUE (team_id, user_id),
	CONSTRAINT members_invited_by_user_id_fkey FOREIGN KEY (invited_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL,
	CONSTRAINT members_team_id_fkey FOREIGN KEY (team_id) REFERENCES team.teams(id) ON DELETE CASCADE,
	CONSTRAINT members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
CREATE INDEX idx_team_members_team ON team.members USING btree (team_id);
CREATE INDEX idx_team_members_user ON team.members USING btree (user_id);

-- Drop table

-- DROP TABLE team.teams;

CREATE TABLE team.teams (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	account_id uuid NOT NULL,
	"name" text NOT NULL,
	"type" text NOT NULL,
	status text DEFAULT 'ACTIVE'::text NOT NULL,
	timezone text DEFAULT 'UTC'::text NOT NULL,
	expires_at timestamptz NULL,
	auto_delete_at timestamptz NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_by_user_id uuid NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT chk_team_status CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'SUSPENDED'::text, 'EXPIRED'::text, 'DELETED'::text]))),
	CONSTRAINT chk_team_type CHECK ((type = ANY (ARRAY['FAMILY'::text, 'WORKFORCE'::text, 'FRIENDS'::text, 'EMERGENCY'::text, 'TEMPORARY'::text, 'TRAVEL'::text, 'EVENT'::text]))),
	CONSTRAINT teams_pkey PRIMARY KEY (id),
	CONSTRAINT teams_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE,
	CONSTRAINT teams_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL
);
CREATE INDEX idx_team_account ON team.teams USING btree (account_id);
CREATE INDEX idx_team_expires_at ON team.teams USING btree (expires_at);
CREATE INDEX idx_team_type ON team.teams USING btree (type);

-- Drop table

-- DROP TABLE team.visibility_rules;

CREATE TABLE team.visibility_rules (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	team_id uuid NOT NULL,
	subject_role text NOT NULL,
	viewer_role text NOT NULL,
	access_mode text NOT NULL,
	schedule jsonb NULL,
	is_active bool DEFAULT true NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT chk_access_mode CHECK ((access_mode = ANY (ARRAY['ALWAYS'::text, 'SCHEDULED'::text, 'ON_DEMAND'::text, 'EMERGENCY_ONLY'::text]))),
	CONSTRAINT visibility_rules_pkey PRIMARY KEY (id),
	CONSTRAINT visibility_rules_team_id_fkey FOREIGN KEY (team_id) REFERENCES team.teams(id) ON DELETE CASCADE
);
CREATE INDEX idx_visibility_team ON team.visibility_rules USING btree (team_id);