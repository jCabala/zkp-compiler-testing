; unique_target=01
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert x2)
(assert (not x1))
(assert (or (not x1) x2))
(check-sat)
(get-model)