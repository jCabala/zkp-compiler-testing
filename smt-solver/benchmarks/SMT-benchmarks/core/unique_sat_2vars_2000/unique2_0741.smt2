; unique_target=10
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert (or (not x2) x1))
(assert x1)
(assert (or (not x1) (not x2)))
(check-sat)
(get-model)