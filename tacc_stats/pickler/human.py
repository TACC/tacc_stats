import time

def ftime(epoch, fmt="%b %d %H:%M:%S"):
    return time.strftime(fmt, time.localtime(epoch))

def fhms(t):
    t = int(t)
    s = ""
    if t < 0:
        t = -t
        s = "-"
    return "%s%02d:%02d:%02d" % (s, t / 3600, (t % 3600) / 60, t % 60)

# Based on coreutils human_readable()
# TODO Handle small values.
# TODO Add unit=""
# Way too complicated, no need to avoid use of floating point.
def fsize_and_unit(amt):
    amt = long(amt)
    sign = ""
    if amt < 0:
        sign = "-"
        amt = - amt
    fraction = ""
    prefix_letters = "KMGTPEZY"
    exponent_max = len(prefix_letters)
    exponent = 0
    base = 1024
    tenths = 0
    rounding = 0
    if base <= amt:
        while base <= amt and exponent < exponent_max:
            r10 = 10 * (amt % base) + tenths
            r2 = 2 * (r10 % base) + (rounding >> 1)
            amt /= base
            tenths = r10 / base
            if r2 < base:
                if r2 + rounding != 0:
                    rounding = 1
                else:
                    rounding = 0
            else:
                if base < r2 + rounding:
                    rounding = 3
                else:
                    rounding = 2
            exponent += 1
        if amt < 10:
            if 2 < rounding + (tenths & 1):
                tenths += 1
                rounding = 0
                if tenths == 10:
                    amt += 1
                    tenths = 0
            if amt < 10 and tenths != 0:
                fraction = "." + str(tenths)
                tenths = rounding = 0
    delta = 0
    if 0 < rounding + (amt & 1):
        delta = 1
    if 5 < tenths + delta:
        amt += 1
        if amt == base and exponent < exponent_max:
            exponent += 1
            fraction = ".0"
            amt = 1
    prefix = ""
    if exponent > 0:
        prefix = prefix_letters[exponent - 1]
    return (sign + str(amt) + fraction, prefix)

def fsize(amt, align=False, space=""):
    size_str, unit_str = fsize_and_unit(amt)
    if align:
        return size_str.rjust(4) + space + unit_str.rjust(1)
    else:
        return size_str + space + unit_str
