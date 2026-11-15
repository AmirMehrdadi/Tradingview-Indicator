"""UNVALIDATED fixture lifecycle plus frozen decision reference, no I/O."""
from tests.phase5b1_reference import State as SignalHistory, Context
from tests.phase5b2_reference import REGISTRY, BITS, Hours, flags_for
from .state import Lifecycle, Candle, Decision, FixtureError, check, SYNTHETIC, ANCHOR, START, END, STEP


class CandidatePath:
    """One candidate, independently owned numerical, hourly and execution state."""
    def __init__(self,candidate='C01',fixture_id='fixture:combined',enabled=False):
        check(candidate in REGISTRY,'CANDIDATE')
        check(type(enabled) is bool,'ENABLED_BOOLEAN_REQUIRED')
        self.candidate,self.enabled=candidate,enabled
        self.model=Lifecycle(candidate,fixture_id)
        self.history,self.hours,self.volumes=SignalHistory(),Hours(),[]
        self.decisions=[]

    def add_hour(self,b):
        check(type(b) is Candle and b.provenance==SYNTHETIC,'SYNTHETIC_HOUR_REQUIRED')
        check(type(b.time) is int and ANCHOR<=b.time<END and b.time%3600000==0,'HOUR_WINDOW')
        check(self.model.last_close is not None and b.time+3600000<=self.model.last_close,'FUTURE_HOUR')
        return self.hours.feed(b.time,(b.open,b.high,b.low,b.close))

    def offer_decision(self,d,flags):
        """Unit seam for explicit prevalidated SYNTHETIC decision fixtures only."""
        check(type(d) is Decision and d.provenance==SYNTHETIC,'SYNTHETIC_DECISION_REQUIRED')
        check(d.candidate==self.candidate,'CANDIDATE_OWNERSHIP')
        check(type(flags) is dict,'FIXTURE_FILTER_BITS_REQUIRED')
        if not self.enabled or any(flags.get(f) is not True for f in REGISTRY[self.candidate]):return False
        accepted=self.model.queue(d)
        if accepted:
            self.decisions.append({'candidate':self.candidate,'signal_close':d.signal_close,
                                   'filter_bits':sum(BITS[f] for f in REGISTRY[self.candidate]),
                                   'entry_id':self.model.pending[1],'scope':SYNTHETIC,'classification':'QUEUED_NOT_FILLED','validation_status':'UNVALIDATED'})
        return accepted

    def feed(self,b,volume=None,hour=None,confirmed=True):
        check(type(b) is Candle and b.provenance==SYNTHETIC,'SYNTHETIC_CANDLE_REQUIRED')
        check(type(b.time) is int and ANCHOR<=b.time<END,'INPUT_WINDOW')
        if not confirmed:return None
        expected=ANCHOR if self.history.numeric.n==0 else self.history.numeric.last
        if b.time!=expected:
            self.model.quarantined=True
            raise FixtureError('INDICATOR_ANCHOR_OR_GAP')
        # Current completed bar executes OPEN and PRIOR_BAR first. Numerical
        # signal-close evaluation then sees only this bar and settled snapshots.
        if hour is not None:
            check(type(hour) is Candle and hour.provenance==SYNTHETIC,'SYNTHETIC_HOUR_REQUIRED')
            check(type(hour.time) is int and ANCHOR<=hour.time<END and hour.time%3600000==0,'HOUR_WINDOW')
            check(hour.time+3600000<=b.time+STEP,'FUTURE_HOUR')
        self.model.process(b)
        if hour is not None:self.add_hour(hour)
        ctx=Context(self.model.settled,self.model.pending is not None or self.model.position is not None,self.model.daily_stop,
                    {(side,pid) for cid,side,pid in self.model.consumed if cid==self.candidate})
        plan,error=self.history.feed(b.time,(b.open,b.high,b.low,b.close),ctx,True)
        self.volumes.append(volume)
        if plan is None or not self.enabled:return None
        s=self.history
        flags=flags_for(s.bars,s.fast,s.slow,s.atr,self.volumes,self.hours,plan)
        d=Decision(self.candidate,plan['signal_close'],plan['pullback_id'],plan['direction'],plan['entry_ref'],
                   plan['sl_ticks'],plan['tp1_ticks'],plan['tp2_ticks'],plan['steps'][0])
        return self.decisions[-1] if self.offer_decision(d,flags) else None
