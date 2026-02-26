pragma circom 2.0.6;

include "../circomlib/gates.circom";

include "../circomlib/comparators.circom";

template main_template() {
    signal input scr1_x1;
    signal input scr1_x2;
    signal input scr1_x3;
    signal input scr1_x4;
    signal input scr1_x5;
    signal input scr2_x1;
    signal output scr1_x4_scr2_x1_fused;
    scr1_x4_scr2_x1_fused <-- ((scr1_x4 + scr2_x1) - (2 * (scr1_x4 * scr2_x1)));
    (scr1_x1 * (1 - scr1_x1)) === 0;
    (scr1_x2 * (1 - scr1_x2)) === 0;
    (scr1_x3 * (1 - scr1_x3)) === 0;
    (scr1_x4 * (1 - scr1_x4)) === 0;
    (scr1_x5 * (1 - scr1_x5)) === 0;
    (scr2_x1 * (1 - scr2_x1)) === 0;
    (scr1_x4_scr2_x1_fused * (1 - scr1_x4_scr2_x1_fused)) === 0;
    component comp_0 = IsEqual();
    comp_0.in[0] <== scr1_x4_scr2_x1_fused;
    comp_0.in[1] <== scr2_x1;
    component comp_1 = NOT();
    comp_1.in <== comp_0.out;
    component comp_2 = AND();
    comp_2.a <== comp_1.out;
    comp_2.b <== scr1_x2;
    component comp_3 = AND();
    comp_3.a <== comp_2.out;
    comp_3.b <== scr1_x5;
    component comp_4 = NOT();
    comp_4.in <== scr1_x3;
    component comp_5 = NOT();
    comp_5.in <== scr1_x4;
    component comp_6 = OR();
    comp_6.a <== comp_4.out;
    comp_6.b <== comp_5.out;
    component comp_7 = AND();
    comp_7.a <== comp_3.out;
    comp_7.b <== comp_6.out;
    component comp_8 = NOT();
    comp_8.in <== scr1_x1;
    component comp_9 = AND();
    comp_9.a <== comp_7.out;
    comp_9.b <== comp_8.out;
    component comp_10 = IsEqual();
    comp_10.in[0] <== scr1_x4_scr2_x1_fused;
    comp_10.in[1] <== scr1_x4;
    component comp_11 = AND();
    comp_11.a <== comp_9.out;
    comp_11.b <== comp_10.out;
    component comp_12 = IsZero();
    comp_12.in <== comp_11.out;
    component comp_13 = NOT();
    comp_13.in <== comp_12.out;
    comp_13.out === 1;
    log("<@> scr1_x4_scr2_x1_fused = ", scr1_x4_scr2_x1_fused);
}

component main = main_template();
