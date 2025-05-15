# Ticket-Pricing Reference Implementation


*The first half derives the break-even formula step-by-step.*  
*The second half maps every symbol to the Python variables used in
`tickets.py`.*

---

## 1  Declare (then fill-in) your inputs

| Symbol | What **you** type in | Where it normally comes from |
|--------|----------------------|------------------------------|
| `F`    | **total** fixed costs | venue, AV, insurance, marketing |
| `v`    | variable cost **per attendee** | catering ÷ head-count, plus optional merch |
| `S`    | sponsorship / grants already locked in | signed agreements |
| `φ`    | refund rate (0 – 1) | past events or policy |
| `c_ref`| payment-processor refund fee | Stripe, PayPal schedule |
| `Q(P)` | demand curve – expected sales at price `P` | old ticket data or a survey |
| `P`    | ticket price you’re solving for | – |

---

## 2  Choose a demand curve

Most clubs start with a **linear** curve:

$$
Q(P)=a-bP
$$

* `a` = intercept (tickets if it were free)  
* `b` = slope (tickets lost per \$1 price rise)  
  `dQ/dP = –b` is constant.

If you prefer, swap in a constant-elasticity form

$$
Q(P)=A\,P^{-\varepsilon},\quad \varepsilon>0
$$


---

## 3  How many people actually show up?

Only a fraction `(1 − φ)` keep their ticket:

$$
\tilde Q(P)=(1-\phi)\,Q(P)
$$

---

## 4  Write the revenue-and-cost pieces

| Piece | Formula | Why |
|-------|---------|-----|
| Revenue kept | $(1-\phi)P\,Q(P)$ | refunds paid back |
| Fixed cost | $F$ | independent of head-count |
| Variable cost | $(1-\phi)v\,Q(P)$ | only show-ups consume |
| Refund fee | $c_{\text{ref}}\phi\,Q(P)$ | optional |
| Sponsorship | $S$ | offsets the gap |

---

## 5  Profit function

$$
\pi(P)=
\underbrace{(1-\phi)P\,Q(P)}_{\text{kept revenue}}
+S
-\underbrace{F}_{\text{fixed}}
-\underbrace{(1-\phi)v\,Q(P)}_{\text{per-head}}
-\underbrace{c_{\text{ref}}\phi\,Q(P)}_{\text{refund fee}}
$$

---

## 6  Break-even condition

Set $\pi(P)=0$ and drop the refund-fee term if you like:

$$
(1-\phi)\,(P-v)\,Q(P)=F-S
$$

Everything on the left depends on `P`; everything on the right is a
constant you **must** cover.

---

## 7  Insert the linear curve → quadratic

$$
(1-\phi)\,(a-bP)\,(P-v)=F-S
$$

Expand or feed into a spreadsheet’s quadratic solver.  
Pick the root that satisfies **both**

* $P>v$   (price covers per-head cost)  
* $Q(P)>0$ (positive demand).

---


## 8  Final constant-refund, single-tier formula (keep it!)

$$
(1-\phi)\,(P-v)\,Q(P)=F-S
$$

_Left-hand_: contribution per attendee × non-refunded attendees  
_Right-hand_: the fixed-cost gap that must be filled.

---

## 9  The ultra-simple shortcut (no demand curve)

If you **don’t** model demand (just assume `Q_est` tickets will be sold):

$$
P_{\text{net}} = v + \frac{F-S}{(1-\phi)\,Q_{\text{est}}}
$$

Add platform fee `f` to get the sticker price:

$$
P_{\text{gross}} = \frac{P_{\text{net}}}{1-f}.
$$

---

## 10  How the code mirrors the maths

| Python variable | Math symbol | Notes |
|-----------------|-------------|-------|
| `REFUND` | φ | refund rate |
| `F_FIXED` | F | total fixed costs |
| `SPONSOR` | S | sponsorship dollars |
| `CATERING / head_total` | part of `v` | per-head food |
| `MERCH_UNIT` | part of `v` | shirt/hoodie cost (if tier has merch) |
| `gap` | $(F-S)\times\text{weight}$ | each tier’s share of the gap |
| `P_net` | $v+\dfrac{\text{gap}}{(1-φ)Q}$ | break-even price **you keep** |
| `P_gross` | $P_\text{net}/(1-f)$ | price shown on ticket site |

*Function `price_tiers()`* implements the proportional gap split for
hackathons.  

*Function `simple_price()`* applies the ultra-simple shortcut for any
single-price event.

