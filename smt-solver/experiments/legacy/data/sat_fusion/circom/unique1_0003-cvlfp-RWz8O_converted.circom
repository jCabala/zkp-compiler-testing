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
    signal output scr1_x5_scr2_x1_fused;
    scr1_x5_scr2_x1_fused <-- ((scr1_x5 + scr2_x1) - (2 * (scr1_x5 * scr2_x1)));
    (scr1_x1 * (1 - scr1_x1)) === 0;
    (scr1_x2 * (1 - scr1_x2)) === 0;
    (scr1_x3 * (1 - scr1_x3)) === 0;
    (scr1_x4 * (1 - scr1_x4)) === 0;
    (scr1_x5 * (1 - scr1_x5)) === 0;
    (scr2_x1 * (1 - scr2_x1)) === 0;
    (scr1_x5_scr2_x1_fused * (1 - scr1_x5_scr2_x1_fused)) === 0;
    component comp_0 = NOT();
    comp_0.in <== scr1_x3;
    component comp_1 = NOT();
    comp_1.in <== scr1_x5;
    component comp_2 = AND();
    comp_2.a <== comp_0.out;
    comp_2.b <== comp_1.out;
    component comp_3 = NOT();
    comp_3.in <== scr1_x1;
    component comp_4 = AND();
    comp_4.a <== comp_2.out;
    comp_4.b <== comp_3.out;
    component comp_5 = NOT();
    comp_5.in <== scr1_x4;
    component comp_6 = AND();
    comp_6.a <== comp_4.out;
    comp_6.b <== comp_5.out;
    component comp_7 = AND();
    comp_7.a <== comp_6.out;
    comp_7.b <== scr1_x2;
    component comp_8 = AND();
    comp_8.a <== comp_7.out;
    comp_8.b <== scr1_x5_scr2_x1_fused;
    component comp_9 = IsZero();
    comp_9.in <== comp_8.out;
    component comp_10 = NOT();
    comp_10.in <== comp_9.out;
    comp_10.out === 1;
    log("<@> scr1_x5_scr2_x1_fused = ", scr1_x5_scr2_x1_fused);
}

component main = main_template();
