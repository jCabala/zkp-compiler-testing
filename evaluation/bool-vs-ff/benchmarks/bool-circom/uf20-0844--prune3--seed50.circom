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
    comp_0.in <== x16;
    component comp_1 = AND();
    comp_1.a <== comp_0.out;
    comp_1.b <== x12;
    component comp_2 = NOT();
    comp_2.in <== x9;
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
