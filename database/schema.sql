-- =============================================================================
-- PRODUCT METADATA SCHEMA
-- PostgreSQL / Supabase
-- 1:1 mapping from product_metadata.json - no field changes
-- =============================================================================

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
