"""Pure synthetic presentation contract; does not parse, compile or execute Pine."""
from dataclasses import dataclass
from research.fixture_state_v1.state import Decision,Candle,SYNTHETIC,ANCHOR,START,END,STEP,check
from tests.phase5b3_pine_audit_reference import canonical_id
from tests.phase5b2_reference import REGISTRY

MANUAL_CAPACITY=(END-START)//STEP


@dataclass(frozen=True)
class Settings:
    markers:bool=True
    levels:bool=True
    dashboard:bool=True
    quality:bool=False
    alerts:bool=False


@dataclass(frozen=True)
class Snapshot:
    candidate:str='C01'
    owner:str=''
    phase:int=0
    available:bool=True
    has_filled:bool=False
    total:int=0
    exited:int=0
    remaining:tuple=(0,0)
    quality:int=0
    last_bar:int=START-STEP
    queued_close:int=START


def snapshot(model,plan=None,run='phase5b3-pine-v1'):
    p=model.position
    archived=None
    if plan is not None:
        archived=next((v for v in reversed(model.completed+model.censored) if v.decision==plan),None)
    current=p if p is not None else archived
    has_filled=current is not None and plan is not None and current.decision==plan
    phase=4 if model.ended and model.censored else 3 if model.ended else 1 if model.pending else 2 if p is not None else 0
    return Snapshot(model.candidate,canonical_id(run,model.candidate,plan.signal_close-STEP,plan.side) if plan else '',
                    phase,not model.quarantined,has_filled,plan.steps if plan else 0,
                    current.exited if has_filled else 0,tuple(current.remaining) if has_filled else (0,0),
                    last_bar=model.last_close-STEP if model.last_close is not None else None,queued_close=plan.signal_close if plan else None)


class Presentation:
    """Only owns synthetic graphical/notification records, never a model reference."""
    def __init__(self,settings=Settings()):
        self.settings=settings;self.owner='';self.plan=None;self.signal_open=None;self.expiry=None;self.expired=False
        self.last_close=None;self.last_alert='';self.markers=[];self.alerts=[];self.objects=[];self.deleted=[]
        self.dashboard=None;self.max_lines=self.max_labels=0
        self.manual_records=[];self.next_expiry=0;self.presentation_blocked=False

    def clear(self):
        self.deleted.extend(self.objects);self.objects=[]

    def owned(self,s):return bool(self.owner) and self.owner==s.owner and self.plan is not None and self.plan.signal_close==s.queued_close

    def research_status(self,s,enabled=True):
        if not enabled:return 'DISABLED'
        if not s.available:return 'UNKNOWN'
        if not self.owner:return 'NO SETUP'
        if not self.owned(s):return 'UNKNOWN'
        if s.phase==1:return 'QUEUED — NOT FILLED'
        if s.phase==2 and s.has_filled:return 'TP1 FILLED / LEG 2 OPEN' if s.remaining[0]==0 and s.remaining[1]>0 else 'HYPOTHETICAL OPEN'
        if s.phase==0 and s.has_filled and s.exited==s.total and sum(s.remaining)==0:return 'HYPOTHETICAL CLOSED'
        if s.phase==0 and not s.has_filled:return 'ENTRY REJECTED'
        return 'CENSORED' if s.phase==4 else 'UNKNOWN'

    def observe(self,bar,s,accepted_plan=None,enabled=False,confirmed=True,realtime=False,last=True,viewport=None):
        check(type(bar) is Candle and bar.provenance==SYNTHETIC,'SYNTHETIC_ONLY')
        close=bar.time+STEP;window=confirmed and ANCHOR<=bar.time<END and START<=close<END
        manual_clock=confirmed and ANCHOR<=bar.time<END and START<=close<=END
        available=enabled and not self.presentation_blocked and s.available and s.last_bar is not None and (s.last_bar==bar.time if confirmed else s.last_bar+STEP==bar.time)
        new=accepted_plan is not None and window and available and s.phase==1 and bool(s.owner) and s.owner!=self.owner and (self.last_close is None or close>self.last_close)
        if new and len(self.manual_records)>=MANUAL_CAPACITY:
            self.presentation_blocked=True;available=False;new=False
        if manual_clock and available:
            while self.next_expiry<len(self.manual_records):
                record=self.manual_records[self.next_expiry]
                if record['deadline']>close:break
                record['expired']=True;record['expired_at']=close;self.next_expiry+=1
        if new:
            check(type(accepted_plan) is Decision and accepted_plan.provenance==SYNTHETIC,'SYNTHETIC_PLAN_ONLY')
            check(accepted_plan.candidate==s.candidate and accepted_plan.signal_close==close,'OWNERSHIP')
            self.clear();self.owner=s.owner;self.plan=accepted_plan;self.signal_open=bar.time
            self.expiry=close+2*STEP;self.expired=False;self.last_close=close
            self.manual_records.append(dict(owner=self.owner,signal_close=close,deadline=self.expiry,expired=False,expired_at=None))
            if self.settings.markers:self.markers.append((self.owner,bar.time,close,self.plan.side))
        if manual_clock and available and self.owner and close>=self.expiry:self.expired=True
        active=available and self.owned(s) and s.phase in (1,2)
        visible=window and available and self.settings.levels and self.owned(s) and (not self.expired or active)
        if visible:
            right=min(max(close,self.plan.signal_close+STEP),END-1)
            check(START<=self.plan.signal_close<=right<END,'OBJECT_BOUNDS')
            prices=(self.plan.entry_ref,self.plan.sl_ticks/10.,self.plan.tp1_ticks/10.,self.plan.tp2_ticks/10.)
            self.objects=[(self.owner,name,self.plan.signal_close,right,price,color) for name,price,color in zip(('ENTRY_REF','SL','TP1','TP2'),prices,('yellow','red','blue','green'))]
            self.max_lines=max(self.max_lines,len(self.objects));self.max_labels=max(self.max_labels,len(self.objects))
        elif confirmed or not enabled or not self.settings.levels or not available:self.clear()
        if new and self.settings.alerts and realtime and self.owner!=self.last_alert:
            self.alerts.append(dict(owner=self.owner,candidate=s.candidate,direction='LONG' if self.plan.side==1 else 'SHORT',
                signal_close=close,entry_ref=self.plan.entry_ref,sl=self.plan.sl_ticks/10.,tp1=self.plan.tp1_ticks/10.,tp2=self.plan.tp2_ticks/10.,
                classification='UNVALIDATED — RESEARCH / MANUAL SIGNALS',actual='REAL_POSITION_UNKNOWN',kind='MANUAL_NOTIFICATION_NO_ORDER'))
            self.last_alert=self.owner
        if last:
            clock=close if confirmed else bar.time
            viewport_ok=viewport is not None and viewport[0]<=viewport[1] and START<=viewport[0]+STEP and viewport[1]+STEP<END
            display=START<=clock<END
            if self.settings.dashboard and display and viewport_ok:
                owns=available and self.owned(s);direction_active=owns and (not self.expired or active)
                self.dashboard=dict(title='UNVALIDATED — RESEARCH / MANUAL SIGNALS',candidate=s.candidate,filters=' '.join(('B',)+REGISTRY[s.candidate]),
                    direction=('LONG' if self.plan.side==1 else 'SHORT') if direction_active else 'NEUTRAL',
                    phase=('FLAT','PENDING_ENTRY','OPEN','ENDED','CENSORED')[s.phase] if available else 'UNKNOWN',
                    research=self.research_status(s,enabled) if available or not enabled else 'UNKNOWN',manual='NONE — DISABLED' if not enabled else 'UNKNOWN' if not available else 'NONE' if not self.owner else 'EXPIRED — UNCONFIRMED' if self.expired else 'UNCONFIRMED',
                    actual='REAL_POSITION_UNKNOWN',quality=s.quality if self.settings.quality and available else None)
            else:self.dashboard=None
            if not display:self.clear()
        return new
