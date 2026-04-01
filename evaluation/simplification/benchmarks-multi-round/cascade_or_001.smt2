; cascading OR benchmark (direct nesting) — depth=5, seed=0
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert (not x1))
(assert (not x2))

; y variables — one per OR level
(declare-fun y1 () Bool)
(declare-fun y2 () Bool)
(declare-fun y3 () Bool)
(declare-fun y4 () Bool)
(declare-fun y5 () Bool)

; deeply nested OR — no intermediate named variables
; innermost is always false: (and x1 (not x1))
(assert (or (or (or (or (or (and x1 (not x1)) y1) y2) y3) y4) y5))

(check-sat)
(get-model)
