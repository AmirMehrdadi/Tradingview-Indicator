"""UNVALIDATED in-memory synthetic lifecycle. Not a TradingView broker emulator."""
from dataclasses import dataclass, asdict
from copy import deepcopy
import math
import json

ANCHOR, START, END = 1793491200000, 1793750400000, 1796083200000
STEP, DAY = 900000, 86400000
SYNTHETIC = 'SYNTHETIC_FIXTURE_ONLY'
FEE, FRICTION = .00055, .0002
CANDIDATES = tuple('C%02d'%i for i in range(1,13))


class FixtureError(ValueError):
    pass


def check(ok, message):
    if not ok:raise FixtureError(message)


def finite(*values):
    return all(type(v) in (float,int) and math.isfinite(v) for v in values)


@dataclass(frozen=True)
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float
    provenance: str = SYNTHETIC


@dataclass(frozen=True)
class Decision:
    candidate: str
    signal_close: int
    pullback_id: int
    side: int
    entry_ref: float
    sl_ticks: int
    tp1_ticks: int
    tp2_ticks: int
    steps: int
    provenance: str = SYNTHETIC


@dataclass
class Position:
    decision: Decision
    entry_id: str
    fill: float
    remaining: list
    exited: int = 0
    state: str = 'OPEN'


class Lifecycle:
    def __init__(self,candidate='C01',fixture_id='fixture:unit'):
        check(candidate in CANDIDATES,'CANDIDATE')
        check(type(fixture_id) is str and fixture_id.startswith('fixture:'),'FIXTURE_PROVENANCE')
        self.candidate,self.fixture_id=candidate,fixture_id
        self.cash=self.settled=self.day_start=10000.0
        self.day=START//DAY
        self.daily_stop=self.ended=self.quarantined=False
        self.pending=self.position=None
        self.last_close=self.last_close_price=None
        self.consumed,self.fill_ids,self.decision_ids=set(),set(),set()
        self.events,self.completed,self.censored=[],[],[]
        self.quality=set()

    @property
    def state(self):
        return 'ENDED' if self.ended else 'PENDING_ENTRY' if self.pending else 'OPEN' if self.position else 'FLAT'

    def event(self,name,t,phase,**data):
        self.events.append(dict(name=name,time=t,phase=phase,candidate=self.candidate,**data))

    def reset_day(self,t):
        if t//DAY != self.day:
            self.day=t//DAY;self.day_start=self.settled;self.daily_stop=False
            self.event('UTC_DAY_RESET',t,'UTC_DAY_RESET')

    def queue(self,d):
        check(type(d) is Decision and d.provenance==SYNTHETIC,'SYNTHETIC_DECISION_REQUIRED')
        check(not self.ended and not self.quarantined,'PATH_UNAVAILABLE')
        check(d.candidate==self.candidate,'CANDIDATE_OWNERSHIP')
        check(type(d.signal_close) is int and START<=d.signal_close<END and d.signal_close%STEP==0,'SIGNAL_WINDOW')
        check(d.signal_close==self.last_close,'SIGNAL_NOT_AT_CONFIRMED_CLOSE')
        check(d.entry_ref==self.last_close_price,'ENTRY_REF_NOT_SIGNAL_CLOSE')
        check(type(d.pullback_id) is int and ANCHOR<=d.pullback_id<d.signal_close and d.pullback_id%STEP==0,'PULLBACK_ID')
        check(type(d.side) is int and d.side in (-1,1),'DIRECTION')
        check(all(type(v) is int for v in (d.sl_ticks,d.tp1_ticks,d.tp2_ticks,d.steps)),'INTEGER_RESERVATIONS')
        check(finite(d.entry_ref) and .1<=d.entry_ref<=1999999.8,'ENTRY_PRICE')
        prices=[x/10. for x in (d.sl_ticks,d.tp1_ticks,d.tp2_ticks)]
        check(all(.1<=x<=1999999.8 for x in prices),'PRICE_BOUNDS')
        sl,tp1,tp2=prices
        check(sl<d.entry_ref<tp1<tp2 if d.side==1 else tp2<tp1<d.entry_ref<sl,'BRACKET_GEOMETRY')
        check(2<=d.steps<=150000 and d.steps//2>=1,'QUANTITY_MIN_MAX')
        amount=d.steps/1000.
        check(amount*d.entry_ref>=5,'ENTRY_NOTIONAL_MIN')
        risk=abs(d.entry_ref-sl);cost=(d.entry_ref+sl)*(FEE+FRICTION)
        check(risk/cost>=2.5,'COST_FLOOR')
        check(amount*(risk+cost)<=.0025*self.settled,'RISK_BUDGET')
        check(amount*d.entry_ref<=2*self.settled,'NOTIONAL_CAP')
        key=(self.candidate,d.side,d.pullback_id)
        if self.pending is not None or self.position is not None or self.daily_stop or key in self.consumed:
            return False
        eid=f'{self.fixture_id}:Research:{self.candidate}:November2026:{d.signal_close-STEP}:{d.side}'
        check(eid not in self.decision_ids,'DUPLICATE_DECISION')
        self.pending=(d,eid)
        self.consumed.add(key);self.decision_ids.add(eid)
        first=d.steps//2
        self.event('QUEUED',d.signal_close,'SIGNAL_CLOSE',entry_id=eid,reservations=[first,d.steps-first],
                   bracket_ids=[eid+':L1',eid+':L2'],oca_ids=[eid+':OCA1',eid+':OCA2'])
        self.invariants()
        return True

    def margin(self,raw,t,phase):
        if self.position:
            p=self.position;q=sum(p.remaining)/1000.
            if self.cash+p.decision.side*q*(raw-p.fill)<.5*q*raw:
                if 'MARGIN_MODEL_EVENT' not in self.quality:self.event('MARGIN_MODEL_EVENT',t,phase,remaining_steps=sum(p.remaining))
                self.quality.add('MARGIN_MODEL_EVENT')

    def exit_leg(self,leg,raw,t,phase,kind,steps=None,mark_price=None):
        p=self.position
        check(p is not None and type(leg) is int and leg in (0,1) and p.remaining[leg]>0,'DUPLICATE_OR_ORPHAN_EXIT')
        check(finite(raw) and raw>0 and type(t) is int and phase in ('OPEN','PRIOR_BAR') and kind in ('TP','STOP'),'INVALID_FILL')
        check(steps is None or type(steps) is int and steps==p.remaining[leg],'OVER_OR_UNDER_FILL')
        fid=p.entry_id+':L'+str(leg+1)
        check(fid not in self.fill_ids,'DUPLICATE_FILL')
        qty=p.remaining[leg];amount=qty/1000.;fill=raw*(1-p.decision.side*FRICTION)
        fee=amount*fill*FEE
        realized=p.decision.side*amount*(fill-p.fill)
        self.cash+=realized-fee
        self.fill_ids.add(fid);p.remaining[leg]=0;p.exited+=qty
        self.event('EXIT',t,phase,entry_id=p.entry_id,fill_id=fid,steps=qty,kind=kind,raw=raw,fill=fill)
        if not sum(p.remaining):
            p.state='COMPLETED';self.completed.append(deepcopy(p));self.position=None
            self.settled=self.cash
            self.daily_stop=self.daily_stop or self.settled-self.day_start<=-.01*self.day_start
            self.event('FULL_FLAT_SETTLEMENT',t,phase,entry_id=p.entry_id,daily_stop=self.daily_stop)
        else:self.margin(raw if mark_price is None else mark_price,t,phase)
        self.invariants()

    def stop_all(self,raw,t,phase):
        self.margin(raw,t,phase)
        for k in (0,1):
            if self.position and self.position.remaining[k]:self.exit_leg(k,raw,t,phase,'STOP')

    def _open(self,b):
        t=b.time
        if self.pending:
            d,eid=self.pending
            check(d.signal_close==t,'ENTRY_NOT_NEXT_OPEN')
            self.pending=None
            qty=d.steps/1000.;fill=b.open*(1+d.side*FRICTION);fee=qty*fill*FEE
            if .5*qty*fill+fee>self.cash:
                self.event('ENTRY_REJECTED_MARGIN',t,'OPEN',entry_id=eid,brackets_cancelled=True)
                return
            fid=eid+':ENTRY';check(fid not in self.fill_ids,'DUPLICATE_ENTRY_FILL');self.fill_ids.add(fid)
            self.cash-=fee
            self.position=Position(d,eid,fill,[d.steps//2,d.steps-d.steps//2])
            self.event('ENTRY',t,'OPEN',entry_id=eid,fill_id=fid,steps=d.steps,fill=fill,raw=b.open)
            risk=d.side*(fill-d.sl_ticks/10.)
            if risk<=0:self.quality.add('EXECUTION_ANOMALY')
            elif (risk-abs(d.entry_ref-d.sl_ticks/10.))/abs(d.entry_ref-d.sl_ticks/10.)>.15:self.quality.add('ENTRY_DEVIATION')
            stop_fill=(d.sl_ticks/10.)*(1-d.side*FRICTION)
            anticipated=qty*d.side*(fill-stop_fill)+fee+qty*stop_fill*FEE
            if anticipated>.0025*self.settled:self.quality.add('RISK_OVERRUN')
            if qty*fill>2*self.settled:self.quality.add('NOTIONAL_OVERRUN')
        if not self.position:return
        p=self.position;d=p.decision;self.margin(b.open,t,'OPEN')
        sl=d.sl_ticks/10.
        if d.side*(b.open-sl)<=0 or d.side*(p.fill-sl)<=0:
            if t==d.signal_close:self.quality.update(('ENTRY_AT_OR_BEYOND_SL','EXECUTION_ANOMALY'))
            self.stop_all(b.open,t,'OPEN');return
        for k,target in enumerate((d.tp1_ticks/10.,d.tp2_ticks/10.)):
            if not self.position:break
            if p.remaining[k] and d.side*(b.open-target)>=0:
                self.exit_leg(k,target,t,'OPEN','TP',mark_price=b.open)
            elif p.remaining[k] and t==d.signal_close and d.side*(p.fill-target)>=0:
                self.quality.update(('FILL_FRICTION_CROSSED_TP','EXECUTION_ANOMALY'))

    def _process(self,b):
        check(not self.ended and not self.quarantined,'PATH_UNAVAILABLE')
        check(type(b) is Candle and b.provenance==SYNTHETIC,'SYNTHETIC_CANDLE_REQUIRED')
        check(type(b.time) is int and ANCHOR<=b.time<END and b.time%STEP==0,'CANDLE_WINDOW')
        check(self.last_close is None or b.time==self.last_close,'GAP_OR_REPLAY')
        check(finite(b.open,b.high,b.low,b.close) and 0<b.low<=min(b.open,b.close)<=max(b.open,b.close)<=b.high,'INVALID_OHLC')
        self.reset_day(b.time)
        self._open(b)
        if self.position:
            p=self.position;d=p.decision;end=b.time+STEP
            stop=b.low<=d.sl_ticks/10. if d.side==1 else b.high>=d.sl_ticks/10.
            favorable=b.high if d.side==1 else b.low
            if stop:
                if any(p.remaining[k] and d.side*(favorable-target)>=0 for k,target in enumerate((d.tp1_ticks/10.,d.tp2_ticks/10.))):self.quality.add('UNCERTAIN_INTRABAR_ORDER')
                self.stop_all(d.sl_ticks/10.,end,'PRIOR_BAR')
            else:
                for k,target in enumerate((d.tp1_ticks/10.,d.tp2_ticks/10.)):
                    if not self.position:break
                    if p.remaining[k] and d.side*(favorable-target)>=0:
                        self.margin(target,end,'PRIOR_BAR');self.exit_leg(k,target,end,'PRIOR_BAR','TP')
                if self.position:
                    self.margin(b.low if d.side==1 else b.high,end,'PRIOR_BAR');self.margin(b.close,end,'PRIOR_BAR')
        self.last_close=b.time+STEP
        self.last_close_price=b.close
        if self.last_close==END:
            check(self.pending is None,'PENDING_AT_END')
            if self.position:
                self.position.state='CENSORED';self.censored.append(deepcopy(self.position));self.position=None
            self.ended=True;self.event('PARTITION_END',END,'PARTITION_END')
        else:self.reset_day(self.last_close)
        self.invariants()

    def process(self,b):
        trial=deepcopy(self)
        try:trial._process(b)
        except FixtureError:
            self.quarantined=True
            raise
        self.__dict__.update(trial.__dict__)

    def invariants(self):
        check(not(self.pending and self.position),'OVERLAPPING_EXPOSURE')
        positions=self.completed+self.censored+([self.position] if self.position else [])
        for p in positions:
            check(all(type(x) is int and x>=0 for x in p.remaining),'REMAINING_STEPS')
            check(p.exited+sum(p.remaining)==p.decision.steps,'QUANTITY_CONSERVATION')
            if p.state=='COMPLETED':check(sum(p.remaining)==0,'UNDERFILLED_COMPLETION')
            check(p.decision.candidate==self.candidate,'FOREIGN_POSITION')
        check(finite(self.cash,self.settled,self.day_start),'ACCOUNTING_FINITE')

    def serialized(self):
        obj={'scope':SYNTHETIC,'validation_status':'UNVALIDATED','candidate':self.candidate,'state':self.state,'events':self.events,
             'cash':self.cash,'settled':self.settled,'day_start':self.day_start,'daily_stop':self.daily_stop,
             'completed':[asdict(p) for p in self.completed],'censored':[asdict(p) for p in self.censored],
             'position':asdict(self.position) if self.position else None,
             'pending': [asdict(self.pending[0]),self.pending[1]] if self.pending else None,
             'consumed':sorted(self.consumed),'quality':sorted(self.quality),'quarantined':self.quarantined,
             'historical_funding':'PARTIAL_DATA','funding_implementation':'NOT_IMPLEMENTED'}
        return (json.dumps(obj,sort_keys=True,allow_nan=False)+'\n').encode()
