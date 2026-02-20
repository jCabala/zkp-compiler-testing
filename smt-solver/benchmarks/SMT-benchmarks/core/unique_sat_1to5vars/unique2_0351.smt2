; unique_target=11
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert x2)
(assert (or (not x2) x1))
(assert (or x2 (not x1)))
(check-sat)
(get-model)