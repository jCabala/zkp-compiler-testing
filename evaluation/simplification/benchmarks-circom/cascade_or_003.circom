pragma circom 2.0.6;

include "../circomlib/comparators.circom";

include "../circomlib/gates.circom";

template main_template() {
    signal input x1;
    signal input x2;
    signal y1;
    signal y2;
    signal y3;
    signal y4;
    signal y5;
    y1 <== 1;
    y2 <== 1;
    y3 <== 1;
    y4 <== 1;
    y5 <== 1;
    (x1 * (1 - x1)) === 0;
    (x2 * (1 - x2)) === 0;
    component comp_0 = NOT();
    comp_0.in <== x1;
    component comp_1 = IsZero();
    comp_1.in <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== comp_1.out;
    comp_2.out === 1;
    component comp_3 = NOT();
    comp_3.in <== x2;
    component comp_4 = IsZero();
    comp_4.in <== comp_3.out;
    component comp_5 = NOT();
    comp_5.in <== comp_4.out;
    comp_5.out === 1;
    component comp_6 = NOT();
    comp_6.in <== x1;
    component comp_7 = AND();
    comp_7.a <== x1;
    comp_7.b <== comp_6.out;
    component comp_8 = OR();
    comp_8.a <== comp_7.out;
    comp_8.b <== y1;
    component comp_9 = OR();
    comp_9.a <== comp_8.out;
    comp_9.b <== y2;
    component comp_10 = OR();
    comp_10.a <== comp_9.out;
    comp_10.b <== y3;
    component comp_11 = OR();
    comp_11.a <== comp_10.out;
    comp_11.b <== y4;
    component comp_12 = OR();
    comp_12.a <== comp_11.out;
    comp_12.b <== y5;
    component comp_13 = IsZero();
    comp_13.in <== comp_12.out;
    component comp_14 = NOT();
    comp_14.in <== comp_13.out;
    comp_14.out === 1;
}

component main = main_template();
