-- ==========================================================================================
-- FASHR V2 - Supabase Schema Definition
-- ==========================================================================================

-- 1. Create native ENUM types for strong data constraints
CREATE TYPE gender_enum AS ENUM ('mens', 'womens', 'unisex');
CREATE TYPE body_type_enum AS ENUM ('slim', 'regular', 'athletic', 'plus', 'petite', 'tall');

-- ==========================================================================================
-- USERS TABLE
-- Stores profile data collected during Clerk onboarding
-- ==========================================================================================
CREATE TABLE users (
    -- The user_id directly matches the ID provided by Clerk
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    
    -- Dimensions needed for RAG filtering
    gender_filter gender_enum NOT NULL,
    body_type body_type_enum[] NOT NULL DEFAULT '{}',
    size_range TEXT[] NOT NULL DEFAULT '{}',
    preferred_brands TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================================================================
-- ANALYSES TABLE (Wardrobe History)
-- Stores the results of the AI style critique
-- ==========================================================================================
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Input Context
    occasion_tier_1 TEXT NOT NULL,
    occasion_tier_2 TEXT,
    style_persona TEXT NOT NULL,
    weather_condition TEXT,
    
    -- AI Outputs (Matches JSON schema from Node responses)
    detected_items JSONB NOT NULL DEFAULT '[]',     -- array of garments
    color_palette JSONB NOT NULL DEFAULT '[]',      -- array of hex codes + harmony type
    style_score INTEGER NOT NULL CHECK (style_score >= 0 AND style_score <= 100),
    score_breakdown JSONB NOT NULL,                 -- color, occasion, silhouette, completeness
    narrative_critique TEXT NOT NULL,
    gap_type TEXT,                                  -- e.g., 'structure', 'footwear', 'texture'
    
    -- Recommended Products (metadata only, no images)
    recommended_products JSONB DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================================================================
-- RATINGS TABLE
-- Anonymous rating system that feeds directly into the Pinecone RAG reranker
-- ==========================================================================================
CREATE TABLE ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- The Pinecone product ID that was rated
    product_id TEXT NOT NULL,
    
    -- We do NOT store user_id here to ensure ratings remain completely anonymous
    -- However, we store the analysis_id to ensure a user can only rate a product once per analysis
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    
    score INTEGER NOT NULL CHECK (score >= 1 AND score <= 5),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    -- Prevent rating the exact same product multiple times within a single analysis context
    UNIQUE(product_id, analysis_id)
);


-- ==========================================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Ensures data privacy since the frontend interacts directly with Supabase via the Clerk token
-- ==========================================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------------------
-- Users Policy: Users can only see and update their own profile record.
-- ------------------------------------------------------------------------------------------
CREATE POLICY "Users can view own profile" 
ON users FOR SELECT 
USING ((auth.uid()::text) = id);

CREATE POLICY "Users can insert own profile" 
ON users FOR INSERT 
WITH CHECK ((auth.uid()::text) = id);

CREATE POLICY "Users can update own profile" 
ON users FOR UPDATE 
USING ((auth.uid()::text) = id) 
WITH CHECK ((auth.uid()::text) = id);

-- ------------------------------------------------------------------------------------------
-- Analyses Policy: Users can only view, insert, and delete their own analyses history.
-- ------------------------------------------------------------------------------------------
CREATE POLICY "Users can view own analyses" 
ON analyses FOR SELECT 
USING ((auth.uid()::text) = user_id);

CREATE POLICY "Users can insert own analyses" 
ON analyses FOR INSERT 
WITH CHECK ((auth.uid()::text) = user_id);

CREATE POLICY "Users can delete own analyses" 
ON analyses FOR DELETE 
USING ((auth.uid()::text) = user_id);

-- ------------------------------------------------------------------------------------------
-- Ratings Policy: Users can insert ratings for their analyses. Open read for aggregation.
-- ------------------------------------------------------------------------------------------
-- We don't limit SELECT on ratings because the backend needs to aggregate them, 
-- and they are anonymous anyway.
CREATE POLICY "Anyone can read anonymous ratings" 
ON ratings FOR SELECT 
USING (true);

-- To insert a rating, the user must own the analysis ID they are linking the rating to.
CREATE POLICY "Users can insert ratings for their analyses" 
ON ratings FOR INSERT 
WITH CHECK (
    EXISTS (
        SELECT 1 FROM analyses a 
        WHERE a.id = analysis_id AND a.user_id = (auth.uid()::text)
    )
);

-- ==========================================================================================
-- REALTIME SUBSCRIPTIONS (Optional, currently off)
-- ==========================================================================================
-- If we want live updates to history later:
-- alter publication supabase_realtime add table analyses;
