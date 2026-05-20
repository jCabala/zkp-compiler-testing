pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input x2;
    signal input x10;
    (x2 * (1 - x2)) === 0;
    (x10 * (1 - x10)) === 0;
    component comp_0 = NOT();
    comp_0.in <== x2;
    component comp_1 = AND();
    comp_1.a <== x10;
    comp_1.b <== comp_0.out;
    component comp_2 = IsZero();
    comp_2.in <== comp_1.out;
    component comp_3 = NOT();
    comp_3.in <== comp_2.out;
    comp_3.out === 1;
}

component main = main_template();
