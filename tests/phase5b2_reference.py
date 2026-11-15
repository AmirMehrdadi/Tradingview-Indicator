"""Synthetic optional predicates and selected-candidate state, never execution."""
import math
from tests.phase5b1_reference import Context, State as BaselineState, decide, accept, confirmed_pivot, finite
from tests.phase5a_reference import ANCHOR, START, END, STEP, HOUR, Reference, consumed_hour

REGISTRY = dict(zip(('C01','C02','C03','C04','C05','C06','C07','C08','C09','C10','C11','C12'),
                   ((),('R',),('H',),('V',),('M',),('Q',),('R','H'),('R','V'),('R','M'),('H','V'),('R','H','Q'),('R','H','V','M','Q'))))
BITS = {'R':1,'H':2,'V':4,'M':8,'Q':16}


class Wilder:
    def __init__(self):
        self.count, self.total, self.value = 0, 0.0, None

    def feed(self, value):
        if not finite(value):
            return None
        if self.value is None:
            self.count += 1
            self.total += value
            if self.count == 14:
                self.value = self.total/14.0
        else:
            self.value = (1.0/14)*value+(1-1.0/14)*self.value
        return self.value


def oscillator_series(bars, atr):
    plus, minus, adx, gain, loss = (Wilder() for _ in range(5))
    adxs, rsis, movements = [], [], []
    for i,b in enumerate(bars):
        pdm = mdm = g = l = None
        if i:
            prev = bars[i-1]
            up, down = b.high-prev.high, prev.low-b.low
            pdm = up if up > down and up > 0 else 0.0
            mdm = down if down > up and down > 0 else 0.0
            g, l = max(b.close-prev.close,0), max(prev.close-b.close,0)
        movements.append((pdm,mdm))
        p,m = plus.feed(pdm),minus.feed(mdm)
        dx = None
        if finite(p,m,atr[i]):
            if atr[i] == 0 and p == m == 0:
                positive = negative = 0.0
            elif atr[i] > 0:
                positive,negative = 100.0*p/atr[i],100.0*m/atr[i]
            else:
                positive = negative = None
            if finite(positive,negative):
                dx = 0.0 if positive+negative == 0 else 100*abs(positive-negative)/(positive+negative)
        adxs.append(adx.feed(dx))
        g,l = gain.feed(g),loss.feed(l)
        rsi = None if not finite(g,l) else 50.0 if g==l==0 else 100.0 if l==0 else 0.0 if g==0 else 100-100/(1+g/l)
        rsis.append(rsi)
    return adxs,rsis,movements


def regime(adx,fast,slow,atr,past):
    if len(past)!=96 or not finite(adx,fast,slow,atr,*past):
        return False
    values=sorted(past)
    median=(values[47]+values[48])/2.0
    return adx>=20 and abs(fast-slow)>=.25*atr and atr<=2*median


def relative_volume(current,past):
    return len(past)==20 and finite(current,*past) and min(current,*past)>=0 and current>=1.2*(sum(past)/20)


def momentum(rsi,d):
    return finite(rsi) and (rsi>=55 if d==1 else rsi<=45 if d==-1 else False)


def higher(hour,d):
    if hour is None:
        return False
    ema,old,close,end,count=hour
    return finite(ema,old,close) and count>=60 and (close>ema>old if d==1 else close<ema<old if d==-1 else False)


def quality(body,span,atr,risk,levels,entry,d):
    if not finite(body,span,atr,risk,entry) or risk<=0:
        return False
    eligible=[d*(v-entry) for v in levels if finite(v) and d*(v-entry)>0]
    return bool(eligible) and body<=1.2*atr and span<=1.8*atr and min(eligible)>=1.5*risk


class Hours:
    def __init__(self):
        self.numeric, self.values = Reference(HOUR), {}
        self.quarantine_from = None

    def feed(self,t,ohlc):
        was_poisoned = self.numeric.poisoned
        result=self.numeric.feed(t,ohlc)
        if not was_poisoned and self.numeric.poisoned:
            self.quarantine_from = t+HOUR
        if result is not None:
            self.values[t+HOUR]=(result[1],ohlc[3],result[4])
        return result

    def at(self,execution_open):
        return None if self.quarantine_from is not None and execution_open >= self.quarantine_from else consumed_hour(execution_open,self.values)


def flags_for(bars,fast,slow,atr,volumes,hours,plan):
    i=len(bars)-1;b=bars[-1];d=plan['direction']
    adx,rsi,_=oscillator_series(bars,atr)
    opposing=[]
    for j in range(max(3,i-80),i-2):
        if confirmed_pivot(bars,j+3,-d)==j:
            opposing.append(bars[j].high if d==1 else bars[j].low)
    return {'R':regime(adx[-1],fast[-1],slow[-1],atr[-1],atr[max(0,i-96):i]),
            'H':higher(hours.at(b.time) if hours is not None else None,d),
            'V':relative_volume(volumes[-1],volumes[max(0,i-20):i]),
            'M':momentum(rsi[-1],d),
            'Q':quality(abs(b.close-b.open),b.high-b.low,atr[-1],plan['risk'],opposing,b.close,d)}


def selected(plan,flags,candidate,context,enabled):
    if candidate not in REGISTRY:
        raise ValueError('UNREGISTERED_CANDIDATE')
    if plan is None or not enabled or context.busy or context.daily_stop:
        return None
    if any(flags.get(name) is not True for name in REGISTRY[candidate]):
        return None
    key=(candidate,plan['direction'],plan['pullback_id'])
    if key in context.consumed:
        return None
    result=dict(plan,candidate=candidate,filter_bits=sum(BITS[x] for x in REGISTRY[candidate]))
    result['decision_id']=plan['decision_id'].replace(':C01:',':'+candidate+':')
    context.consumed.add(key)
    return result


class Diagnostic:
    def __init__(self,candidate='C01',balance=10000.0,busy=False,daily_stop=False,enabled=False):
        if candidate not in REGISTRY:
            raise ValueError('UNREGISTERED_CANDIDATE')
        self.candidate,self.enabled=candidate,enabled
        self.context=Context(balance,busy,daily_stop)
        self.baseline,self.volumes=BaselineState(),[]

    def feed(self,t,ohlc,volume,hours=None,confirmed=True):
        plan,error=self.baseline.feed(t,ohlc,self.context,confirmed)
        if error=='UNAVAILABLE':
            return None
        self.volumes.append(volume)
        if plan is None:
            return None
        s=self.baseline
        flags=flags_for(s.bars,s.fast,s.slow,s.atr,self.volumes,hours,plan)
        return selected(plan,flags,self.candidate,self.context,self.enabled)
