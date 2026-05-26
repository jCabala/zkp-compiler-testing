pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x3;
    signal input x12;
    signal input x14;
    (x3 * (1 - x3)) === 0;
    (x12 * (1 - x12)) === 0;
    (x14 * (1 - x14)) === 0;
    component comp_0 = NOT();
    comp_0.in <== x3;
    component comp_1 = AND();
    comp_1.a <== x14;
    comp_1.b <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== x12;
    component comp_3 = AND();
    comp_3.a <== comp_1.out;
    comp_3.b <== comp_2.out;
    component comp_4 = IsZero();
    comp_4.in <== comp_3.out;
    component comp_5 = NOT();
    comp_5.in <== comp_4.out;
    comp_5.out === 1;
}

component main = main_template();
