# tickets.py  ── minimal break-even calculator
import pandas as pd

# ──────────── USER INPUTS ────────────
# this is based on 2024 hackathon, change accordingly
# particularly the price variable and the sold variable to approximate attendance
TIERS = {                       # leave empty {} if you use only simple_price
    "Early Bird + Shirt (UQ)"     : dict(price=55, sold=51, merch=True),
    "Early Bird (UQ)"             : dict(price=35, sold=86, merch=False),
    "UQ Regular"                  : dict(price=45, sold=14, merch=False),
    "Early Bird (Non-UQ)"         : dict(price=40, sold=9 , merch=False),
    "Early Bird + Shirt (Non-UQ)" : dict(price=60, sold=4 , merch=True),
    "Non-UQ"                      : dict(price=50, sold=3 , merch=False)
}
# refund rate
REFUND     = 0.03      # φ
# humanitix approximate fee per ticket
PLATFORM_F = 0.04      
# these are fixed costs, basically things like prizes etc
F_FIXED    = 5000
#Sponsor is how much we use from the bank account from sponsors
SPONSOR    = 5000
CATERING   = 4000
#cost of merch per unit
MERCH_UNIT = 20

# ──────────── CORE FUNCTIONS ────────────

# the math below is correct, dont need to change any of it just the inputs above
def price_tiers(tiers: dict) -> pd.DataFrame:
    df = pd.DataFrame.from_dict(tiers, orient="index")
    df.index.name = "Tier"
    df.reset_index(inplace=True)

    head_total = df["sold"].sum()
    v_cat = CATERING / head_total          # $ per head catering
    df["v"] = v_cat + df["merch"].map({True: MERCH_UNIT, False: 0})

    gap_total = F_FIXED - SPONSOR
    df["gap"] = gap_total * df["sold"] / head_total        # proportional

    denom = (1 - REFUND) * df["sold"]
    df["P_net"]   = df["v"] + df["gap"] / denom
    df["P_gross"] = df["P_net"] / (1 - PLATFORM_F)

    return df[["Tier", "sold", "v", "gap", "P_net", "P_gross"]]

def simple_price(headcount: int, *, with_merch=False) -> dict:
    if headcount <= 0:
        raise ValueError("headcount must be positive")
    v = CATERING / headcount + (MERCH_UNIT if with_merch else 0)
    P_net = v + (F_FIXED - SPONSOR) / ((1 - REFUND) * headcount)
    P_gross = P_net / (1 - PLATFORM_F)
    return dict(P_net=P_net, P_gross=P_gross, var_cost=v)

# ──────────── DEMO ────────────
if __name__ == "__main__":
    # 1) hackathon tier pricing
    if TIERS:
        print("\n=== tier break-even prices ===")
        print(price_tiers(TIERS).to_string(index=False,
              float_format=lambda x: f"{x:,.2f}"))

    # 2) simple single-price event (100 seats, base ticket)
    # change the headcount number to approximate attendance
    print("\n=== simple event (100 seats) ===")
    print(simple_price(100, with_merch=False))

    #    simple ticket that bundles merch (40 merch tickets expected)
    # this function is an approixmation for merch buyers
    print("\n=== simple event (40 merch seats) ===")
    print(simple_price(40, with_merch=True))
