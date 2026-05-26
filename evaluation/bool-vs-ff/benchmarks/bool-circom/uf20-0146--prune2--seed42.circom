pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x1;
    signal input x4;
    (x1 * (1 - x1)) === 0;
    (x4 * (1 - x4)) === 0;
    component comp_0 = NOT();
    comp_0.in <== x1;
    component comp_1 = AND();
    comp_1.a <== comp_0.out;
    comp_1.b <== x4;
    component comp_2 = IsZero();
    comp_2.in <== comp_1.out;
    component comp_3 = NOT();
    comp_3.in <== comp_2.out;
    comp_3.out === 1;
}

component main = main_template();
