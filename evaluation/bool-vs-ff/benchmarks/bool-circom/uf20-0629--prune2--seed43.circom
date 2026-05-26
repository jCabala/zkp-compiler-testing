pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x2;
    signal input x10;
    (x2 * (1 - x2)) === 0;
    (x10 * (1 - x10)) === 0;
    component comp_0 = AND();
    comp_0.a <== x2;
    comp_0.b <== x10;
    component comp_1 = IsZero();
    comp_1.in <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== comp_1.out;
    comp_2.out === 1;
}

component main = main_template();
