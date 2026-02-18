; unique_target=1
(set-logic QF_BV)
(declare-fun x1 () Bool)
(assert x1)
(check-sat)
(get-model)