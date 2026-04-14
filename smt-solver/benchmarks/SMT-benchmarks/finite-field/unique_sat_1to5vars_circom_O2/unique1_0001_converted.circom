pragma circom 2.0.6;

include "gates.circom";

include "comparators.circom";

template main_template() {
    signal input v1;
    signal input v6;
    signal sig_0;
    sig_0 <== (v1 * (v1 + (- 1)));
    signal sig_1;
    sig_1 <== 0;
    component comp_2 = IsEqual();
    comp_2.in[0] <== sig_0;
    comp_2.in[1] <== sig_1;
    component comp_3 = IsZero();
    comp_3.in <== comp_2.out;
    component comp_4 = NOT();
    comp_4.in <== comp_3.out;
    comp_4.out === 1;
    signal sig_5;
    sig_5 <== ((1 + (21888242871839275222246405745257275088548364400416034343698204186575808495616 * v1)) * v1);
    signal sig_6;
    sig_6 <== 0;
    component comp_7 = IsEqual();
    comp_7.in[0] <== sig_5;
    comp_7.in[1] <== sig_6;
    component comp_8 = IsZero();
    comp_8.in <== comp_7.out;
    component comp_9 = NOT();
    comp_9.in <== comp_8.out;
    comp_9.out === 1;
    signal sig_10;
    sig_10 <== ((1 + (21888242871839275222246405745257275088548364400416034343698204186575808495616 * v1)) * v6);
    signal sig_11;
    sig_11 <== 1;
    component comp_12 = IsEqual();
    comp_12.in[0] <== sig_10;
    comp_12.in[1] <== sig_11;
    component comp_13 = IsZero();
    comp_13.in <== comp_12.out;
    component comp_14 = NOT();
    comp_14.in <== comp_13.out;
    comp_14.out === 1;
}

component main = main_template();
