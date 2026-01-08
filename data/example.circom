template Circuit() {
    signal input x;
    signal input y;
    
    x * 123123 === 1;
    x * y === 1;
}

component main = Circuit();