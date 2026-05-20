pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x9;
    signal input x12;
    signal input x16;
    (x9 * (1 - x9)) === 0;
    (x12 * (1 - x12)) === 0;
    (x16 * (1 - x16)) === 0;
    component comp_0 = NOT();
    comp_0.in <== x12;
    component comp_1 = AND();
    comp_1.a <== x9;
    comp_1.b <== comp_0.out;
    component comp_2 = AND();
    comp_2.a <== comp_1.out;
    comp_2.b <== x16;
    component comp_3 = IsZero();
    comp_3.in <== comp_2.out;
    component comp_4 = NOT();
    comp_4.in <== comp_3.out;
    comp_4.out === 1;
}

component main = main_template();
