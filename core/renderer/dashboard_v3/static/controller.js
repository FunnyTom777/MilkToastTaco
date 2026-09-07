/**
 * Milk Toast Taco — Controller Library v1.1 (grid-locked fix)
 * Location: core/renderer/dashboard_v3/static/controller.js
 * Reusable for ANY MTT UI that needs gamepad + keyboard support.
 *
 * Provides two globals:
 *   window.MTTController — low-level gamepad polling + semantic events
 *   window.MTTFocus      — spatial focus manager for controller navigation
 *
 * Design goals:
 *  - Works on big-screen / couch (deadzone, repeat, no drift)
 *  - Keyboard fallback so everything testable without a pad
 *  - No dependencies, file:// friendly, pywebview friendly
 *  - Future UIs just include this file + instantiate
 *
 * Usage:
 *   const pad = new MTTController({ deadzone: 0.45 });
 *   pad.on('up',    () => nav.move('up'));
 *   pad.on('down',  () => nav.move('down'));
 *   pad.on('a',     () => nav.activate());
 *   pad.on('b',     () => nav.back());
 *   pad.on('connect', e => console.log('pad', e.gamepad.id));
 *
 *   const nav = new MTTFocus({ selector: '[data-focusable]', loop: false });
 *   nav.bind(pad); // auto-wires up/down/left/right/a/b
 *   // or manually: nav.move('up'), nav.activate(), nav.back()
 *
 * Keyboard map (always active):
 *   Arrows -> up/down/left/right
 *   Enter/Space -> a (activate)
 *   Escape/Backspace -> b (back)
 *   Tab / Shift+Tab -> focus next/prev (also emits)
 *
 * Gamepad map (Standard):
 *   Buttons: 0:A, 1:B, 2:X, 3:Y, 4:LB, 5:RB, 8:Back/View, 9:Start/Menu,
 *            12:D-Up, 13:D-Down, 14:D-Left, 15:D-Right
 *   Axes: 0 (LS X), 1 (LS Y) with deadzone
 *   LT/RT (6,7) as analog triggers
 */
(function (global) {
  'use strict';

  // ---------------------------------------------------------------------------
  // MTTController — semantic gamepad + keyboard
  // ---------------------------------------------------------------------------
  class MTTController {
    constructor(opts = {}) {
      this.deadzone = opts.deadzone ?? 0.45;
      this.repeatDelay = opts.repeatDelay ?? 320;
      this.repeatRate = opts.repeatRate ?? 130;
      this.axisThreshold = opts.axisThreshold ?? 0.55;

      this._listeners = new Map(); // event -> Set<fn>
      this._running = false;
      this._raf = null;
      this._last = { up: false, down: false, left: false, right: false, a: false, b: false, x: false, y: false, lb: false, rb: false, lt: false, rt: false, start: false, back: false };
      this._repeatAt = { up: 0, down: 0, left: 0, right: 0 };
      this._connected = false;
      this._padIndex = null;
      this._onKeyDown = this._onKeyDown.bind(this);
      this._onGamepadConnected = this._onGamepadConnected.bind(this);
      this._onGamepadDisconnected = this._onGamepadDisconnected.bind(this);
    }

    on(event, fn) {
      if (!this._listeners.has(event)) this._listeners.set(event, new Set());
      this._listeners.get(event).add(fn);
      return () => this.off(event, fn);
    }
    off(event, fn) {
      const s = this._listeners.get(event);
      if (s) s.delete(fn);
    }
    emit(event, data) {
      const s = this._listeners.get(event);
      if (s) s.forEach(fn => { try { fn(data); } catch (e) { console.error(e); } });
      const any = this._listeners.get('*');
      if (any) any.forEach(fn => { try { fn(event, data); } catch (e) { console.error(e); } });
    }

    start() {
      if (this._running) return;
      this._running = true;
      window.addEventListener('keydown', this._onKeyDown);
      window.addEventListener('gamepadconnected', this._onGamepadConnected);
      window.addEventListener('gamepaddisconnected', this._onGamepadDisconnected);
      this._tick();
    }
    stop() {
      this._running = false;
      if (this._raf) cancelAnimationFrame(this._raf);
      this._raf = null;
      window.removeEventListener('keydown', this._onKeyDown);
      window.removeEventListener('gamepadconnected', this._onGamepadConnected);
      window.removeEventListener('gamepaddisconnected', this._onGamepadDisconnected);
    }

    get connected() { return this._connected; }
    get gamepad() {
      const pads = navigator.getGamepads ? navigator.getGamepads() : [];
      for (let i = 0; i < pads.length; i++) if (pads[i]) return pads[i];
      return null;
    }
    get gamepadName() {
      const g = this.gamepad;
      return g ? g.id : null;
    }

    _onGamepadConnected(e) {
      this._connected = true;
      this._padIndex = e.gamepad.index;
      this.emit('connect', { gamepad: e.gamepad });
      this.emit('status', { connected: true, name: e.gamepad.id });
    }
    _onGamepadDisconnected(e) {
      // check if any pad remains
      const pads = navigator.getGamepads ? navigator.getGamepads() : [];
      const any = Array.from(pads).some(p => p);
      this._connected = any;
      if (!any) this._padIndex = null;
      this.emit('disconnect', { gamepad: e.gamepad });
      this.emit('status', { connected: any, name: any ? this.gamepadName : null });
    }

    _onKeyDown(e) {
      // Avoid interfering when typing in inputs (but still allow Escape/Enter for modals)
      const tag = (e.target && e.target.tagName) || '';
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || (e.target && e.target.isContentEditable);
      const k = e.key;
      // Map keyboard to semantic
      let sem = null;
      if (k === 'ArrowUp') sem = 'up';
      else if (k === 'ArrowDown') sem = 'down';
      else if (k === 'ArrowLeft') sem = 'left';
      else if (k === 'ArrowRight') sem = 'right';
      else if (k === 'Enter' || k === ' ') sem = 'a';
      else if (k === 'Escape' || k === 'Backspace') sem = 'b';
      else if (k === 'Tab') { sem = e.shiftKey ? 'shift+tab' : 'tab'; }
      else if (k.toLowerCase() === 'x') sem = 'x';
      else if (k.toLowerCase() === 'y') sem = 'y';

      if (sem) {
        // For arrows / a / b we emit and prevent page scroll when not typing
        if (!isTyping || sem === 'b' || sem === 'up' || sem === 'down') {
          // let b/escape always through for back navigation
        }
        this.emit(sem, { source: 'keyboard', key: k, originalEvent: e });
        this.emit('press', { button: sem, source: 'keyboard', key: k });
        // Don't preventDefault for Tab (let browser move focus unless handled by FocusManager)
        if (['up','down','left','right','a','b','x','y'].includes(sem) && !isTyping) {
          // slight: only prevent scroll for arrows/a/b when not in input
          // handled by caller if needed
        }
      }
    }

    _tick() {
      if (!this._running) return;
      this._raf = requestAnimationFrame(() => this._tick());
      const now = performance.now();
      const pads = navigator.getGamepads ? navigator.getGamepads() : [];
      let gp = null;
      for (let i = 0; i < pads.length; i++) if (pads[i]) { gp = pads[i]; break; }

      if (gp) {
        if (!this._connected) {
          this._connected = true;
          this.emit('connect', { gamepad: gp });
          this.emit('status', { connected: true, name: gp.id });
        }
        const dead = this.deadzone;
        const thr = this.axisThreshold;
        const ax0 = gp.axes[0] || 0;
        const ax1 = gp.axes[1] || 0;
        const btn = (i) => !!(gp.buttons[i] && gp.buttons[i].pressed);
        const up = btn(12) || ax1 < -thr;
        const down = btn(13) || ax1 > thr;
        const left = btn(14) || ax0 < -thr;
        const right = btn(15) || ax0 > thr;
        const a = btn(0);
        const b = btn(1);
        const x = btn(2);
        const y = btn(3);
        const lb = btn(4);
        const rb = btn(5);
        const lt = btn(6) || (gp.buttons[6] && gp.buttons[6].value > 0.5);
        const rt = btn(7) || (gp.buttons[7] && gp.buttons[7].value > 0.5);
        const back = btn(8);
        const start = btn(9);

        const handleDir = (pressed, was, name) => {
          if (pressed) {
            if (!was) { this.emit(name, { source: 'gamepad', gamepad: gp }); this.emit('press', { button: name, source: 'gamepad' }); this._repeatAt[name] = now + this.repeatDelay; }
            else if (now >= this._repeatAt[name]) { this.emit(name, { source: 'gamepad', gamepad: gp, repeat: true }); this.emit('press', { button: name, source: 'gamepad', repeat: true }); this._repeatAt[name] = now + this.repeatRate; }
          }
        };
        handleDir(up, this._last.up, 'up');
        handleDir(down, this._last.down, 'down');
        handleDir(left, this._last.left, 'left');
        handleDir(right, this._last.right, 'right');

        const fireEdge = (pressed, was, name) => {
          if (pressed && !was) { this.emit(name, { source: 'gamepad', gamepad: gp }); this.emit('press', { button: name, source: 'gamepad' }); }
          if (!pressed && was) this.emit(name + ':up', { source: 'gamepad', gamepad: gp });
        };
        fireEdge(a, this._last.a, 'a');
        fireEdge(b, this._last.b, 'b');
        fireEdge(x, this._last.x, 'x');
        fireEdge(y, this._last.y, 'y');
        fireEdge(lb, this._last.lb, 'lb');
        fireEdge(rb, this._last.rb, 'rb');
        fireEdge(lt, this._last.lt, 'lt');
        fireEdge(rt, this._last.rt, 'rt');
        fireEdge(start, this._last.start, 'start');
        fireEdge(back, this._last.back, 'back');

        this._last = { up, down, left, right, a, b, x, y, lb, rb, lt, rt, start, back };
      } else {
        if (this._connected) {
          // delay disconnect detection (let browser event fire) but also poll
        }
        this._last = { up: false, down: false, left: false, right: false, a: false, b: false, x: false, y: false, lb: false, rb: false, lt: false, rt: false, start: false, back: false };
      }
    }
  }

  // ---------------------------------------------------------------------------
  // MTTFocus — spatial navigation
  // ---------------------------------------------------------------------------
  class MTTFocus {
    /**
     * @param {Object} opts
     * @param {string} opts.selector — focusable selector (default '[data-focusable]')
     * @param {boolean} opts.loop — wrap at edges (default false)
     * @param {string} opts.focusClass — css class for focused element
     * @param {boolean} opts.remember — remember last focused per container
     */
    constructor(opts = {}) {
      this.selector = opts.selector || '[data-focusable]';
      this.loop = !!opts.loop;
      this.focusClass = opts.focusClass || 'is-focused';
      this.remember = opts.remember !== false;
      this.containers = []; // array of HTMLElements to search within (default: document)
      this._current = null;
      this._onActivate = opts.onActivate || null;
      this._onBack = opts.onBack || null;
      this._onMove = opts.onMove || null;
      this._boundController = null;
    }

    setContainers(els) {
      if (!els) this.containers = [];
      else if (Array.isArray(els)) this.containers = els;
      else this.containers = [els];
    }
    addContainer(el) { if (el && !this.containers.includes(el)) this.containers.push(el); }

    get focusable() {
      const roots = this.containers.length ? this.containers : [document];
      const out = [];
      roots.forEach(root => {
        const list = root.querySelectorAll(this.selector);
        list.forEach(el => {
          if (el.offsetParent !== null || el.getClientRects().length) out.push(el);
          else if (getComputedStyle(el).display !== 'none') out.push(el);
        });
      });
      // de-dupe
      return [...new Set(out)];
    }
    get current() { return this._current; }

    focus(el, opts = {}) {
      if (!el) return;
      if (this._current === el && !opts.force) return;
      if (this._current) {
        this._current.classList.remove(this.focusClass);
        this._current.setAttribute('tabindex', '-1');
        this._current.blur();
      }
      this._current = el;
      el.classList.add(this.focusClass);
      el.setAttribute('tabindex', '0');
      try { el.focus({ preventScroll: false }); } catch (e) { try { el.focus(); } catch(_) {} }
      // ensure visible (center-ish)
      try { el.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: opts.smooth ? 'smooth' : 'auto' }); } catch(_) {}
      if (this._onMove) try { this._onMove(el); } catch(e) {}
      this.emitFocus(el);
    }
    emitFocus(el) {
      const ev = new CustomEvent('mtt:focus', { detail: { element: el }, bubbles: true });
      el.dispatchEvent(ev);
      document.dispatchEvent(new CustomEvent('mtt:focuschange', { detail: { element: el } }));
    }

    focusFirst() {
      const list = this.focusable;
      if (list.length) this.focus(list[0]);
    }
    focusLast() {
      const list = this.focusable;
      if (list.length) this.focus(list[list.length - 1]);
    }

    /** Spatial move: up/down/left/right — grid-locked, no drift */
    move(dir) {
      const list = this.focusable;
      if (!list.length) return;
      if (!this._current || !document.contains(this._current)) { this.focusFirst(); return; }
      const cur = this._current;
      const curRect = cur.getBoundingClientRect();
      const curCenter = { x: curRect.left + curRect.width / 2, y: curRect.top + curRect.height / 2 };

      // If custom data-nav-* hints exist, honor them first (explicit wiring)
      const hintAttr = `data-nav-${dir}`;
      if (cur.hasAttribute(hintAttr)) {
        const targetId = cur.getAttribute(hintAttr);
        const target = document.getElementById(targetId) || document.querySelector(targetId);
        if (target) { this.focus(target); return; }
      }

      const candidates = [];
      for (const el of list) {
        if (el === cur) continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        const c = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        const dx = c.x - curCenter.x;
        const dy = c.y - curCenter.y;
        let inDir = false;
        if (dir === 'up') inDir = dy < -4;
        else if (dir === 'down') inDir = dy > 4;
        else if (dir === 'left') inDir = dx < -4;
        else if (dir === 'right') inDir = dx > 4;
        if (!inDir) continue;
        candidates.push({ el, r, c, dx, dy });
      }
      if (!candidates.length) {
        // fall through to edge handling below
      } else {
        // Grid-locked: only allow moves that share the same row (left/right) or column (up/down).
        // This prevents the diagonal drift bug where left would hop down a row because a diagonal
        // candidate was horizontally closer. Overlap in the orthogonal axis means same band.
        const banded = candidates.filter(({ r }) => {
          let overlap = 0;
          if (dir === 'up' || dir === 'down') overlap = Math.max(0, Math.min(curRect.right, r.right) - Math.max(curRect.left, r.left));
          else overlap = Math.max(0, Math.min(curRect.bottom, r.bottom) - Math.max(curRect.top, r.top));
          return overlap > 4;
        });

        if (!banded.length) {
          // No band-aligned candidate — treat as edge (don't drift diagonally)
        } else {
          let best = null;
          let bestScore = Infinity;
          for (const { el, r, dx, dy } of banded) {
            const primary = dir === 'up' ? -dy : dir === 'down' ? dy : dir === 'left' ? -dx : dx;
            const secondary = (dir === 'up' || dir === 'down') ? Math.abs(dx) : Math.abs(dy);
            // All in banded already overlap, but keep scoring by drift then distance
            const score = primary * 1.0 + secondary * 1.45;
            const tie = secondary * 0.01 + primary * 0.001;
            const final = score + tie;
            if (final < bestScore) { bestScore = final; best = el; }
          }
          if (best) { this.focus(best); return; }
        }
      }

      // No candidate in direction: optionally wrap/loop or bubble to container edge
      if (this.loop) {
        // simple loop: for up wrap to bottom-most, down to top-most, etc.
        if (dir === 'up' || dir === 'left') this.focusLast();
        else this.focusFirst();
        return;
      }
      // emit edge event so app can switch focus layers (e.g., tabs -> content)
      const edgeEv = new CustomEvent('mtt:edge', { detail: { dir, from: cur }, bubbles: true });
      cur.dispatchEvent(edgeEv);
      document.dispatchEvent(new CustomEvent('mtt:edge', { detail: { dir, from: cur } }));
    }

    activate() {
      if (!this._current) return;
      const el = this._current;
      // trigger click
      el.click();
      // also dispatch keyboard enter for elements expecting it
      el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      if (this._onActivate) try { this._onActivate(el); } catch(e) {}
      document.dispatchEvent(new CustomEvent('mtt:activate', { detail: { element: el } }));
    }
    back() {
      if (this._onBack) { try { const r = this._onBack(); if (r === false) return; } catch(e) {} }
      document.dispatchEvent(new CustomEvent('mtt:back', { detail: { from: this._current } }));
    }

    /** Bind a controller instance to auto-drive focus */
    bind(controller) {
      if (this._boundController) this.unbind();
      this._boundController = controller;
      const ups = [];
      ups.push(controller.on('up', () => this.move('up')));
      ups.push(controller.on('down', () => this.move('down')));
      ups.push(controller.on('left', () => this.move('left')));
      ups.push(controller.on('right', () => this.move('right')));
      ups.push(controller.on('a', () => this.activate()));
      ups.push(controller.on('b', () => this.back()));
      this._bindings = ups;
      return () => this.unbind();
    }
    unbind() {
      if (this._bindings) this._bindings.forEach(off => { try { off(); } catch(_){} });
      this._bindings = null;
      this._boundController = null;
    }

    /** Auto-discover focusables and keep focus sane after DOM mutations — no teleport */
    observe() {
      if (this._observer) return;
      let lastCenter = null;
      let lastKey = null;
      const capture = () => {
        if (this._current && document.contains(this._current)) {
          const r = this._current.getBoundingClientRect();
          if (r.width || r.height) lastCenter = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
          // key for exact restoration (saves, theme, etc.)
          lastKey = this._current.getAttribute('data-save') || this._current.getAttribute('data-theme') || this._current.textContent?.trim().slice(0, 40) || null;
        }
      };
      // keep lastCenter up to date on focus changes
      document.addEventListener('mtt:focuschange', (e) => {
        const el = e.detail.element;
        if (el) {
          const r = el.getBoundingClientRect();
          if (r.width || r.height) lastCenter = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
          lastKey = el.getAttribute('data-save') || el.getAttribute('data-theme') || el.textContent?.trim().slice(0, 40) || null;
        }
      });
      // initial capture
      if (this._current) capture();

      this._observer = new MutationObserver(() => {
        const list = this.focusable;
        if (!list.length) return;
        if (this._current && list.includes(this._current) && document.contains(this._current)) {
          capture();
          return;
        }
        // Current was destroyed or missing — try to restore to same logical element
        if (lastKey) {
          const byKey = list.find(el => el.getAttribute('data-save') === lastKey || el.getAttribute('data-theme') === lastKey);
          if (byKey) { this.focus(byKey); return; }
        }
        if (lastCenter) {
          let best = null; let bestDist = Infinity;
          for (const el of list) {
            const r = el.getBoundingClientRect();
            if (!r.width && !r.height) continue;
            const c = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
            const dx = c.x - lastCenter.x; const dy = c.y - lastCenter.y;
            const dist = dx * dx + dy * dy;
            if (dist < bestDist) { bestDist = dist; best = el; }
          }
          // Only restore if reasonably close (within ~800px) — avoids jumping from bottom to top when idle
          if (best && bestDist < 640000) { this.focus(best); return; }
        }
        // No close restoration — just clear current, don't teleport to top while idle.
        // Next directional press will call focusFirst() via move().
        if (this._current && !list.includes(this._current)) this._current = null;
      });
      this._observer.observe(document.body, { childList: true, subtree: true, childList: true });
    }
    disconnectObserver() { if (this._observer) { this._observer.disconnect(); this._observer = null; } }
  }

  // Convenience: create + start + focus first
  function create(opts) {
    const ctrl = new MTTController(opts && opts.controller);
    const focus = new MTTFocus(opts && opts.focus);
    ctrl.start();
    return { controller: ctrl, focus };
  }

  // Expose
  const MTT = { Controller: MTTController, Focus: MTTFocus, create };
  global.MTTController = MTTController;
  global.MTTFocus = MTTFocus;
  global.MTT = MTT;

})(window);
