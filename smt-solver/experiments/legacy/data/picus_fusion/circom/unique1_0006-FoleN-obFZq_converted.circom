pragma circom 2.0.6;

include "../circomlib/comparators.circom";

include "../circomlib/gates.circom";

template main_template() {
    signal input scr1_x1;
    signal input scr1_x2;
    signal input scr1_x3;
    signal input scr1_x4;
    signal input scr2_x1;
    signal output scr1_x4_scr2_x1_fused;
    scr1_x4_scr2_x1_fused <-- ((scr1_x4 + scr2_x1) - (2 * (scr1_x4 * scr2_x1)));
    (scr1_x1 * (1 - scr1_x1)) === 0;
    (scr1_x2 * (1 - scr1_x2)) === 0;
    (scr1_x3 * (1 - scr1_x3)) === 0;
    (scr1_x4 * (1 - scr1_x4)) === 0;
    (scr2_x1 * (1 - scr2_x1)) === 0;
    (scr1_x4_scr2_x1_fused * (1 - scr1_x4_scr2_x1_fused)) === 0;
    component comp_0 = NOT();
    comp_0.in <== scr1_x3;
    component comp_1 = NOT();
    comp_1.in <== scr1_x4_scr2_x1_fused;
    component comp_2 = AND();
    comp_2.a <== comp_0.out;
    comp_2.b <== comp_1.out;
    component comp_3 = AND();
    comp_3.a <== comp_2.out;
    comp_3.b <== scr1_x1;
    component comp_4 = NOT();
    comp_4.in <== scr1_x2;
    component comp_5 = AND();
    comp_5.a <== comp_3.out;
    comp_5.b <== comp_4.out;
    component comp_6 = NOT();
    comp_6.in <== scr2_x1;
    component comp_7 = AND();
    comp_7.a <== comp_5.out;
    comp_7.b <== comp_6.out;
    component comp_8 = IsZero();
    comp_8.in <== comp_7.out;
    component comp_9 = NOT();
    comp_9.in <== comp_8.out;
    comp_9.out === 1;
    log("<@> scr1_x4_scr2_x1_fused = ", scr1_x4_scr2_x1_fused);
}

component main = main_template();
