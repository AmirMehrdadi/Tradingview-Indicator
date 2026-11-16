"""Private aggregate metrics in original closure-event order; no ranking."""
from decimal import Decimal, localcontext
from research.funding_lifecycle.accounting import exact_add


def total(values):
    value = Decimal(0)
    for v in values:
        value = exact_add(value, v)
    return value


def metrics(payload, accounting):
    completed = [e['entry_id'] for e in payload['ledger'] if e['event'] == 'POSITION_CLOSED']
    rows = {r['entry_id']: r for r in accounting['trades']}
    if len(set(completed)) != len(completed) or {k for k,v in rows.items() if v['state']=='COMPLETED'} != set(completed):
        raise ValueError('CLOSURE_ORDER_OR_OWNERSHIP_CHANGED')
    closed = [rows[k] for k in completed]
    nets = [Decimal(t['net_after_funding']) for t in closed]
    rs = [Decimal(t['trade_R_net']) for t in closed]
    gp, gl = total(x for x in nets if x > 0), -total(x for x in nets if x < 0)
    with localcontext() as ctx:
        ctx.prec = 50
        wr = Decimal(sum(x > 0 for x in nets))*100/len(nets) if nets else None
        mean = total(rs)/len(rs) if rs else None
        pf = gp/gl if gl else 'INFINITE' if gp else None
    cumulative = peak = drawdown = Decimal(0)
    for value in rs:
        cumulative = exact_add(cumulative, value)
        peak = max(peak, cumulative)
        drawdown = max(drawdown, exact_add(peak, cumulative.copy_negate()))
    return dict(filled=len(rows), completed=len(closed), censored=sum(t['state']=='CENSORED' for t in rows.values()),
                win_rate=wr, net_usdt=total(nets), mean_R=mean, profit_factor=pf, max_realized_drawdown_R=drawdown,
                funding_completed=total(Decimal(t['attributed_funding']) for t in closed),
                funding_censored=total(Decimal(t['attributed_funding']) for t in rows.values() if t['state']=='CENSORED'))
