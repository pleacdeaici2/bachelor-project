from constatns import Constants


class Utils:
    @staticmethod
    def convert_to_bytes(size_string):
        size = int(size_string[:-1])  # Extract the numeric part of the string
        unit = size_string[-1].upper()  # Extract the unit (e.g., G, M, K)
        return size * Constants.units[unit]

    @staticmethod
    def convert_to_kilobytes(size_string):
        size = int(size_string[:-1])
        unit = size_string[-1].upper()
        return size * (Constants.units[unit] // 1024)

    @staticmethod
    def convert_to_megabytes(size_string):
        size = int(size_string[:-1])  # Extract the numeric part of the string
        unit = size_string[-1].upper()  # Extract the unit (e.g., G, M, K)
        return size * (Constants.units[unit] // (1024 ** 2))  # Convert to megabytes
