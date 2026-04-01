; tautological OR benchmark — 5 ORs, seed=2
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert (not x1))
(assert (not x2))

; d is always false: x1 AND (NOT x1) = 0
(declare-fun d () Bool)
(assert (= d (and x1 (not x1))))

; y variables — free, ORed with the always-false d
(declare-fun y1 () Bool)
(declare-fun y2 () Bool)
(declare-fun y3 () Bool)
(declare-fun y4 () Bool)
(declare-fun y5 () Bool)

; OR(d, y_i) — d=0 forces linearisation in round 2
(assert (or d y1))
(assert (or d y2))
(assert (or d y3))
(assert (or d y4))
(assert (or d y5))

(check-sat)
(get-model)
