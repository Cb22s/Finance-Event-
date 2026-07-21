-- ============================================================================
-- SQL Migration for Money Master — Marriage & Courtship Feature (ADR-002)
-- ============================================================================

-- ──── 1. Add marriage_round_active to game_control ────
ALTER TABLE public.game_control
ADD COLUMN IF NOT EXISTS marriage_round_active BOOLEAN NOT NULL DEFAULT false;

-- ──── 2. Create spouse_archetypes table ────
CREATE TABLE IF NOT EXISTS public.spouse_archetypes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    income NUMERIC NOT NULL DEFAULT 0,
    expense_mod NUMERIC NOT NULL DEFAULT 0,
    stocks NUMERIC NOT NULL DEFAULT 0,
    gold NUMERIC NOT NULL DEFAULT 0,
    ef NUMERIC NOT NULL DEFAULT 0,
    loan NUMERIC NOT NULL DEFAULT 0,
    description TEXT
);

-- Seed spouse_archetypes
INSERT INTO public.spouse_archetypes (id, name, income, expense_mod, stocks, gold, ef, loan, description) VALUES
('saver', 'The Saver', 10000, -9000, 0, 8000, 22000, 0, 'Strong expense discipline, small emergency buffer. Low income; limited upside.'),
('earner', 'The Earner', 36000, 12000, 0, 0, 0, 0, 'High second income, but higher lifestyle expense and event exposure.'),
('investor', 'The Investor', 9000, -1000, 44000, 20000, 24000, 0, 'Brings an existing portfolio of stocks, gold, and cash. Volatile but high potential.'),
('anchor', 'The Anchor', 14000, -2000, 8000, 0, 45000, 0, 'Stable income and a well-funded emergency fund. Predictable and solid.')
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  income = EXCLUDED.income,
  expense_mod = EXCLUDED.expense_mod,
  stocks = EXCLUDED.stocks,
  gold = EXCLUDED.gold,
  ef = EXCLUDED.ef,
  loan = EXCLUDED.loan,
  description = EXCLUDED.description;

-- ──── 3. Add spouse fields to player_state ────
ALTER TABLE public.player_state
ADD COLUMN IF NOT EXISTS spouse_archetype TEXT REFERENCES public.spouse_archetypes(id) DEFAULT NULL;

-- ──── 4. Create player_spouse_reveals table ────
CREATE TABLE IF NOT EXISTS public.player_spouse_reveals (
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    archetype_id TEXT REFERENCES public.spouse_archetypes(id) ON DELETE CASCADE,
    trait_key TEXT NOT NULL,
    PRIMARY KEY (user_id, archetype_id, trait_key)
);

-- Enable RLS on player_spouse_reveals
ALTER TABLE public.player_spouse_reveals ENABLE ROW LEVEL SECURITY;

-- Add read own policy (mirroring player_state policies)
CREATE POLICY "player_spouse_reveals read own" ON public.player_spouse_reveals
    FOR SELECT USING (auth.uid() = user_id);

-- Reference tables public-read policy (mirroring events/choices)
ALTER TABLE public.spouse_archetypes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read for all" ON public.spouse_archetypes FOR SELECT USING (true);
