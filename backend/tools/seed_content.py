import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import supabase

events_data = [
    # Month 2
    {
        "month": 2,
        "event_name": "Lifestyle Creep",
        "event_type": "fixed",
        "impact_target": "expense_increase",
        "value": -2500,
        "description": "Your first real paycheck makes small upgrades feel affordable — a nicer phone plan, more takeout, a few 'treat yourself' purchases. The habits you build with your very first paycheck tend to stick, for better or worse."
    },
    # Month 3
    {
        "month": 3,
        "event_name": "Transport Upkeep",
        "event_type": "fixed",
        "impact_target": "cash",
        "value": -1800,
        "description": "Between commuting wear-and-tear and routine upkeep, getting around cost more than expected this month — a reminder that steady habits and new skills take time to pay off, even while the regular costs of daily life keep coming."
    },
    # Month 4
    {
        "month": 4,
        "event_name": "Rent Renewal — Rates Increase",
        "event_type": "fixed",
        "impact_target": "expense_increase",
        "value": -2200,
        "description": "Your lease renews this month and rents citywide have climbed — the first visible sign of inflation. How closely you've been tracking your spending starts to matter more from here on."
    },
    # Month 5
    {
        "month": 5,
        "event_name": "Market Correction",
        "event_type": "percentage",
        "impact_target": "stocks",
        "value": -8,
        "description": "A broad market pullback trims stock valuations across the board. Every player faces the identical move this month — how well-prepared anyone is for volatility like this is about to be tested, one way or another."
    },
    # Month 6
    {
        "month": 6,
        "event_name": "Medical Emergency",
        "event_type": "fixed",
        "impact_target": "cash",
        "value": -15000,
        "description": "An unexpected hospital visit requires immediate payment — the kind of moment that reveals how much preparation and discipline actually matter, regardless of how the rest of the year has gone so far."
    },
    # Month 7
    {
        "month": 7,
        "event_name": "New Job, New Costs",
        "event_type": "fixed",
        "impact_target": "cash",
        "value": -3500,
        "description": "You take a new job with better long-term prospects, but the notice-period income gap and transition costs hit your wallet this month. Whatever skills or side income anyone has worked on this year are about to be worth something in a negotiation or a new role."
    },
    # Month 8
    {
        "month": 8,
        "event_name": "Sector Rally",
        "event_type": "percentage",
        "impact_target": "stocks",
        "value": 12,
        "description": "A strong earnings season lifts stock valuations broadly. Every player faces the identical move this month — the discipline to stay invested through the harder months is what a rally like this tends to reward."
    },
    # Month 9
    {
        "month": 9,
        "event_name": "Major Home Repair",
        "event_type": "fixed",
        "impact_target": "cash",
        "value": -18000,
        "description": "A major system failure at home demands immediate repair. Preparation — whether that's an emergency fund, insurance, or simply careful budgeting — determines whether a shock like this is a manageable setback or a lasting one."
    },
    # Month 10
    {
        "month": 10,
        "event_name": "Market Stress Test",
        "event_type": "percentage",
        "impact_target": "stocks",
        "value": -15,
        "description": "A sharp downturn tests every portfolio at once. Every player faces the identical move this month — the decisions that hold up under pressure are usually the ones made calmly, long before the pressure arrived."
    },
    # Month 11
    {
        "month": 11,
        "event_name": "Tax Settlement",
        "event_type": "fixed",
        "impact_target": "cash",
        "value": -5000,
        "description": "Annual tax obligations come due — a predictable cost that rewards planning ahead rather than reacting in the moment. Consistency over the course of a year tends to get noticed."
    },
    # Month 12
    {
        "month": 12,
        "event_name": "Year-End Performance Bonus",
        "event_type": "fixed",
        "impact_target": "cash",
        "value": 10000,
        "description": "A full year of consistent work is rewarded with a year-end performance bonus. As the year closes, your own monthly record — visible on your dashboard — is the real account of how you got here, whatever path that was."
    }
]

choices_data = [
    # Month 2
    {
        "month": 2,
        "name": "Online Skill Certification (Equity Track)",
        "cost": 8000,
        "risk_type": "low",
        "reward_type": "stocks",
        "reward_value": 19000,
        "probability": 70
    },
    # Month 3
    {
        "month": 3,
        "name": "Weekend Freelance Gig",
        "cost": 0,
        "risk_type": "low",
        "reward_type": "cash",
        "reward_value": 4500,
        "probability": 55
    },
    # Month 4
    {
        "month": 4,
        "name": "Budget Optimization Challenge",
        "cost": 2000,
        "risk_type": "low",
        "reward_type": "emergency_fund",
        "reward_value": 5000,
        "probability": 75
    },
    # Month 5
    {
        "month": 5,
        "name": "Term Insurance Enrollment",
        "cost": 4500,
        "risk_type": "medium",
        "reward_type": "cash",
        "reward_value": 13000,
        "probability": 45
    },
    # Month 6
    {
        "month": 6,
        "name": "Family Support Network",
        "cost": 3000,
        "risk_type": "medium",
        "reward_type": "cash",
        "reward_value": 7500,
        "probability": 60
    },
    # Month 7
    {
        "month": 7,
        "name": "Negotiate Your Salary — Make Your Case",
        "cost": 0,
        "risk_type": "low",
        "reward_type": "cash",
        "reward_value": 9000,
        "probability": 50
    },
    # Month 8
    {
        "month": 8,
        "name": "Launch a Side Business",
        "cost": 12000,
        "risk_type": "high",
        "reward_type": "cash",
        "reward_value": 30000,
        "probability": 35
    },
    # Month 9
    {
        "month": 9,
        "name": "'Buy Now, Pay Later' Upgrade",
        "cost": 4000,
        "risk_type": "low",
        "reward_type": "cash",
        "reward_value": 4300,
        "probability": 90
    },
    # Month 10
    {
        "month": 10,
        "name": "Long-Term Reserve Contribution",
        "cost": 5000,
        "risk_type": "low",
        "reward_type": "gold",
        "reward_value": 5800,
        "probability": 70
    },
    # Month 11
    {
        "month": 11,
        "name": "Promoted to Team Lead",
        "cost": 1500,
        "risk_type": "medium",
        "reward_type": "cash",
        "reward_value": 11000,
        "probability": 65
    },
    # Month 12
    {
        "month": 12,
        "name": "Charitable Giving — Year-End Donation",
        "cost": 5000,
        "risk_type": "low",
        "reward_type": "cash",
        "reward_value": 5800,
        "probability": 55
    }
]

def main():
    print("Clearing existing events...")
    supabase.table("events").delete().neq("id", 0).execute()
    print("Clearing existing choices...")
    supabase.table("optional_choices").delete().neq("id", 0).execute()
    
    print(f"Inserting {len(events_data)} events...")
    supabase.table("events").insert(events_data).execute()
    
    print(f"Inserting {len(choices_data)} optional choices...")
    supabase.table("optional_choices").insert(choices_data).execute()
    
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    main()
