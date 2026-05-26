// ============================================================
// state_machine.js - State Machine Pattern (K122 + K136)
// Piyasa rejimi tespiti ve sistem durum yonetimi.
// ============================================================

const logger = require('../logger');

class StateMachine {
    constructor(name, states, transitions, initialState) {
        this.name = name;
        this.states = new Set(states);
        this.transitions = transitions;
        this.state = initialState;
        this._history = [{ from: null, to: initialState, time: Date.now(), reason: 'INIT' }];
        this._listeners = [];
    }

    canTransition(to) {
        const allowed = this.transitions[this.state];
        return allowed ? allowed.includes(to) : false;
    }

    transition(to, reason = '') {
        if (!this.states.has(to)) {
            throw new Error(`[SM] ${this.name}: Bilinmeyen durum ${to}`);
        }
        if (!this.canTransition(to)) {
            throw new Error(`[SM] ${this.name}: ${this.state} -> ${to} gecisi yasak`);
        }
        const from = this.state;
        this.state = to;
        const record = { from, to, time: Date.now(), reason };
        this._history.push(record);
        logger.info(`[SM] ${this.name} ${from} -> ${to} | ${reason}`);
        for (const cb of this._listeners) {
            try { cb(record); } catch (e) { logger.error(`[SM] listener hatasi: ${e.message}`); }
        }
        return record;
    }

    onTransition(callback) {
        this._listeners.push(callback);
    }

    getState() { return this.state; }
    getHistory() { return [...this._history]; }

    is(state) { return this.state === state; }
    isOneOf(states) { return states.includes(this.state); }
}

class MarketRegimeDetector {
    constructor() {
        this.sm = new StateMachine('MARKET_REGIME',
            ['UNKNOWN', 'BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'CRASH'],
            {
                UNKNOWN: ['BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'CRASH'],
                BULL: ['BULL', 'SIDEWAYS', 'VOLATILE', 'BEAR', 'CRASH'],
                BEAR: ['BEAR', 'SIDEWAYS', 'VOLATILE', 'BULL', 'CRASH'],
                SIDEWAYS: ['SIDEWAYS', 'BULL', 'BEAR', 'VOLATILE', 'CRASH'],
                VOLATILE: ['VOLATILE', 'BULL', 'BEAR', 'SIDEWAYS', 'CRASH'],
                CRASH: ['CRASH', 'BEAR', 'SIDEWAYS'],
            },
            'UNKNOWN'
        );
    }

    detect(vix, trend, breadth, volume) {
        let newState = this.sm.getState();
        if (vix > 30 || trend < -5) newState = 'CRASH';
        else if (vix > 25) newState = 'VOLATILE';
        else if (trend > 2 && breadth > 0.6) newState = 'BULL';
        else if (trend < -2 && breadth < 0.4) newState = 'BEAR';
        else if (Math.abs(trend) < 1) newState = 'SIDEWAYS';

        if (newState !== this.sm.getState() && this.sm.canTransition(newState)) {
            this.sm.transition(newState, `vix=${vix}, trend=${trend}, breadth=${breadth}`);
        }
        return this.sm.getState();
    }

    getState() { return this.sm.getState(); }
    getHistory() { return this.sm.getHistory(); }
}

module.exports = { StateMachine, MarketRegimeDetector };
