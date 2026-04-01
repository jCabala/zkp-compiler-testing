; unique_target=00
(set-logic QF_BV)
(declare-fun x1 () Bool)
(declare-fun x2 () Bool)
(assert (not x2))
(assert (not x1))

; --- NOT chain: 400 links anchored to x1 ---
(declare-fun c1 () Bool)
(declare-fun c2 () Bool)
(declare-fun c3 () Bool)
(assert (= c1 (not x1)))
(assert (= c2 (not c1)))
(assert (= c3 (not c2)))

(check-sat)
(get-model)