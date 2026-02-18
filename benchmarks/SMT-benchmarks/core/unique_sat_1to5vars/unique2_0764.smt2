; unique_target=11
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert x1)
(assert (or (not x1) x2))
(assert x2)
(check-sat)
(get-model)