"""Two pre-registered exit adapters; reuse the frozen stateful V1 engine."""
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING

from research.stage0b.engine import Engine
from research.stage0b.model import IntegrityError

A = 'V2_A_BREAKEVEN_AFTER_TP1'
B = 'V2_B_FULL_EXIT_AT_TP1'
ARMS = (A, B)


class ExitExperiment(Engine):
    def __init__(self, *args, arm, **kwargs):
        if arm not in ARMS:
            raise IntegrityError('UNREGISTERED_EXIT_POLICY')
        super().__init__(*args, **kwargs)
        self.arm = arm
        self.be_stops = {}
        self.activations = []

    def current_stop(self):
        if self.position is None:
            raise IntegrityError('STOP_WITHOUT_POSITION')
        p = self.position
        return self.be_stops.get(p.plan.entry_id, p.plan.sl)

    def _exit_leg(self, leg, raw_price, t, phase, kind, mark_price=None):
        old = self.position
        if old is None:
            raise IntegrityError('EXIT_WITHOUT_POSITION')
        identity, fill = old.plan.entry_id, old.entry_fill
        super()._exit_leg(leg, raw_price, t, phase, kind, mark_price)
        if self.position is None or leg != 0 or kind != 'TP':
            return
        if self.arm == B:
            # One logical whole-position TP1 exit. Two frozen accounting allocations
            # conserve the original sizing split; there is no independent leg timing.
            super()._exit_leg(1, raw_price, t, phase, 'TP', mark_price)
            self.quality['FULL_TP1_EXIT'] += 1
            return
        tick = Decimal(self.config['instrument_assumption']['tick_size'])
        rounding = ROUND_FLOOR if old.plan.sign == 1 else ROUND_CEILING
        stop = float((Decimal(str(fill))/tick).to_integral_value(rounding=rounding)*tick)
        if old.plan.sign*(stop-old.plan.sl) < 0:
            raise IntegrityError('BREAKEVEN_STOP_WORSE_THAN_INITIAL_STOP')
        self.be_stops[identity] = stop
        self.activations.append(dict(entry_id=identity, time_ms=t, phase=phase, stop=stop))
        self.quality['BE_ACTIVATED_AFTER_TP1'] += 1
        # A known Open can already be through the newly activated stop. Never
        # assume it fills at its reference price rather than the adverse Open.
        if phase == 'OPEN' and mark_price is not None and old.plan.sign*(mark_price-stop) <= 0:
            self.quality['BE_IMMEDIATE_OPEN_EXIT'] += 1
            self._stop_all(mark_price, t, 'OPEN')
        elif phase == 'PRIOR_BAR' and old.plan.sign*(raw_price-stop) <= 0:
            # If entry friction/gap put economic breakeven beyond the just-touched
            # TP1, the new stop is immediately marketable at that known touch.
            # Filling at an unvisited BE reference would invent a better price.
            self.quality['BE_IMMEDIATE_INTRABAR_EXIT'] += 1
            self._stop_all(raw_price, t, phase)

    def process_open(self, bar):
        if self.ended:
            raise IntegrityError('PATH_ALREADY_FINISHED')
        self.window.authorize_bar(bar.open_time)
        p = self.position
        if self.arm == A and p is not None and p.plan.entry_id in self.be_stops:
            if self.pending is not None:
                raise IntegrityError('PENDING_AND_ACTIVE_POSITION')
            if p.plan.sign*(bar.open-self.current_stop()) <= 0:
                self.quality['BE_OPEN_STOP_EXIT'] += 1
                self._stop_all(bar.open, bar.open_time, 'OPEN')
                return
        super().process_open(bar)

    def process_intrabar(self, bar):
        if self.arm == B:
            return super().process_intrabar(bar)
        p = self.position
        if p is None:
            return
        t = bar.open_time+self.window.step
        stop = self.current_stop()
        stop_hit = bar.low <= stop if p.plan.sign == 1 else bar.high >= stop
        favorable = bar.high if p.plan.sign == 1 else bar.low
        target_hit = any(p.remaining[i] and p.plan.sign*(favorable-target) >= 0
                         for i, target in enumerate((p.plan.tp1, p.plan.tp2)))
        if stop_hit:
            if target_hit:
                self.quality['UNCERTAIN_INTRABAR_ORDER'] += 1
            self._stop_all(stop, t, 'PRIOR_BAR')
            return
        for leg, target in enumerate((p.plan.tp1, p.plan.tp2)):
            if self.position is None:
                break
            if p.remaining[leg] and p.plan.sign*(favorable-target) >= 0:
                self._margin(target, t, 'PRIOR_BAR')
                self._exit_leg(leg, target, t, 'PRIOR_BAR', 'TP')
                if leg == 0 and self.position is not None:
                    stop = self.current_stop()
                    activation_touch = bar.low <= stop if p.plan.sign == 1 else bar.high >= stop
                    if activation_touch:
                        self.quality['BE_ACTIVATION_INTRABAR_AMBIGUOUS'] += 1
                        self._stop_all(stop, t, 'PRIOR_BAR')
                        break
        if self.position is not None:
            adverse = bar.low if p.plan.sign == 1 else bar.high
            self._margin(adverse, t, 'PRIOR_BAR')
            self._margin(bar.close, t, 'PRIOR_BAR')
