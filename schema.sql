-- =============================================================================
-- PRODUCT METADATA SCHEMA
-- PostgreSQL / Supabase
-- 1:1 mapping from product_metadata.json - no field changes
-- =============================================================================

-- Enable trigram extension for fast text search (if not already enabled)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DROP TABLE IF EXISTS products CASCADE;

CREATE TABLE products (
    -- Top-level fields
    sku_id              VARCHAR(100) PRIMARY KEY,
    image_file          VARCHAR(255) NOT NULL,
    title               VARCHAR(500),
    brand               VARCHAR(255),

    -- visual_features fields (exact 1:1 mapping)
    type                VARCHAR(100) NOT NULL,
    category            VARCHAR(100) NOT NULL,
    sub_category        VARCHAR(100),
    primary_color       VARCHAR(100),
    secondary_colors    TEXT[],
    pattern             VARCHAR(100),
    material_appearance VARCHAR(100),
    fit                 VARCHAR(50),
    gender              VARCHAR(50) NOT NULL,
    design_elements     TEXT[],
    formality_level     VARCHAR(50),
    versatility         VARCHAR(50),
    statement_piece     BOOLEAN DEFAULT FALSE,
    functional_slot     VARCHAR(50) NOT NULL,
    style               VARCHAR(255),
    fashion_aesthetics  TEXT[],
    occasion            TEXT[],
    formality_score     SMALLINT NOT NULL,
    season              TEXT[],

    -- Metadata timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- REQUIRED INDEXES
-- =============================================================================

CREATE INDEX idx_products_functional_slot ON products (functional_slot);
CREATE INDEX idx_products_formality_score ON products (formality_score);
CREATE INDEX idx_products_gender ON products (gender);
CREATE INDEX idx_products_occasion ON products USING GIN (occasion);
CREATE INDEX idx_products_season ON products USING GIN (season);
CREATE INDEX idx_products_fashion_aesthetics ON products USING GIN (fashion_aesthetics);

-- =============================================================================
-- ADDITIONAL USEFUL INDEXES
-- =============================================================================

CREATE INDEX idx_products_category ON products (category);
CREATE INDEX idx_products_primary_color ON products (primary_color);
CREATE INDEX idx_products_brand ON products (brand);
CREATE INDEX idx_products_style ON products (style);

-- Composite indexes for common query patterns
CREATE INDEX idx_products_slot_gender ON products (functional_slot, gender);
CREATE INDEX idx_products_slot_formality ON products (functional_slot, formality_score);

-- =============================================================================
-- TRIGRAM INDEXES FOR FAST TEXT SEARCH
-- =============================================================================

-- These indexes dramatically speed up ILIKE searches (10x+ improvement)
CREATE INDEX idx_products_title_trgm ON products USING GIN (title gin_trgm_ops);
CREATE INDEX idx_products_brand_trgm ON products USING GIN (brand gin_trgm_ops);

-- =============================================================================
-- AUTO-UPDATE TRIGGER FOR updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- COMPATIBILITY EDGES TABLE
-- Stores pre-computed pairwise compatibility scores between products
-- =============================================================================

DROP TABLE IF EXISTS compatibility_edges CASCADE;

CREATE TABLE compatibility_edges (
    sku_1 VARCHAR(100) NOT NULL,
    sku_2 VARCHAR(100) NOT NULL,
    target_slot VARCHAR(50) NOT NULL,  -- The slot that sku_2 fills
    score NUMERIC(4,3) NOT NULL,       -- 0.000 to 1.000

    PRIMARY KEY (sku_1, sku_2),

    -- Foreign keys for referential integrity
    FOREIGN KEY (sku_1) REFERENCES products(sku_id) ON DELETE CASCADE,
    FOREIGN KEY (sku_2) REFERENCES products(sku_id) ON DELETE CASCADE
);

-- Critical indexes for query patterns
-- Main query: get compatible items for a SKU, optionally filtered by slot, sorted by score
CREATE INDEX idx_compat_sku1_slot_score ON compatibility_edges(sku_1, target_slot, score DESC);

-- Reverse lookup (for bidirectional compatibility)
CREATE INDEX idx_compat_sku2 ON compatibility_edges(sku_2);

-- High-score filtering (for quality recommendations)
CREATE INDEX idx_compat_score ON compatibility_edges(score) WHERE score >= 0.7;
