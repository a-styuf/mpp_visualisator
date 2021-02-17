import serial
import serial.tools.list_ports
import my_crc16
import time
import numpy as np


class Device:
    def __init__(self, **kw):
        self.serial_numbers = ["A700ECSA"]  # это лист возможных серийников!!! (не строка)
        self.baudrate = 38400
        self.timeout = 0.3
        self.id = 0x06
        self.port = "COM0"
        self.read_row_data = b""
        self.send_row_data = b""
        self.a = 1
        self.b = 0
        self.serial = None
        self.dev_offset = 0
        for key in sorted(kw):
            if key == "serial_numbers":
                self.serial_numbers = kw.pop(key)
            elif key == "baudrate":
                self.baudrate = kw.pop(key)
            elif key == "timeout":
                self.baudrate = kw.pop(key)
            elif key == "port":
                self.baudrate = kw.pop(key)
            elif key == "id":
                self.id = kw.pop(key)
            elif key == "a":
                self.a = kw.pop(key)
            elif key == "b":
                self.b = kw.pop(key)
            elif key == "dev_offset":
                self.offset = kw.pop(key)
            else:
                pass
        self.state = 0
        self._connect_serial_by_ser_num()
        # data
        self.osc_time = [0 for i in range(512)]
        self.osc_freq = [0 for i in range(256)]
        self.osc_data = [0 for i in range(512)]
        self.osc_spectra = [0 for i in range(256)]

        self.pulse_row_data = 0
        self.pulse_width = 0
        self.pulse_zero_count = 0
        self.pulse_peak = 0
        self.pulse_power = 0
        self.pulse_mean = 0
        self.pulse_noise = 0
        self.report = ""
        self.offset = 0
        self.total_pulse_num = 0
        self.arch_pulse_num = 0

    def _connect_serial_by_ser_num(self):  # функция для установки связи с устройством по его ID
        if self.serial:
            try:
                self.serial.close()
            except Exception:
                pass
        com_list = serial.tools.list_ports.comports()
        for com in com_list:
            for serial_number in self.serial_numbers:
                if com.serial_number is not None:
                    print(serial_number, com.serial_number)
                    if serial_number in com.serial_number:
                        try:
                            self.serial = serial.Serial(com.device, self.baudrate, timeout=self.timeout)
                            self.port = com.device
                            self.state = 1
                            return
                        except serial.serialutil.SerialException:
                            self.state = -1

    def reconnect(self):
        self._connect_serial_by_ser_num()

    def send_com(self, data_list):
        """
        Отправка команды в МПП. В конце, к отправленным данным приделывается crc16-ModBus
        :param data_list: лист с данными
        :return:
        """
        send_buff = data_list
        crc16 = my_crc16.calc_crc16_bytes(send_buff)
        send_buff.extend(crc16)
        if self.serial:
            self.serial.write(bytes(send_buff))
            self.send_row_data = bytes(send_buff)
            self.read_row_data = self.serial.read(256)
            if len(self.read_row_data) > len(self.send_row_data):
                self.read_row_data = self.read_row_data[len(send_buff):]
                self.state = 1
            else:
                self.state = -1
        else:
            self.state = -1
        return self.read_row_data

    def set_offset(self, offset=0.0):
        # установка уставки МПП
        self.offset = offset
        mpp_offset_adc = int(offset / self.a)
        # print("Уставка: ", mpp_offset_adc, hex(mpp_offset_adc))
        # установка порогового уровня регистрации помехиУстановка порогового уровня регистрации помехи по F6
        send_data = [self.id, 0x06, 0x00, 0x00, (mpp_offset_adc >> 8) & 0xFF, mpp_offset_adc & 0xFF]
        read_data = self.send_com(send_data)
        # print(bytes_array_to_str(send_data), bytes_array_to_str(read_data))
        self.report = "Уставка: %d (0x%04X) ->%s -<%s" % (mpp_offset_adc,
                                                          mpp_offset_adc,
                                                          bytes_array_to_str(send_data),
                                                          bytes_array_to_str(read_data))

    def registration_single_ena(self):
        read_data = self.send_com([self.id, 0x06, 0x00, 0x01, 0x00, 0x02])
        # print(bytes_array_to_str(read_data))
        self.report = "Единичные запуск МПП%d: -<%s" % (self.id, bytes_array_to_str(read_data))

    def registration_contin_ena(self, ena=False):
        if ena:
            read_data = self.send_com([self.id, 0x06, 0x00, 0x01, 0x00, 0x01])
            state = "Запуск"
        else:
            read_data = self.send_com([self.id, 0x06, 0x00, 0x01, 0x00, 0x00])
            state = "Остановка"
        self.report = "%s МПП%d: <-%s" % (state, self.id, bytes_array_to_str(read_data))

    def pulse_waiting(self, try_num=10):
        num_new, num_old = 0, 100000
        report = ""
        for i in range(try_num):
            read_data = self.send_com([self.id, 0x03, 0x80, 0x00, 0x00, 0x02])
            report += "Ожидаем помехи %d: <-%s" % (i, bytes_array_to_str(read_data))
            if read_data:
                num_new = int.from_bytes(read_data[3:7], byteorder='big', signed=False)
                report += "\n \t Кол-во помех: %d\n" % num_new
                if num_new > num_old:
                    break
                num_old = num_new
                self.total_pulse_num = num_new
        self.report = report

    def initialisation(self):
        read_data = self.send_com([self.id, 0x10, 0x7F, 0xFF, 0x00, 0x02, 0x04, 0x12, 0x34, 0x56, 0x78])
        self.report = "Инициализация МПП%d: <-%s" % (self.id, bytes_array_to_str(read_data))

    def read_newest_pulse(self):
        read_data = self.send_com([self.id, 0x03, 0x00, 0x7A, 0x00, 0x10])
        report = "Чтение самой свежей помехи МПП%d, <-%s" % (self.id, bytes_array_to_str(read_data))
        self.report = report

    def read_by_lifetime_pulse(self):
        read_data = self.send_com([self.id, 0x03, 0x00, 0x6A, 0x00, 0x10])
        report = "Чтение помехи c наибольшим временем жизни МПП%d, <-%s" % (self.id, bytes_array_to_str(read_data))
        self.report = report

    def osc_read(self):
        i, k = 0, 0
        row_osc_data = []
        while i < 8 and k < 50:
            read_data = self.send_com([self.id, 0x03, 0xA0 + ((i * 0x40) // 256), (i * 0x40) % 256, 0x00, 0x40])
            if read_data:
                i += 1
                if read_data[2] == 128:
                    row_osc_data += read_data[3:3 + 128]
            else:
                k += 1
        # сборка осциллограммы
        self.osc_data = []
        self.osc_time = []
        for i in range(len(row_osc_data) // 2):
            self.osc_data.append(self.a * int.from_bytes(row_osc_data[i * 2:(i + 1) * 2], byteorder='big', signed=True) + self.b)
            self.osc_time.append(float(i * 0.025))
        # подсчет спектра
        self.osc_freq = [(1 / (512 * 0.025)) * i for i in range(256)]
        self.osc_freq[0] = 0  # отрезаем постоянную составляющую
        self.osc_spectra = [0 for i in range(256)]
        if self.osc_data:
            spectra_complex = np.fft.fft(self.osc_data, len(self.osc_data))
            self.osc_spectra = [abs(var) for var in spectra_complex[:len(spectra_complex) // 2]]
            self.osc_spectra[0] = 0
        pass

    def data_pars(self, offset=0):
        """

        :param offset: 0 - БКАП, 2 - СКЭ-ЛР
        :return:
        """
        if self.read_row_data:
            self.pulse_row_data = self.read_row_data[3 + 8:3 + 8 + 24]
            self.pulse_width = int.from_bytes(self.pulse_row_data[8+offset:12+offset], byteorder='big') * 0.025
            self.pulse_zero_count = int.from_bytes(self.pulse_row_data[12+offset:14+offset], byteorder='big')
            self.pulse_peak = self.a * int.from_bytes(self.pulse_row_data[14+offset:16+offset], byteorder='big')
            self.pulse_power = self.a * int.from_bytes(self.pulse_row_data[16+offset:20+offset], byteorder='big') * 0.025
            self.pulse_mean = self.a * int.from_bytes(self.pulse_row_data[20+offset:22+offset], byteorder='big', signed=False) + self.b
            self.pulse_noise = self.a * int.from_bytes(self.pulse_row_data[22+offset:24+offset], byteorder='big') / 2 ** 4
        else:
            self.pulse_width = 0
            self.pulse_zero_count = 0
            self.pulse_peak = 0
            self.pulse_power = 0
            self.pulse_mean = 0
            self.pulse_noise = 0
        self.report = ("Полученный импульс: width={:.2E} us, z_c={:.2E}, peak={:.2E} V, power={:.2E} V*s, "
                       "mean={:.2E} V, noise={:.2E} V".
                       format(self.pulse_width, self.pulse_zero_count, self.pulse_peak, self.pulse_power,
                              self.pulse_mean, self.pulse_noise))
        pass

    def pulse_read(self):
        # установка уставки МПП
        self.set_offset(offset=self.offset)
        print(self.report)
        # запуск регистрации помех
        self.registration_contin_ena(ena=True)
        print(self.report)
        # ожидаем помеху из МПП
        self.pulse_waiting(try_num=10)
        print(self.report)
        # остановка регистрации помех
        self.registration_contin_ena(ena=False)
        print(self.report)
        # чтение самой новой помехи
        self.read_newest_pulse()
        print(self.report)
        self.data_pars(offset=self.dev_offset)
        print(self.report)
        self.osc_read()
        #
        pass


def bytes_array_to_str(bytes_array):
    bytes_string = "0x"
    for i, ch in enumerate(bytes_array):
        byte_str = (" %02X" % bytes_array[i])
        bytes_string += byte_str
    return bytes_string


def get_time():
    return time.strftime("%Y_%m_%d__%H-%M-%S", time.localtime())
