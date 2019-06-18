from factory import fuzzy, random


class PhoneFuzzy(fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        prefixes = ('38050', '38063', '38066', '38067', '38068', '38073',
                    '38091', '38092', '38093', '38094', '38095',
                    '38096', '38097', '38098', '38099')
        return '%s%07d' % (random.randgen.choice(prefixes), random.randgen.randrange(0, 9999999))

