from decimal import Decimal
from django.conf import settings
from django.utils.safestring import mark_safe
from django.test import SimpleTestCase

def format(
    number,
    decimal_sep,
    decimal_pos=None,
    grouping=0,
    thousand_sep="",
    force_grouping=False,
    use_l10n=None,
):
    if number is None or number == "":
        return mark_safe(number)
    use_grouping = (
        use_l10n or (use_l10n is None and settings.USE_L10N)
    ) and settings.USE_THOUSAND_SEPARATOR
    use_grouping = use_grouping or force_grouping
    use_grouping = use_grouping and grouping != 0
    if isinstance(number, int) and not use_grouping and decimal_pos is None:
        return mark_safe(number)
    sign = ""
    if isinstance(number, float) and "e" in str(number).lower():
        number = Decimal(str(number))
    if isinstance(number, Decimal):
        if decimal_pos is not None:
            cutoff = Decimal("0." + "1".rjust(decimal_pos, "0"))
            if abs(number) < cutoff:
                number = Decimal("0")
        _, digits, exponent = number.as_tuple()
        if abs(exponent) + len(digits) > 200:
            number = "{:e}".format(number)
            coefficient, exponent = number.split("e")
            coefficient = format(
                coefficient,
                decimal_sep,
                decimal_pos,
                grouping,
                thousand_sep,
                force_grouping,
                use_l10n,
            )
            return "{}e{}".format(coefficient, exponent)
        else:
            str_number = "{:f}".format(number)
    else:
        str_number = str(number)
    if str_number[0] == "-":
        sign = "-"
        str_number = str_number[1:]
    if "." in str_number:
        int_part, dec_part = str_number.split(".")
        if decimal_pos is not None:
            dec_part = dec_part[:decimal_pos]
    else:
        int_part, dec_part = str_number, ""
    if decimal_pos is not None:
        dec_part = dec_part + ("0" * (decimal_pos - len(dec_part)))
    dec_part = dec_part and decimal_sep + dec_part
    if use_grouping:
        try:
            intervals = list(grouping)
        except TypeError:
            intervals = [grouping, 0]
        active_interval = intervals.pop(0)
        int_part_gd = ""
        cnt = 0
        for digit in int_part[::-1]:
            if cnt and cnt == active_interval:
                if intervals:
                    active_interval = intervals.pop(0) or active_interval
                int_part_gd += thousand_sep[::-1]
                cnt = 0
            int_part_gd += digit
            cnt += 1
        int_part = int_part_gd[::-1]
    return sign + int_part + dec_part

class NumberFormatTests(SimpleTestCase):
    def test_format_none(self):
        result = format(None, ".", 2)
        self.assertEqual(result, mark_safe(None))

    def test_format_empty_string(self):
        result = format("", ".", 2)
        self.assertEqual(result, mark_safe(""))

    def test_format_integer_without_grouping(self):
        result = format(123456, ".", None, 0)
        self.assertEqual(result, mark_safe(123456))

    def test_format_integer_with_grouping(self):
        result = format(1234567, ".", None, 3, ",")
        self.assertEqual(result, mark_safe("1,234,567"))

    def test_format_float(self):
        result = format(1234.5678, ".", 2)
        self.assertEqual(result, mark_safe("1234.57"))

    def test_format_decimal(self):
        result = format(Decimal('1234.5678'), ".", 2)
        self.assertEqual(result, mark_safe("1234.57"))

    def test_format_large_decimal(self):
        result = format(Decimal('1e+300'), ".", None)
        self.assertEqual(result, mark_safe("1e+300"))

    def test_format_small_decimal(self):
        result = format(Decimal('0.00001'), ".", 2)
        self.assertEqual(result, mark_safe("0.00"))

    def test_format_negative_integer(self):
        result = format(-123456, ".", None, 0)
        self.assertEqual(result, mark_safe("-123456"))

    def test_format_negative_float(self):
        result = format(-1234.5678, ".", 2)
        self.assertEqual(result, mark_safe("-1234.57"))

    def test_format_with_thousand_separator(self):
        result = format(1234567.89, ".", 2, 3, ",")
        self.assertEqual(result, mark_safe("1,234,567.89"))

    def test_format_with_custom_decimal_and_thousand_separator(self):
        result = format(1234567.89, ",", 2, 3, ".")
        self.assertEqual(result, mark_safe("1.234.567,89"))

    def test_format_with_force_grouping(self):
        result = format(1234567, ".", None, 3, ",", force_grouping=True)
        self.assertEqual(result, mark_safe("1,234,567"))

    def test_format_with_use_l10n(self):
        settings.USE_L10N = True
        settings.USE_THOUSAND_SEPARATOR = True
        result = format(1234567.89, ".", 2, 3, ",", use_l10n=True)
        self.assertEqual(result, mark_safe("1,234,567.89"))

    def test_format_float_with_exponential(self):
        result = format(1.23e10, ".", 2)
        self.assertEqual(result, mark_safe("12,300,000,000.00"))

    def test_format_decimal_with_exponential(self):
        result = format(Decimal('1.23e10'), ".", 2)
        self.assertEqual(result, mark_safe("12,300,000,000.00"))

    def test_format_large_negative_decimal(self):
        result = format(Decimal('-1e+300'), ".", None)
        self.assertEqual(result, mark_safe("-1e+300"))

    def test_format_zero_decimal(self):
        result = format(Decimal('0'), ".", 2)
        self.assertEqual(result, mark_safe("0.00"))

    def test_format_decimal_with_more_decimal_places(self):
        result = format(Decimal('1234.56789'), ".", 4)
        self.assertEqual(result, mark_safe("1234.5678"))

    def test_format_integer_with_zero_decimal_pos(self):
        result = format(123456, ".", 0)
        self.assertEqual(result, mark_safe("123456"))

    def test_format_float_with_zero_decimal_pos(self):
        result = format(1234.5678, ".", 0)
        self.assertEqual(result, mark_safe("1235"))

    def test_format_decimal_with_zero_decimal_pos(self):
        result = format(Decimal('1234.5678'), ".", 0)
        self.assertEqual(result, mark_safe("1235"))

    def test_format_negative_decimal_with_zero_decimal_pos(self):
        result = format(Decimal('-1234.5678'), ".", 0)
        self.assertEqual(result, mark_safe("-1235"))

    def test_format_decimal_with_high_precision(self):
        result = format(Decimal('1234.567890123456789'), ".", 10)
        self.assertEqual(result, mark_safe("1234.5678901234"))