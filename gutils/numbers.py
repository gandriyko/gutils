class MoneyBase:

    def _gen(self, value, gender=False):
        value = str(value)
        i = int(value)
        if i == 0:
            return ''
        if i < 20:
            if isinstance(self.r1[i], list):
                return self.r1[i][int(gender)]
            else:
                return self.r1[i]
        elif i < 100:
            o = self._gen(value[-1], gender)
            if o:
                return '%s %s' % (self.r2[int(value[-2]) - 2], o)
            else:
                return self.r2[int(value[-2]) - 2]
        elif i < 1000:
            o = self._gen(value[1:], gender)
            if o:
                return '%s %s' % (self.r3[int(value[-3]) - 1], o)
            else:
                return self.r3[int(value[-3]) - 1]

    def _ending(self, value, array):
        value = str(value)
        last_d = int(value[-1])
        last = int(value[-2:])
        if last > 10 and last < 20 or last_d > 4 and last_d < 10:
            return array[2]
        elif last_d == 1:
            return array[0]
        elif last_d > 1 and last_d < 5:
            return array[1]
        else:
            return array[2]

    def make(self, value):
        result = []
        value = '%0.2f' % value
        value, kop = value.split('.')
        if not value:
            return '%s %s' % (self.r1[0], self._ending(value, self.e1))
        if int(value) > 1000000:
            sub_value = value[:-6]
            result.append(self._gen(sub_value))
            result.append(self._ending(sub_value, self.e2))
            value = value[-6:]
        if int(value) > 1000:
            sub_value = value[:-3]
            result.append(self._gen(sub_value, True))
            result.append(self._ending(sub_value, self.e1))
            value = value[-3:]
        result.append(self._gen(value, True))
        result.append(self._ending(value, self.m1))
        result.append(kop)
        result.append(self._ending(kop, self.m2))
        return ' '.join([r for r in result if r]).capitalize()


class Money_RU_UAH(MoneyBase):
    r1 = [
        'ноль', ['один', 'одна'], ['два', 'две'], 'три', 'четыре', 'пять',
        'шесть', 'сем', 'восемь', 'девять', 'десять', 'одиннадцать',
        'двенадцать', 'тринадцать', 'четырнадцать', 'пятнадцать',
        'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать']

    r2 = [
        'двадцать', 'тридцать', 'сорок', 'пятьдесят', 'шестьдесят',
        'семьдесят', 'восемьдесят', 'девяносто']

    r3 = [
        'сто', 'двести', 'триста', 'четыриста', 'пятьсот', 'шестьсот',
        'семьсот', 'восемьсот', 'девятьсот']

    e1 = ['тысяча', 'тысячи', 'тисяч']
    e2 = ['миллион', 'миллиона', 'миллионов']
    m1 = ['гривна', 'гривны', 'гривен']
    m2 = ['копейка', 'копейки', 'копеек']


class Money_RU_EUR(Money_RU_UAH):
    m1 = ['евро', 'евро', 'евро']
    m2 = ['евроцент', 'евроцента', 'евроцентов']


class Money_RU_PLN(Money_RU_UAH):
    m1 = ['злотый', 'злотых', 'злотых']
    m2 = ['грош', 'гроша', 'грошей']


class Money_RU_ERP(Money_RU_EUR):
    pass


class Money_RU_USD(Money_RU_UAH):
    m1 = ['доллар', 'доллара', 'долларов']
    m2 = ['цент', 'цента', 'центов']


class Money_UK_UAH(MoneyBase):
    r1 = [
        'ноль', ['один', 'одна'], ['два', 'дві'], 'три', 'чотири',
        'п\'ять', 'шість', 'сім', 'вісім', 'дев\'ять', 'десять',
        'одинадцять', 'дванадцять', 'тринадцять', 'чотирнадцять',
        'п\'ятнадцять', 'шістнадцять', 'сімнадцять', 'вісімнадцять',
        'дев\'ятнадцять'
    ]

    r2 = [
        'двадцять', 'тридцять', 'сорок', 'п\'ятдесят', 'шістдесят',
        'сімдесят', 'вісімдесят', 'дев\'яносто']

    r3 = [
        'сто', 'двісті', 'триста', 'чотириста', 'п\'ятсот', 'шістсот',
        'сімсот', 'вісімсот', 'дев\'ятсот']
    e1 = ['тисяча', 'тисячі', 'тисяч']
    e2 = ['мільйон', 'мільони', 'мільйонів']
    m1 = ['гривня', 'гривні', 'гривень']
    m2 = ['копійка', 'копійки', 'копійок']


class Money_UK_EUR(Money_UK_UAH):
    m1 = ['євро', 'євро', 'євро']
    m2 = ['євроцент', 'євроцента', 'євроцентів']


class Money_UK_ERP(Money_UK_EUR):
    pass


class Money_UK_USD(Money_UK_UAH):
    m1 = ['долар', 'долари', 'доларів']
    m2 = ['цент', 'цента', 'центів']


class Money_UK_PLN(Money_UK_UAH):
    m1 = ['злотий', 'злотих', 'злотих']
    m2 = ['грош', 'гроша', 'грошей']


def get_money(language, currency_name):
    return globals()['Money_%s_%s' % (language.upper(), currency_name.upper())]()
