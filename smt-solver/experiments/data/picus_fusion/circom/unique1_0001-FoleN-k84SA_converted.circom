pragma circom 2.0.6;

include "../circomlib/comparators.circom";

include "../circomlib/gates.circom";

template main_template() {
    signal input scr1_x1;
    signal input scr2_x1;
    signal output scr1_x1_scr2_x1_fused;
    scr1_x1_scr2_x1_fused <-- ((scr1_x1 + scr2_x1) - (2 * (scr1_x1 * scr2_x1)));
    (scr1_x1 * (1 - scr1_x1)) === 0;
    (scr2_x1 * (1 - scr2_x1)) === 0;
    (scr1_x1_scr2_x1_fused * (1 - scr1_x1_scr2_x1_fused)) === 0;
    component comp_0 = NOT();
    comp_0.in <== scr2_x1;
    component comp_1 = AND();
    comp_1.a <== scr1_x1_scr2_x1_fused;
    comp_1.b <== comp_0.out;
    component comp_2 = IsZero();
    comp_2.in <== comp_1.out;
    component comp_3 = NOT();
    comp_3.in <== comp_2.out;
    comp_3.out === 1;
    log("<@> scr1_x1_scr2_x1_fused = ", scr1_x1_scr2_x1_fused);
}

component main = main_template();
