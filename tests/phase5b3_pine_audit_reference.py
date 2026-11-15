"""Fixture-only audit observer of the preserved Lifecycle, not a Pine interpreter.

Economic transitions remain owned by the preserved engine. This observer records
new canonical IDs and immutable primitive snapshots without changing that engine.
"""
from research.fixture_state_v1.state import Lifecycle, FixtureError, check, START, STEP

BITS={'ENTRY_DEVIATION':1,'EXECUTION_ANOMALY':2,'RISK_OVERRUN':4,'NOTIONAL_OVERRUN':8,
      'MARGIN_MODEL_EVENT':16,'UNCERTAIN_INTRABAR_ORDER':32,'ENTRY_AT_OR_BEYOND_SL':64,'FILL_FRICTION_CROSSED_TP':128}
CAPACITY=20000
BAR_RESERVE=16
DEFAULT_RUN='phase5b3-pine-v1'


def canonical_id(run,candidate,bar_open,side):
    allowed='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
    check(type(run) is str and 1<=len(run)<=64 and all(x in allowed for x in run),'INVALID_RUN_ID')
    return f'{run}/Research/{candidate}/November2026/{bar_open}/{side}'


class AuditedLifecycle(Lifecycle):
    """Audit instrumentation only; inherited serialized() excludes this tape.

    The unit seam permits isolated prevalidated fixtures, as in the preserved
    Lifecycle. CandidatePath supplies strict full-stream anchoring separately.
    """
    def __init__(self,candidate='C01',fixture_id='fixture:combined',run_id=DEFAULT_RUN,capacity=CAPACITY):
        super().__init__(candidate,fixture_id)
        canonical_id(run_id,candidate,START-STEP,1)
        self.run_id,self.capacity=run_id,capacity
        self.tape=[];self.trade_id='';self.plan=None;self.audit_quality=set();self.trade_fills=0
        self.audit_blocked=False;self.audit_bar=None;self.last_mark=None

    def reserve(self,slots):
        if len(self.tape)+slots>self.capacity:
            self.audit_blocked=self.quarantined=True
            raise FixtureError('AUDIT_CAPACITY_EXHAUSTED')

    def record(self,kind,t,phase,fill_id='',steps=0,raw=None,price=None,fee=None,leg=-1,release=False,classification='',position=None):
        self.reserve(1)
        p=position if position is not None else self.position
        remaining=list(p.remaining) if p else [0,0]
        d=self.plan
        first=d.steps//2 if d else 0
        self.tape.append(dict(sequence=len(self.tape)+1,trade_id=self.trade_id,kind=kind,fill_id=fill_id,
            time=t,phase=phase,leg=leg,steps=steps,raw_price=raw,price=price,fee=fee,
            remaining=remaining,reservations=[first,d.steps-first] if d else [0,0],
            exited=p.exited if p else (d.steps if d and self.trade_fills else 0),total=d.steps if d else 0,
            entered=d.steps if d and self.trade_fills else 0,fill_count=self.trade_fills,observation_price=self.last_mark,
            exposure_notional=sum(remaining)/1000.*self.last_mark if self.last_mark is not None else None,
            occupied=self.pending is not None or p is not None,release_time=t if release else None,
            quality=sorted(self.audit_quality),quality_code=sum(BITS[x] for x in self.audit_quality),
            classification=classification or kind,cash=self.cash,settled=self.settled,
            day=self.day,day_start=self.day_start,daily_stop=self.daily_stop))

    def tag(self,name,t,phase):
        if name not in self.audit_quality:
            self.audit_quality.add(name);self.record('QUALITY',t,phase,classification=name)

    def event(self,name,t,phase,**data):
        super().event(name,t,phase,**data)
        if name=='QUEUED':
            self.plan=self.pending[0];self.trade_id=canonical_id(self.run_id,self.candidate,self.plan.signal_close-STEP,self.plan.side)
            self.audit_quality=set();self.trade_fills=0;self.last_mark=self.plan.entry_ref
            self.record('PLAN_QUEUED',t,phase,raw=self.plan.entry_ref,classification='QUEUED_NOT_FILLED')
        elif name=='ENTRY':
            p=self.position;d=p.decision;self.trade_fills+=1;self.last_mark=data['raw']
            self.record('ENTRY',t,phase,self.trade_id+'/ENTRY',data['steps'],data['raw'],data['fill'],data['steps']/1000.*data['fill']*.00055)
            actual=d.side*(p.fill-d.sl_ticks/10.);planned=abs(d.entry_ref-d.sl_ticks/10.)
            if actual<=0:self.tag('EXECUTION_ANOMALY',t,phase)
            elif (actual-planned)/planned>.15:self.tag('ENTRY_DEVIATION',t,phase)
            qty=d.steps/1000.;stop_fill=d.sl_ticks/10.*(1-d.side*.0002)
            if qty*d.side*(p.fill-stop_fill)+qty*p.fill*.00055+qty*stop_fill*.00055>.0025*self.settled:self.tag('RISK_OVERRUN',t,phase)
            if qty*p.fill>2*self.settled:self.tag('NOTIONAL_OVERRUN',t,phase)
        elif name=='EXIT':
            leg=int(data['fill_id'][-1])-1;self.trade_fills+=1;self.last_exit_raw=data['raw']
            self.record('EXIT',t,phase,self.trade_id+'/L'+str(leg+1),data['steps'],data['raw'],data['fill'],data['steps']/1000.*data['fill']*.00055,leg,classification=data['kind'])
        elif name=='FULL_FLAT_SETTLEMENT':
            self.record(name,t,phase,raw=self.last_exit_raw,release=True)
        elif name=='ENTRY_REJECTED_MARGIN':
            self.record(name,t,phase,raw=self.audit_bar.open,release=True)
        elif name=='PARTITION_END' and self.censored:
            self.last_mark=self.last_close_price
            self.record('PARTITION_CENSORED',t,phase,raw=self.last_close_price,classification='CENSORED',position=self.censored[-1])

    def queue(self,d):
        # Reserve before the inherited method can mutate a successful plan.
        self.reserve(1)
        return super().queue(d)

    def margin(self,raw,t,phase):
        self.last_mark=raw
        super().margin(raw,t,phase)
        if self.position:
            p=self.position;q=sum(p.remaining)/1000.
            if self.cash+p.decision.side*q*(raw-p.fill)<.5*q*raw:self.tag('MARGIN_MODEL_EVENT',t,phase)

    def exit_leg(self,leg,raw,t,phase,kind,steps=None,mark_price=None):
        self.last_mark=raw if mark_price is None else mark_price
        return super().exit_leg(leg,raw,t,phase,kind,steps,mark_price)

    def stop_all(self,raw,t,phase):
        self.last_mark=raw
        p=self.position
        if p:
            d=p.decision
            if phase=='OPEN' and t==d.signal_close:
                self.tag('ENTRY_AT_OR_BEYOND_SL',t,phase);self.tag('EXECUTION_ANOMALY',t,phase)
            if phase=='PRIOR_BAR':
                favorable=self.audit_bar.high if d.side==1 else self.audit_bar.low
                if any(p.remaining[k] and d.side*(favorable-target)>=0 for k,target in enumerate((d.tp1_ticks/10.,d.tp2_ticks/10.))):self.tag('UNCERTAIN_INTRABAR_ORDER',t,phase)
        return super().stop_all(raw,t,phase)

    def _open(self,b):
        self.last_mark=b.open
        super()._open(b)
        if self.position and self.position.decision.signal_close==b.time:
            p=self.position;d=p.decision
            if any(p.remaining[k] and d.side*(b.open-target)<0 and d.side*(p.fill-target)>=0 for k,target in enumerate((d.tp1_ticks/10.,d.tp2_ticks/10.))):
                self.tag('FILL_FRICTION_CROSSED_TP',b.time,'OPEN');self.tag('EXECUTION_ANOMALY',b.time,'OPEN')

    def process(self,b):
        self.reserve(BAR_RESERVE)
        self.audit_bar=b
        return super().process(b)
