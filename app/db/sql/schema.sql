create extension if not exists vector;

create table if not exists schema_migrations (
    version text primary key,
    description text,
    applied_at timestamptz not null default now()
);

create table if not exists students (
    id uuid primary key default gen_random_uuid(),
    usn text not null unique,
    student_name text,
    semester int,
    section text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_students_usn on students(usn);

create table if not exists subjects (
    id uuid primary key default gen_random_uuid(),
    subject_code text not null unique,
    subject_name text not null,
    semester int,
    credits numeric,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_subjects_code on subjects(subject_code);
create index if not exists idx_subjects_name on subjects(subject_name);

create table if not exists email_logs (
    id uuid primary key default gen_random_uuid(),
    message_id text not null unique,
    sender_email text not null,
    subject text not null,
    body_text text,
    received_at timestamptz not null,
    processed_at timestamptz,
    has_attachments boolean not null default false,
    query_detected boolean not null default false,
    query_text text,
    response_status text,
    response_error text,
    created_at timestamptz not null default now()
);

create table if not exists query_logs (
    id uuid primary key default gen_random_uuid(),
    channel text not null check (channel in ('chat', 'email')),
    raw_query text not null,
    normalized_query text,
    intent text,
    tool_choice text,
    sql_result_count int not null default 0,
    vector_result_count int not null default 0,
    final_response text,
    status text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists email_dead_letters (
    id uuid primary key default gen_random_uuid(),
    message_id text,
    sender_email text,
    subject text,
    error_text text not null,
    raw_hash text,
    created_at timestamptz not null default now()
);

create index if not exists idx_email_logs_message_id on email_logs(message_id);
create index if not exists idx_email_logs_sender on email_logs(sender_email);

create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    source_type text not null check (source_type in ('upload', 'email')),
    source_ref uuid,
    file_name text not null,
    mime_type text not null,
    content_text text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists results (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students(id) on delete cascade,
    subject_id uuid not null references subjects(id) on delete cascade,
    exam_type text,
    marks numeric,
    max_marks numeric,
    grade text,
    pass_fail text,
    source_type text not null check (source_type in ('upload', 'email')),
    source_ref uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (student_id, subject_id, exam_type, source_ref)
);

create index if not exists idx_results_student on results(student_id);
create index if not exists idx_results_subject on results(subject_id);

create table if not exists vector_chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    chunk_index int not null,
    chunk_text text not null,
    embedding vector(384) not null,
    source_type text not null check (source_type in ('upload', 'email')),
    source_ref uuid,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists ingested_blobs (
    id uuid primary key default gen_random_uuid(),
    source_type text not null check (source_type in ('upload', 'email')),
    source_ref uuid,
    content_hash text not null unique,
    file_name text,
    created_at timestamptz not null default now()
);

create index if not exists idx_vector_chunks_document on vector_chunks(document_id);
-- choose one ANN index based on your Supabase Postgres version and workload
-- create index if not exists idx_vector_chunks_embedding_hnsw on vector_chunks using hnsw (embedding vector_cosine_ops);
-- create index if not exists idx_vector_chunks_embedding_ivfflat on vector_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create or replace function match_vector_chunks(
    query_embedding vector(384),
    match_count int default 5,
    source_filter text default null
)
returns table (
    id uuid,
    document_id uuid,
    chunk_index int,
    chunk_text text,
    source_type text,
    source_ref uuid,
    metadata jsonb,
    similarity float
)
language sql
stable
as $$
    select
        vc.id,
        vc.document_id,
        vc.chunk_index,
        vc.chunk_text,
        vc.source_type,
        vc.source_ref,
        vc.metadata,
        1 - (vc.embedding <=> query_embedding) as similarity
    from vector_chunks vc
    where source_filter is null or vc.source_type = source_filter
    order by vc.embedding <=> query_embedding
    limit greatest(match_count, 1);
$$;

create or replace function student_lookup(payload jsonb default '{}'::jsonb)
returns table (
    usn text,
    student_name text,
    semester int,
    subject_code text,
    subject_name text,
    marks numeric,
    max_marks numeric,
    grade text,
    pass_fail text,
    exam_type text
)
language sql
stable
as $$
    select
        s.usn,
        s.student_name,
        s.semester,
        sub.subject_code,
        sub.subject_name,
        r.marks,
        r.max_marks,
        r.grade,
        r.pass_fail,
        r.exam_type
    from results r
    join students s on s.id = r.student_id
    join subjects sub on sub.id = r.subject_id
    where ((payload->>'usn') is null or s.usn = upper(payload->>'usn'))
      and ((payload->>'subject') is null or lower(sub.subject_name) = lower(payload->>'subject'))
      and ((payload->>'semester') is null or s.semester = (payload->>'semester')::int)
    order by s.usn, sub.subject_name;
$$;

create or replace function subject_analysis(payload jsonb default '{}'::jsonb)
returns table (
    subject_name text,
    highest numeric,
    lowest numeric,
    average numeric
)
language sql
stable
as $$
    select
        sub.subject_name,
        max(r.marks) as highest,
        min(r.marks) as lowest,
        avg(r.marks) as average
    from results r
    join subjects sub on sub.id = r.subject_id
    where ((payload->>'subject') is null or lower(sub.subject_name) = lower(payload->>'subject'))
      and r.marks is not null
    group by sub.subject_name
    order by sub.subject_name;
$$;

create or replace function ranking(payload jsonb default '{}'::jsonb)
returns table (
    usn text,
    student_name text,
    total_marks numeric,
    average_marks numeric,
    rank_position bigint
)
language sql
stable
as $$
    with scores as (
        select
            s.usn,
            s.student_name,
            sum(coalesce(r.marks, 0)) as total_marks,
            avg(r.marks) as average_marks
        from results r
        join students s on s.id = r.student_id
        join subjects sub on sub.id = r.subject_id
        where ((payload->>'subject') is null or lower(sub.subject_name) = lower(payload->>'subject'))
          and ((payload->>'semester') is null or s.semester = (payload->>'semester')::int)
        group by s.usn, s.student_name
    )
    select
        usn,
        student_name,
        total_marks,
        average_marks,
        dense_rank() over (order by total_marks desc) as rank_position
    from scores
    order by rank_position, usn;
$$;

create or replace function comparison(payload jsonb default '{}'::jsonb)
returns table (
    usn text,
    student_name text,
    subject_name text,
    marks numeric,
    class_average numeric,
    delta_from_average numeric
)
language sql
stable
as $$
    with base as (
        select
            s.usn,
            s.student_name,
            sub.subject_name,
            r.marks,
            avg(r.marks) over (partition by sub.id) as class_average
        from results r
        join students s on s.id = r.student_id
        join subjects sub on sub.id = r.subject_id
        where ((payload->>'usn') is null or s.usn = upper(payload->>'usn'))
          and ((payload->>'subject') is null or lower(sub.subject_name) = lower(payload->>'subject'))
    )
    select
        usn,
        student_name,
        subject_name,
        marks,
        class_average,
        marks - class_average as delta_from_average
    from base
    order by subject_name;
$$;

create or replace function aggregation(payload jsonb default '{}'::jsonb)
returns table (
    usn text,
    student_name text,
    total_marks numeric,
    average_marks numeric
)
language sql
stable
as $$
    select
        s.usn,
        s.student_name,
        sum(coalesce(r.marks, 0)) as total_marks,
        avg(r.marks) as average_marks
    from results r
    join students s on s.id = r.student_id
    where ((payload->>'usn') is null or s.usn = upper(payload->>'usn'))
      and ((payload->>'semester') is null or s.semester = (payload->>'semester')::int)
    group by s.usn, s.student_name
    order by s.usn;
$$;

create or replace function report_generation(payload jsonb default '{}'::jsonb)
returns table (
    usn text,
    student_name text,
    subject_name text,
    marks numeric,
    grade text
)
language sql
stable
as $$
    select
        s.usn,
        s.student_name,
        sub.subject_name,
        r.marks,
        r.grade
    from results r
    join students s on s.id = r.student_id
    join subjects sub on sub.id = r.subject_id
    where ((payload->>'usn') is null or s.usn = upper(payload->>'usn'))
    order by s.usn, sub.subject_name;
$$;

create or replace function student_report(payload jsonb default '{}'::jsonb)
returns table (
    usn text,
    student_name text,
    subject_name text,
    marks numeric,
    grade text,
    sgpa numeric
)
language sql
stable
as $$
    with grade_map as (
        select * from jsonb_each_text(
            coalesce(nullif(payload->'grade_scale', '{}'::jsonb),
            '{"O":10,"A+":9,"A":8,"B+":7,"B":6,"C":5,"P":4,"F":0}'::jsonb)
        )
    ),
    base as (
        select
            s.usn,
            s.student_name,
            sub.subject_name,
            r.marks,
            r.grade,
            coalesce(sub.credits, 0) as credits,
            coalesce((select value::numeric from grade_map gm where gm.key = r.grade), 0) as grade_point
        from results r
        join students s on s.id = r.student_id
        join subjects sub on sub.id = r.subject_id
        where ((payload->'filters'->>'usn') is null or s.usn = upper(payload->'filters'->>'usn'))
    ),
    sgpa_calc as (
        select
            usn,
            case when sum(credits) = 0 then null else round(sum(grade_point * credits) / sum(credits), 2) end as sgpa
        from base
        group by usn
    )
    select
        b.usn,
        b.student_name,
        b.subject_name,
        b.marks,
        b.grade,
        s.sgpa
    from base b
    left join sgpa_calc s on s.usn = b.usn
    order by b.usn, b.subject_name;
$$;

create or replace function class_report(payload jsonb default '{}'::jsonb)
returns table (
    class_average numeric,
    failure_count bigint,
    topper_usn text,
    topper_name text,
    topper_total numeric
)
language sql
stable
as $$
    with student_totals as (
        select
            s.usn,
            s.student_name,
            sum(coalesce(r.marks, 0)) as total_marks,
            avg(r.marks) as average_marks,
            sum(case when upper(coalesce(r.pass_fail, 'PASS')) = 'FAIL' then 1 else 0 end) as failures
        from results r
        join students s on s.id = r.student_id
        where ((payload->'filters'->>'semester') is null or s.semester = (payload->'filters'->>'semester')::int)
        group by s.usn, s.student_name
    ),
    topper as (
        select usn, student_name, total_marks
        from student_totals
        order by total_marks desc
        limit 1
    )
    select
        (select round(avg(average_marks), 2) from student_totals) as class_average,
        (select coalesce(sum(failures), 0) from student_totals) as failure_count,
        (select usn from topper) as topper_usn,
        (select student_name from topper) as topper_name,
        (select total_marks from topper) as topper_total;
$$;

create or replace function subject_report(payload jsonb default '{}'::jsonb)
returns table (
    subject_name text,
    highest numeric,
    lowest numeric,
    average numeric
)
language sql
stable
as $$
    select
        sub.subject_name,
        max(r.marks) as highest,
        min(r.marks) as lowest,
        round(avg(r.marks), 2) as average
    from results r
    join subjects sub on sub.id = r.subject_id
    where ((payload->'filters'->>'subject') is null or lower(sub.subject_name) = lower(payload->'filters'->>'subject'))
    group by sub.subject_name
    order by sub.subject_name;
$$;

insert into schema_migrations(version, description)
values ('001_unified_schema', 'Unified schema, rpc functions, and hardening tables')
on conflict (version) do nothing;
