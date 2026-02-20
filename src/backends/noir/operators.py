from enum import StrEnum


class Operator(StrEnum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"

    # Noir uses bitwise-style boolean operators.
    LAND = "&"
    LOR = "|"
    LXOR = "^"
    NOT = "!"

    EQU = "=="
    NEQ = "!="
    LTH = "<"
    LEQ = "<="
    GTH = ">"
    GEQ = ">="
