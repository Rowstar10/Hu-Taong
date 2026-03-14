class SettingBase:

    def __init__(self, key, label):
        self.key = key
        self.label = label

class DropdownSetting(SettingBase):

    def __init__(self, key, label, options):
        super().__init__(key, label)
        self.options = options

class SliderSetting(SettingBase):

    def __init__(self, key, label, min_val, max_val, step=1):
        super().__init__(key, label)
        self.min = min_val
        self.max = max_val
        self.step = step

class CycleSetting(SettingBase):

    def __init__(self, key, label, values):
        super().__init__(key, label)
        self.values = values

class ToggleSetting(SettingBase):

    def __init__(self, key, label):
        super().__init__(key, label)
