CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.threads (
    thread_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     text NOT NULL,
    title       text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS threads_user_idx ON app.threads (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app.messages (
    message_id  bigserial PRIMARY KEY,
    thread_id   uuid NOT NULL REFERENCES app.threads(thread_id) ON DELETE CASCADE,
    role        text NOT NULL CHECK (role IN ('user', 'assistant')),
    content     text NOT NULL,
    details     jsonb NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS messages_thread_idx ON app.messages (thread_id, message_id);

CREATE TABLE IF NOT EXISTS app.feedback (
    feedback_id bigserial PRIMARY KEY,
    message_id  bigint NOT NULL REFERENCES app.messages(message_id) ON DELETE CASCADE,
    user_id     text NOT NULL,
    rating      smallint NOT NULL CHECK (rating IN (-1, 1)),
    comment     text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (message_id, user_id)
);