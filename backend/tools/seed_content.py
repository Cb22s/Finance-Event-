# =============================================================================
# CONTENT PACK — 12-month problem + opportunity schedule
# =============================================================================
# Rewritten 2026-07-21 for the V2 economy. The OLD pack was tuned to the broken
# 8%/month-growth game where a Rs15,000 "emergency" was pocket change; against a
# ~Rs12-18k monthly surplus those numbers did nothing. Every value here is scaled
# so the decision actually hurts or helps.
#
# STRUCTURE: months 2-12 each get exactly ONE problem (event) and ONE opportunity
# (optional choice). Month 1 is initial allocation only. Market moves live in
# market_scenarios / the news library — these events are the PERSONAL life shocks
# on top of the market.
#
# CATEGORIES drive insurance: only 'emergency' and 'medical' pay out. You cannot
# insure a rent hike, a market move, or your own lifestyle creep.
#
# Emojis are embedded in names/descriptions for the real-time UI feel.

events_data = [
    {
        "month": 2, "category": "expense",
        "event_name": "💸 Lifestyle Creep",
        "event_type": "fixed", "impact_target": "expense_increase", "value": -4000,
        "description": "Your first few paychecks make small upgrades feel affordable — a nicer phone plan, more takeout, a couple of 'treat yourself' buys. The habits you set with your first salary tend to stick. This month those extras added up and came out of your cash."
    },
    {
        "month": 3, "category": "expense",
        "event_name": "📱 Phone Screen Shatters",
        "event_type": "fixed", "impact_target": "cash", "value": -14000,
        "description": "Your phone slipped off the table and the screen is done. A replacement is not optional in 2026 — you need it for work, payments and everything else. Straight out of cash."
    },
    {
        "month": 4, "category": "expense",
        "event_name": "🏠 Rent Renewal — Landlord Hikes",
        "event_type": "fixed", "impact_target": "expense_increase", "value": -5000,
        "description": "Your lease renews and rents across the city have climbed. The first visible bite of inflation on your fixed costs. You pay the catch-up adjustment now, on top of the automatic monthly inflation the game already applies from Month 4."
    },
    {
        "month": 5, "category": "emergency",
        "event_name": "🏥 Medical Emergency",
        "event_type": "fixed", "impact_target": "cash", "value": -48000,
        "description": "An unexpected hospital visit needs immediate payment. This is the month that separates the players who bought health cover and kept an emergency fund from the ones who put everything into stocks. Insurance pays out here if you have it."
    },
    {
        "month": 6, "category": "expense",
        "event_name": "🎉 Family Wedding Contribution",
        "event_type": "fixed", "impact_target": "cash", "value": -22000,
        "description": "A close cousin is getting married and the family expects you to contribute — gift, travel and outfit included. Culturally non-negotiable. It lands the same month you may be planning your own wedding round."
    },
    {
        "month": 7, "category": "expense",
        "event_name": "⚠️ Sudden Job Switch — One Gap Month",
        "event_type": "fixed", "impact_target": "cash", "value": -35000,
        "description": "You move jobs for a better long-term role, but there's a one-month gap between the last salary and the first new one, plus relocation costs. Job loss is NOT insurable — this is why the emergency fund exists."
    },
    {
        "month": 8, "category": "expense",
        "event_name": "🔧 Major Appliance + Vehicle Repair",
        "event_type": "fixed", "impact_target": "cash", "value": -30000,
        "description": "The fridge died and the bike needs a major service in the same month. Big-ticket repairs cluster at the worst times. Out of cash."
    },
    {
        "month": 9, "category": "medical",
        "event_name": "🩺 Family Member Falls Ill",
        "event_type": "fixed", "impact_target": "cash", "value": -55000,
        "description": "A parent needs a procedure that isn't fully covered. You step in. The largest personal shock of the year — and insurable, if you planned for it."
    },
    {
        "month": 10, "category": "expense",
        "event_name": "🧾 Tax Notice — Underpaid Advance Tax",
        "event_type": "fixed", "impact_target": "cash", "value": -26000,
        "description": "A reassessment shows you underpaid advance tax earlier in the year. Interest and penalty included. The taxman always collects."
    },
    {
        "month": 11, "category": "emergency",
        "event_name": "🛵 Minor Road Accident",
        "event_type": "fixed", "impact_target": "cash", "value": -38000,
        "description": "A small collision — you're fine, but there's a hospital check-up, vehicle damage and a third-party settlement. Insurable if you're covered."
    },
    {
        "month": 12, "category": "windfall",
        "event_name": "🎁 Year-End Performance Bonus",
        "event_type": "fixed", "impact_target": "cash", "value": 25000,
        "description": "You made it to the final month. Your annual appraisal comes through with a performance bonus — a reward for a full year of decisions, good and bad. A rare piece of pure good news."
    },
]

# ── OPPORTUNITIES ─────────────────────────────────────────────────────────────
# Each: cost is paid regardless; on a WIN (seeded probability) you receive
# reward_value into reward_type. Net EV = -cost + p*reward. Designed so smart
# bets are positive-EV but never risk-free, and high-risk bets carry real
# variance. Nothing here is a guaranteed printer of money.
choices_data = [
    {
        "month": 2, "name": "🎓 Online Skill Certification",
        "cost": 8000, "risk_type": "low", "reward_type": "cash",
        "reward_value": 16000, "probability": 70
        # EV +Rs3,200. Invest in yourself early; usually pays back.
    },
    {
        "month": 3, "name": "💻 Weekend Freelance Gig",
        "cost": 0, "risk_type": "low", "reward_type": "cash",
        "reward_value": 9000, "probability": 55
        # Free to attempt, coin-flip payoff. Pure upside.
    },
    {
        "month": 4, "name": "📊 No-Spend Month Challenge",
        "cost": 0, "risk_type": "low", "reward_type": "emergency_fund",
        "reward_value": 8000, "probability": 75
        # Discipline builds your buffer. High odds, feeds liquidity score.
    },
    {
        "month": 5, "name": "📈 Employer Stock Purchase Plan (ESPP)",
        "cost": 15000, "risk_type": "medium", "reward_type": "stocks",
        "reward_value": 32000, "probability": 55
        # EV +Rs2,600 into stocks. Discounted equity, but locks up cash the
        # same month as the medical emergency — a real liquidity trap.
    },
    {
        "month": 6, "name": "🤝 Salary Negotiation",
        "cost": 0, "risk_type": "low", "reward_type": "cash",
        "reward_value": 14000, "probability": 50
        # Costs nothing but nerve. Ask and you might receive.
    },
    {
        "month": 7, "name": "🚀 Launch a Side Business",
        "cost": 20000, "risk_type": "high", "reward_type": "cash",
        "reward_value": 65000, "probability": 35
        # EV +Rs2,750 but 65% chance you lose the whole Rs20k. High variance,
        # tempting exactly when your job is unstable. Classic over-reach trap.
    },
    {
        "month": 8, "name": "🏢 REIT / Real-Estate Fund Unit",
        "cost": 18000, "risk_type": "medium", "reward_type": "gold",
        "reward_value": 30000, "probability": 65
        # EV +Rs1,500, parked in a stable asset. Diversification play.
    },
    {
        "month": 9, "name": "⭐ Promotion to Senior Role",
        "cost": 3000, "risk_type": "medium", "reward_type": "cash",
        "reward_value": 24000, "probability": 60
        # Small cost (a course + certification), solid odds, strong payoff.
    },
    {
        "month": 10, "name": "🥇 Sovereign Gold Bond Scheme",
        "cost": 12000, "risk_type": "low", "reward_type": "gold",
        "reward_value": 15500, "probability": 78
        # EV +Rs90 — near break-even, but it's the SAFE haven going into the
        # accident month. Sometimes you pay for protection, not profit.
    },
    {
        "month": 11, "name": "👔 Team Lead Stipend",
        "cost": 2000, "risk_type": "medium", "reward_type": "cash",
        "reward_value": 18000, "probability": 60
        # Take on responsibility for a shot at a stipend bump.
    },
    {
        "month": 12, "name": "🎯 Year-End Tax-Saver Investment (ELSS)",
        "cost": 15000, "risk_type": "medium", "reward_type": "stocks",
        "reward_value": 27000, "probability": 62
        # EV +Rs1,740 into stocks, with a tax-saving flavour. Finish strong.
    },
]


def _sql_escape(v):
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    return str(v)


def emit_sql() -> str:
    """Generate the DELETE + INSERT SQL so the live DB and this file never drift."""
    lines = ["DELETE FROM public.optional_choices;", "DELETE FROM public.events;"]
    ev_cols = "month, category, event_name, event_type, impact_target, value, description"
    for e in events_data:
        vals = ", ".join(_sql_escape(e[c]) for c in
                         ["month", "category", "event_name", "event_type",
                          "impact_target", "value", "description"])
        lines.append(f"INSERT INTO public.events ({ev_cols}) VALUES ({vals});")
    ch_cols = "month, name, cost, risk_type, reward_type, reward_value, probability"
    for c in choices_data:
        vals = ", ".join(_sql_escape(c[k]) for k in
                         ["month", "name", "cost", "risk_type",
                          "reward_type", "reward_value", "probability"])
        lines.append(f"INSERT INTO public.optional_choices ({ch_cols}) VALUES ({vals});")
    return "\n".join(lines)


def main():
    from supabase_client import supabase
    print("Clearing existing events/choices...")
    supabase.table("optional_choices").delete().neq("id", 0).execute()
    supabase.table("events").delete().neq("id", 0).execute()
    print(f"Inserting {len(events_data)} events...")
    supabase.table("events").insert(events_data).execute()
    print(f"Inserting {len(choices_data)} choices...")
    supabase.table("optional_choices").insert(choices_data).execute()
    print("Done.")


if __name__ == "__main__":
    import sys
    if "--sql" in sys.argv:
        print(emit_sql())
    else:
        main()
