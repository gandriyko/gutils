from django.utils.encoding import force_str
from django.utils import formats
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, ROUND_UP, InvalidOperation, Context
from six import string_types
import re


def to_decimal(value, round=-1, rounding=ROUND_HALF_EVEN):
    try:
        if value is None or value == '':
            result = Decimal(0)
        elif isinstance(value, Decimal):
            result = value
        elif isinstance(value, float):
            result = Decimal("%.15g" % value)
        elif isinstance(value, string_types):
            try:
                value = re.sub(r'[^\d\.\-]', '', value.replace(',', '.'))
                result = Decimal(value)
            except Exception:
                return Decimal(0)
        else:
            result = Decimal(value)
        if round >= 0:
            result = result.quantize(decimal_digits(round), rounding=rounding)
    except TypeError:
        result = Decimal(0)
    return result


def decimal_digits(n):
    if n <= 0:
        n = '0'
    else:
        n = '0.%s1' % ('0' * (n - 1))
    return Decimal(n)


def decimal_mult(a, b, round=-1):
    a = to_decimal(a)
    b = to_decimal(b)
    res = a * b
    return to_decimal(res, round)


def decimal_div(a, b, round=-1):
    a = to_decimal(a)
    b = to_decimal(b)
    res = a / b
    return to_decimal(res, round)


def decimal_adjust(a, percent, round=-1):
    # a = to_decimal(a)
    # percent = to_decimal(percent)
    res = a + a * percent / 100
    return to_decimal(res, round)


def decimal_average(a, b, a_qty, b_qty):
    a = to_decimal(a)
    b = to_decimal(b)
    a_qty = to_decimal(a_qty)
    b_qty = to_decimal(b_qty)
    return to_decimal(a * a_qty + b * b_qty) / (a_qty + b_qty)


def decimal_round(value):
    if not value:
        return Decimal('0.00')
    value = to_decimal(value)
    if value < 5:
        if value % 1 <= Decimal('0.5'):
            return Decimal(int(value) + Decimal('0.50'))
    return value.quantize(Decimal('1'), rounding=ROUND_UP)


pos_inf = 1e200 * 1e200
neg_inf = -1e200 * 1e200
nan = (1e200 * 1e200) // (1e200 * 1e200)
special_floats = [str(pos_inf), str(neg_inf), str(nan)]


def decimal_format(text, arg=-1):
    try:
        input_val = force_str(text)
        d = Decimal(input_val)
    except UnicodeEncodeError:
        return ''
    except InvalidOperation:
        if input_val in special_floats:
            return input_val
        try:
            d = Decimal(force_str(float(text)))
        except (ValueError, InvalidOperation, TypeError, UnicodeEncodeError):
            return ''
    try:
        p = int(arg)
    except ValueError:
        return input_val

    try:
        m = int(d) - d
    except (ValueError, OverflowError, InvalidOperation):
        return input_val

    if not m and p < 0:
        return formats.number_format('%d' % (int(d)), 0)

    if p == 0:
        exp = Decimal(1)
    else:
        exp = Decimal('1.0') / (Decimal(10) ** abs(p))
    try:
        # Set the precision high enough to avoid an exception, see #15789.
        tupl = d.as_tuple()
        units = len(tupl[1]) - tupl[2]
        prec = abs(p) + units + 1

        # Avoid conversion to scientific notation by accessing `sign`, `digits`
        # and `exponent` from `Decimal.as_tuple()` directly.
        sign, digits, exponent = d.quantize(exp, ROUND_HALF_UP,
                                            Context(prec=prec)).as_tuple()
        digits = [force_str(digit) for digit in reversed(digits)]
        while len(digits) <= abs(exponent):
            digits.append('0')
        digits.insert(-exponent, '.')
        if sign:
            digits.append('-')
        number = ''.join(reversed(digits))
        return formats.number_format(number, abs(p))
    except InvalidOperation:
        return input_val
