create extension if not exists pgcrypto;

create table if not exists public.stock_items (
 id uuid primary key default gen_random_uuid(),
 name text not null,
 unit text not null,
 minimum_level numeric(18,3) not null default 0,
 active boolean not null default true,
 created_at timestamptz not null default now(),
 unique(name,unit)
);

create table if not exists public.stock_movements (
 id uuid primary key default gen_random_uuid(),
 movement_date date not null,
 item_id uuid not null references public.stock_items(id),
 direction text not null check(direction in ('IN','OUT')),
 quantity numeric(18,3) not null check(quantity>0),
 reference_no text,
 party text,
 vehicle_no text,
 handled_by text,
 notes text,
 entered_by uuid not null,
 duplicate_fingerprint text not null unique,
 created_at timestamptz not null default now()
);

create index if not exists idx_stock_movements_date on public.stock_movements(movement_date);
create index if not exists idx_stock_movements_item on public.stock_movements(item_id);

create table if not exists public.accounts_sales (
 id uuid primary key default gen_random_uuid(),
 invoice_no text not null unique,
 invoice_date date not null,
 customer text not null,
 gstin text,
 taxable_value numeric(18,2) not null default 0,
 gst_amount numeric(18,2) not null default 0,
 invoice_total numeric(18,2) not null default 0,
 payment_status text not null default 'UNPAID',
 due_date date,
 entered_by uuid not null,
 created_at timestamptz not null default now()
);

create table if not exists public.accounts_purchases (
 id uuid primary key default gen_random_uuid(),
 bill_no text not null unique,
 bill_date date not null,
 supplier text not null,
 gstin text,
 taxable_value numeric(18,2) not null default 0,
 gst_amount numeric(18,2) not null default 0,
 bill_total numeric(18,2) not null default 0,
 entered_by uuid not null,
 created_at timestamptz not null default now()
);

-- Before real data: enable RLS and create role-based policies.
