pragma circom 2.0.6;

include "../circomlib/comparators.circom";

include "../circomlib/gates.circom";

template main_template() {
    signal input x2;
    signal input x9;
    signal input x13;
    signal input x14;
    signal input x16;
    (x2 * (1 - x2)) === 0;
    (x9 * (1 - x9)) === 0;
    (x13 * (1 - x13)) === 0;
    (x14 * (1 - x14)) === 0;
    (x16 * (1 - x16)) === 0;
    component comp_0 = AND();
    comp_0.a <== x13;
    comp_0.b <== x2;
    component comp_1 = AND();
    comp_1.a <== comp_0.out;
    comp_1.b <== x16;
    component comp_2 = AND();
    comp_2.a <== comp_1.out;
    comp_2.b <== x14;
    component comp_3 = NOT();
    comp_3.in <== x9;
    component comp_4 = AND();
    comp_4.a <== comp_2.out;
    comp_4.b <== comp_3.out;
    component comp_5 = IsZero();
    comp_5.in <== comp_4.out;
    component comp_6 = NOT();
    comp_6.in <== comp_5.out;
    comp_6.out === 1;
}

component main = main_template();
