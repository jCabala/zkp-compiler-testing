; unique_target=00
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert (or (not x2) (not x1)))
(assert (not x1))
(assert (not x2))
(check-sat)
(get-model)