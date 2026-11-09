-- Hybrid RAG sample: PostgreSQL schema (synthetic data, fictional entities)
-- Three schemas mirror the three domains: tax, banking, finance.
-- COMMENT ON statements double as the "table cards" you embed for text-to-SQL.

CREATE SCHEMA IF NOT EXISTS tax;
CREATE SCHEMA IF NOT EXISTS banking;
CREATE SCHEMA IF NOT EXISTS finance;

-- ============================ TAX ============================
CREATE TABLE tax.jurisdictions (
    code           char(2) PRIMARY KEY,
    name           text NOT NULL,
    level          text NOT NULL,
    base_rate_pct  numeric(5,2) NOT NULL
);
COMMENT ON TABLE tax.jurisdictions IS 'Taxing jurisdictions (US states) and base sales/use tax rate in percent.';

CREATE TABLE tax.vendors (
    vendor_id         text PRIMARY KEY,
    vendor_name       text NOT NULL,
    primary_category  text NOT NULL CHECK (primary_category IN ('telecom_equipment','software','services','office')),
    hq_state          char(2) REFERENCES tax.jurisdictions(code),
    federal_ein       text
);
COMMENT ON TABLE tax.vendors IS 'Suppliers Meridian Financial Group buys from. primary_category drives exemption eligibility.';

CREATE TABLE tax.exemption_certificates (
    certificate_id     text PRIMARY KEY,
    vendor_id          text NOT NULL REFERENCES tax.vendors(vendor_id),
    jurisdiction_code  char(2) NOT NULL REFERENCES tax.jurisdictions(code),
    exemption_type     text NOT NULL,
    issued_date        date NOT NULL,
    expiry_date        date NOT NULL,
    status             text NOT NULL CHECK (status IN ('active','expired','revoked'))
);
COMMENT ON TABLE tax.exemption_certificates IS 'Sales tax exemption certificates on file per vendor and state. Valid only if invoice_date <= expiry_date.';

CREATE TABLE tax.invoices (
    invoice_id         text PRIMARY KEY,
    vendor_id          text NOT NULL REFERENCES tax.vendors(vendor_id),
    invoice_date       date NOT NULL,
    jurisdiction_code  char(2) NOT NULL REFERENCES tax.jurisdictions(code),
    category           text NOT NULL,
    cost_center        text NOT NULL,
    amount_usd         numeric(14,2) NOT NULL,
    tax_charged_usd    numeric(14,2) NOT NULL,
    exemption_claimed  boolean NOT NULL,
    certificate_id     text REFERENCES tax.exemption_certificates(certificate_id)
);
COMMENT ON TABLE tax.invoices IS 'Vendor purchase invoices for 2026. exemption_claimed=true means no sales tax was charged; certificate_id should point to a valid certificate.';
CREATE INDEX ON tax.invoices (jurisdiction_code, invoice_date);

CREATE TABLE tax.tax_payments (
    payment_id         text PRIMARY KEY,
    jurisdiction_code  char(2) NOT NULL REFERENCES tax.jurisdictions(code),
    tax_type           text NOT NULL,
    period_month       date NOT NULL,
    amount_usd         numeric(14,2) NOT NULL,
    paid_date          date NOT NULL,
    confirmation_no    text
);
COMMENT ON TABLE tax.tax_payments IS 'Monthly use tax remittances to each state. period_month is the first day of the month covered.';

-- ============================ BANKING ============================
CREATE TABLE banking.customers (
    customer_id      text PRIMARY KEY,
    legal_name       text NOT NULL,
    industry         text NOT NULL,
    state            char(2) NOT NULL,
    onboarded_date   date NOT NULL,
    aml_risk_rating  text NOT NULL CHECK (aml_risk_rating IN ('low','medium','high'))
);
COMMENT ON TABLE banking.customers IS 'Commercial customers of Lakeshore Bank (Meridian subsidiary) with AML risk rating.';

CREATE TABLE banking.accounts (
    account_id    text PRIMARY KEY,
    customer_id   text NOT NULL REFERENCES banking.customers(customer_id),
    account_type  text NOT NULL,
    opened_date   date NOT NULL,
    status        text NOT NULL
);
COMMENT ON TABLE banking.accounts IS 'Deposit accounts per customer (operating, payroll).';

CREATE TABLE banking.transactions (
    txn_id      text PRIMARY KEY,
    account_id  text NOT NULL REFERENCES banking.accounts(account_id),
    txn_date    date NOT NULL,
    channel     text NOT NULL CHECK (channel IN ('ach','wire','check','cash','card')),
    direction   text NOT NULL CHECK (direction IN ('credit','debit')),
    amount_usd  numeric(14,2) NOT NULL,
    branch_id   text
);
COMMENT ON TABLE banking.transactions IS 'Account transactions Jul-Sep 2026. Cash credits are deposits; used for CTR and structuring monitoring.';
CREATE INDEX ON banking.transactions (account_id, txn_date);

CREATE TABLE banking.loans (
    loan_id                  text PRIMARY KEY,
    customer_id              text NOT NULL REFERENCES banking.customers(customer_id),
    loan_type                text NOT NULL,
    original_principal_usd   numeric(14,2) NOT NULL,
    outstanding_balance_usd  numeric(14,2) NOT NULL,
    interest_rate_pct        numeric(6,3) NOT NULL,
    origination_date         date NOT NULL,
    dscr                     numeric(5,2) NOT NULL,
    ltv_pct                  numeric(5,1) NOT NULL,
    risk_grade               text NOT NULL
);
COMMENT ON TABLE banking.loans IS 'Commercial loan book with latest debt service coverage ratio (dscr) and loan-to-value (ltv_pct).';

-- ============================ FINANCE ============================
CREATE TABLE finance.gl_accounts (
    gl_account    text PRIMARY KEY,
    account_name  text NOT NULL,
    account_type  text NOT NULL CHECK (account_type IN ('revenue','expense'))
);
COMMENT ON TABLE finance.gl_accounts IS 'General ledger chart of accounts (P&L lines).';

CREATE TABLE finance.budgets (
    fiscal_year   int NOT NULL,
    fiscal_month  int NOT NULL CHECK (fiscal_month BETWEEN 1 AND 12),
    gl_account    text NOT NULL REFERENCES finance.gl_accounts(gl_account),
    budget_usd    numeric(14,2) NOT NULL,
    PRIMARY KEY (fiscal_year, fiscal_month, gl_account)
);
COMMENT ON TABLE finance.budgets IS 'Monthly budget by GL account. Fiscal year = calendar year.';

CREATE TABLE finance.gl_entries (
    entry_id      text PRIMARY KEY,
    posting_date  date NOT NULL,
    gl_account    text NOT NULL REFERENCES finance.gl_accounts(gl_account),
    amount_usd    numeric(14,2) NOT NULL,
    source        text NOT NULL
);
COMMENT ON TABLE finance.gl_entries IS 'Monthly actuals posted at close, one summarized entry per GL account per month.';

-- Read-only role for the chatbot's SQL node
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chatbot_ro') THEN
    CREATE ROLE chatbot_ro LOGIN PASSWORD 'change-me';
  END IF;
END $$;
GRANT USAGE ON SCHEMA tax, banking, finance TO chatbot_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA tax, banking, finance TO chatbot_ro;
ALTER ROLE chatbot_ro SET statement_timeout = '10s';
