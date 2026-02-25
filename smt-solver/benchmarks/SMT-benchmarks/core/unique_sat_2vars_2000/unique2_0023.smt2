; unique_target=00
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert (not x1))
(assert (or (not x2) x1))
(check-sat)
(get-model)