"""Independent Python abstract model of the Pine object's intended state contract.

This does not parse, transpile, compile or execute Pine. Comparisons are Python
reference comparisons, with source/static obligations tested separately.
"""
from copy import deepcopy
from types import SimpleNamespace
from research.fixture_state_v1.state import (Decision,Candle,FixtureError,SYNTHETIC,ANCHOR,START,END,STEP,DAY,check,finite)


class Book:
    def __init__(self,candidate='C01',fixture_id='fixture:combined'):
        self.candidate,self.fixture_id=candidate,fixture_id
        self.phase,self.quarantined=0,False
        self.cash=self.settled=self.day_start=10000.0
        self.day=START//DAY;self.daily_stop=False
        self.last_close=self.last_close_price=None
        self.d=None;self.eid='';self.fill=None
        self.left=[0,0];self.exited=0
        self.consumed=set();self.ids=set()
        self.events=[];self.quality=set();self.completed=[];self.censored=[]

    @property
    def state(self):return {0:'FLAT',1:'PENDING_ENTRY',2:'OPEN',3:'ENDED',4:'ENDED'}[self.phase]
    @property
    def pending(self):return (self.d,self.eid) if self.phase==1 else None
    @property
    def position(self):return SimpleNamespace(remaining=self.left,entry_id=self.eid) if self.phase==2 else None
    @property
    def ended(self):return self.phase>=3

    def reset_day(self,t):
        if self.day!=t//DAY:
            self.day=t//DAY;self.day_start=self.settled;self.daily_stop=False
            self.events.append(('UTC_DAY_RESET',t))

    def queue(self,d):
        check(type(d) is Decision and d.provenance==SYNTHETIC,'SYNTHETIC_DECISION_REQUIRED')
        check(d.candidate==self.candidate and type(d.side) is int and d.side in (1,-1),'OWNER_DIRECTION')
        check(not self.ended and not self.quarantined,'PATH_UNAVAILABLE')
        check(type(d.signal_close) is int and START<=d.signal_close<END and d.signal_close%STEP==0 and self.last_close==d.signal_close,'SIGNAL_TIME')
        check(type(d.pullback_id) is int and ANCHOR<=d.pullback_id<d.signal_close and d.pullback_id%STEP==0,'PULLBACK_ID')
        check(d.entry_ref==self.last_close_price,'REFERENCE_CLOSE')
        check(all(type(x) is int for x in (d.sl_ticks,d.tp1_ticks,d.tp2_ticks,d.steps)),'INTEGER_GRID')
        sl,t1,t2=[x/10. for x in (d.sl_ticks,d.tp1_ticks,d.tp2_ticks)]
        check(finite(d.entry_ref) and all(.1<=v<=1999999.8 for v in (d.entry_ref,sl,t1,t2)),'PRICE_BOUNDS')
        check(sl<d.entry_ref<t1<t2 if d.side==1 else 0<t2<t1<d.entry_ref<sl,'GEOMETRY')
        check(2<=d.steps<=150000 and (d.steps/1000.)*d.entry_ref>=5,'QUANTITY')
        cost=(d.entry_ref+sl)*(.00055+.0002);risk=abs(d.entry_ref-sl);q=d.steps/1000.
        check(risk/cost>=2.5 and q*(risk+cost)<=.0025*self.settled and q*d.entry_ref<=2*self.settled,'BUDGET_COST')
        key=(self.candidate,d.side,d.pullback_id)
        if self.phase!=0 or self.daily_stop or key in self.consumed:return False
        self.d=d;self.eid=f'{self.fixture_id}:Research:{self.candidate}:November2026:{d.signal_close-STEP}:{d.side}'
        self.phase=1;self.left=[0,0];self.exited=0;self.fill=None
        self.consumed.add(key);self.events.append(('QUEUED',d.signal_close,self.eid))
        return True

    def mark(self,raw):
        if self.phase==2 and self.cash+self.d.side*(sum(self.left)/1000.)*(raw-self.fill)<.5*(sum(self.left)/1000.)*raw:
            self.quality.add('MARGIN_MODEL_EVENT')

    def close_leg(self,leg,raw,t,phase,kind,mark=None):
        check(self.phase==2 and type(leg) is int and leg in (0,1) and self.left[leg]>0,'DUPLICATE_OR_ORPHAN_EXIT')
        check(finite(raw) and raw>0 and type(t) is int and phase in ('OPEN','PRIOR_BAR') and kind in ('TP','STOP'),'INVALID_FILL')
        fid=self.eid+':L'+str(leg+1);check(fid not in self.ids,'DUPLICATE_FILL')
        steps=self.left[leg];q=steps/1000.;price=raw*(1-self.d.side*.0002)
        self.cash+=self.d.side*q*(price-self.fill)-q*price*.00055
        self.ids.add(fid);self.left[leg]=0;self.exited+=steps
        self.events.append(('EXIT',t,phase,fid,steps,kind,price))
        if sum(self.left)==0:
            self.phase=0;self.settled=self.cash
            self.daily_stop=self.daily_stop or self.settled-self.day_start<=-.01*self.day_start
            self.completed.append((self.eid,self.exited))
        else:self.mark(raw if mark is None else mark)
        self.invariants()

    def stop(self,raw,t,phase):
        self.mark(raw)
        for k in range(2):
            if self.phase==2 and self.left[k]:self.close_leg(k,raw,t,phase,'STOP')

    def _process(self,b):
        check(not self.ended and not self.quarantined,'UNAVAILABLE')
        check(type(b) is Candle and b.provenance==SYNTHETIC,'SYNTHETIC_CANDLE_REQUIRED')
        check(type(b.time) is int and ANCHOR<=b.time<END and b.time%STEP==0,'WINDOW')
        check(self.last_close is None or b.time==self.last_close,'GAP_REPLAY')
        check(finite(b.open,b.high,b.low,b.close) and 0<b.low<=min(b.open,b.close)<=max(b.open,b.close)<=b.high,'OHLC')
        self.reset_day(b.time)
        if self.phase==1:
            d=self.d;check(d.signal_close==b.time,'NEXT_OPEN')
            q=d.steps/1000.;fill=b.open*(1+d.side*.0002);fee=q*fill*.00055
            if .5*q*fill+fee>self.cash:
                self.phase=0;self.events.append(('ENTRY_REJECTED_MARGIN',b.time,self.eid))
            else:
                check(self.eid+':ENTRY' not in self.ids,'DUPLICATE_ENTRY')
                self.ids.add(self.eid+':ENTRY');self.phase=2;self.fill=fill;self.cash-=fee
                self.left=[d.steps//2,d.steps-d.steps//2]
                self.events.append(('ENTRY',b.time,self.eid,d.steps,fill))
                actual=d.side*(fill-d.sl_ticks/10.);planned=abs(d.entry_ref-d.sl_ticks/10.)
                if actual<=0:self.quality.add('EXECUTION_ANOMALY')
                elif (actual-planned)/planned>.15:self.quality.add('ENTRY_DEVIATION')
                stop_fill=(d.sl_ticks/10.)*(1-d.side*.0002)
                if q*d.side*(fill-stop_fill)+fee+q*stop_fill*.00055>.0025*self.settled:self.quality.add('RISK_OVERRUN')
                if q*fill>2*self.settled:self.quality.add('NOTIONAL_OVERRUN')
        if self.phase==2:
            d=self.d;sl=d.sl_ticks/10.;self.mark(b.open)
            if d.side*(b.open-sl)<=0 or d.side*(self.fill-sl)<=0:
                if b.time==d.signal_close:self.quality.update(('ENTRY_AT_OR_BEYOND_SL','EXECUTION_ANOMALY'))
                self.stop(b.open,b.time,'OPEN')
            else:
                for k,target in enumerate((d.tp1_ticks/10.,d.tp2_ticks/10.)):
                    if self.phase==2 and self.left[k]:
                        if d.side*(b.open-target)>=0:self.close_leg(k,target,b.time,'OPEN','TP',b.open)
                        elif b.time==d.signal_close and d.side*(self.fill-target)>=0:self.quality.update(('FILL_FRICTION_CROSSED_TP','EXECUTION_ANOMALY'))
        if self.phase==2:
            d=self.d;sl=d.sl_ticks/10.;favorable=b.high if d.side==1 else b.low
            if b.low<=sl if d.side==1 else b.high>=sl:
                if any(self.left[k] and d.side*(favorable-target)>=0 for k,target in enumerate((d.tp1_ticks/10.,d.tp2_ticks/10.))):self.quality.add('UNCERTAIN_INTRABAR_ORDER')
                self.stop(sl,b.time+STEP,'PRIOR_BAR')
            else:
                for k,target in enumerate((d.tp1_ticks/10.,d.tp2_ticks/10.)):
                    if self.phase==2 and self.left[k] and d.side*(favorable-target)>=0:
                        self.mark(target);self.close_leg(k,target,b.time+STEP,'PRIOR_BAR','TP')
                if self.phase==2:self.mark(b.low if d.side==1 else b.high);self.mark(b.close)
        self.last_close=b.time+STEP;self.last_close_price=b.close
        if self.last_close==END:
            if self.phase==2:self.censored.append((self.eid,list(self.left),self.exited));self.phase=4
            else:self.phase=3
        else:self.reset_day(self.last_close)
        self.invariants()

    def process(self,b):
        trial=deepcopy(self)
        try:trial._process(b)
        except FixtureError:
            self.quarantined=True;raise
        self.__dict__.update(trial.__dict__)

    def invariants(self):
        if self.phase in (2,4):check(self.exited+sum(self.left)==self.d.steps and min(self.left)>=0,'CONSERVATION')
        check(finite(self.cash,self.settled,self.day_start),'FINITE_ACCOUNTING')

    def snapshot(self):
        return {'phase':self.phase,'remaining':list(self.left),'cash':self.cash,'settled':self.settled,
                'day_start':self.day_start,'daily_stop':self.daily_stop,'quality':sorted(self.quality),'ids':sorted(self.ids),
                'consumed':sorted(self.consumed),'events':self.events,'completed':self.completed,'censored':self.censored,
                'validation':'UNVALIDATED','provenance':SYNTHETIC}
