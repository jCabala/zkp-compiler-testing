pragma circom 2.0.6;

include "../circomlib/gates.circom";

include "../circomlib/comparators.circom";

template main_template() {
    signal input scr1_x1;
    signal input scr1_x2;
    signal input scr1_x3;
    signal input scr1_x4;
    signal input scr2_x1;
    signal output scr1_x1_scr2_x1_fused;
    scr1_x1_scr2_x1_fused <-- ((scr1_x1 + scr2_x1) - (2 * (scr1_x1 * scr2_x1)));
    (scr1_x1 * (1 - scr1_x1)) === 0;
    (scr1_x2 * (1 - scr1_x2)) === 0;
    (scr1_x3 * (1 - scr1_x3)) === 0;
    (scr1_x4 * (1 - scr1_x4)) === 0;
    (scr2_x1 * (1 - scr2_x1)) === 0;
    (scr1_x1_scr2_x1_fused * (1 - scr1_x1_scr2_x1_fused)) === 0;
    component comp_0 = NOT();
    comp_0.in <== scr1_x3;
    component comp_1 = OR();
    comp_1.a <== scr1_x1_scr2_x1_fused;
    comp_1.b <== comp_0.out;
    component comp_2 = NOT();
    comp_2.in <== scr1_x3;
    component comp_3 = NOT();
    comp_3.in <== scr1_x1_scr2_x1_fused;
    component comp_4 = OR();
    comp_4.a <== comp_2.out;
    comp_4.b <== comp_3.out;
    component comp_5 = AND();
    comp_5.a <== comp_1.out;
    comp_5.b <== comp_4.out;
    component comp_6 = NOT();
    comp_6.in <== scr1_x1;
    component comp_7 = AND();
    comp_7.a <== comp_5.out;
    comp_7.b <== comp_6.out;
    component comp_8 = NOT();
    comp_8.in <== scr1_x4;
    component comp_9 = AND();
    comp_9.a <== comp_7.out;
    comp_9.b <== comp_8.out;
    component comp_10 = NOT();
    comp_10.in <== scr1_x2;
    component comp_11 = AND();
    comp_11.a <== comp_9.out;
    comp_11.b <== comp_10.out;
    component comp_12 = NOT();
    comp_12.in <== scr2_x1;
    component comp_13 = AND();
    comp_13.a <== comp_11.out;
    comp_13.b <== comp_12.out;
    component comp_14 = IsZero();
    comp_14.in <== comp_13.out;
    component comp_15 = NOT();
    comp_15.in <== comp_14.out;
    comp_15.out === 1;
    log("<@> scr1_x1_scr2_x1_fused = ", scr1_x1_scr2_x1_fused);
}

component main = main_template();
