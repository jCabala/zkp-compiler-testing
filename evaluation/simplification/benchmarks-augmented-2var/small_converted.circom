pragma circom 2.0.6;

include "../circomlib/comparators.circom";

include "../circomlib/gates.circom";

template main_template() {
    signal input x1;
    signal input x2;
    signal input c1;
    signal input c2;
    signal input c3;
    (x1 * (1 - x1)) === 0;
    (x2 * (1 - x2)) === 0;
    (c1 * (1 - c1)) === 0;
    (c2 * (1 - c2)) === 0;
    (c3 * (1 - c3)) === 0;
    component comp_0 = NOT();
    comp_0.in <== x2;
    component comp_1 = NOT();
    comp_1.in <== x1;
    component comp_2 = AND();
    comp_2.a <== comp_0.out;
    comp_2.b <== comp_1.out;
    component comp_3 = AND();
    comp_3.a <== comp_2.out;
    comp_3.b <== c1;
    component comp_4 = NOT();
    comp_4.in <== c2;
    component comp_5 = AND();
    comp_5.a <== comp_3.out;
    comp_5.b <== comp_4.out;
    component comp_6 = AND();
    comp_6.a <== comp_5.out;
    comp_6.b <== c3;
    component comp_7 = IsZero();
    comp_7.in <== comp_6.out;
    component comp_8 = NOT();
    comp_8.in <== comp_7.out;
    comp_8.out === 1;
}

component main = main_template();
