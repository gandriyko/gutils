import random
from faker.providers import BaseProvider


class Provider(BaseProvider):
    def random_phone(self):
        prefixes = ('38050', '38063', '38066', '38067', '38068', '38073',
                    '38091', '38092', '38093', '38094', '38095',
                    '38096', '38097', '38098', '38099')
        return '%s%07d' % (random.choice(prefixes), random.randint(0, 9999999))
