from serial.serialutil import SerialException
from typing import Optional
from fbs_runtime.application_context import cached_property
from fbs_runtime.application_context.PySide2 import ApplicationContext
from PySide2.QtCore import QObject, QTimer, Qt, Signal
from PySide2.QtGui import QCloseEvent
from PySide2.QtSvg import QSvgWidget
from PySide2.QtWidgets import QAction, QFileDialog, QFrame, QLabel, QLineEdit, QMainWindow, QMenu, QPushButton, QSpinBox, QStackedWidget, QTextEdit
from QtDesign.QtdUiTools import loadUi

import itertools
import os
import re
import serial
import serial.tools.list_ports as serial_ports
import shutil


class AppContext(ApplicationContext):
    
    def run(self):
        self.arduino_design.show()
        return self.app.exec_()

    @cached_property
    def arduino_design(self):
        return ArduinoDesign(self)


class SerialManager(QObject):
    received = Signal(bytes)

    def __init__(self, port: str = "") -> None:
        super().__init__()
        self.arduino = None
        self._port = port
        self.timer = None

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, serial_port: str):
        self._port = serial_port
        self.start()

    def start(self):
        self.arduino = serial.Serial(port = self._port, baudrate = 115200, timeout = 0.01)

        self.timer = QTimer()
        self.timer.timeout.connect(self._receive)
        self.timer.start(250)

        self.arduino.reset_input_buffer()

    def stop(self):
        try:
            self.timer.stop()
            self.arduino.close()
            self._port = ""
        except AttributeError:
            pass

    def _receive(self):
        data = self.read()
        if data is not None and len(data) > 0:
            self.received.emit(data)

    def read(self):
        try:
            if not self.arduino.isOpen(): self.start()
            return self.arduino.readline()
        except SerialException:
            self.timer.stop()
            self.arduino.close()

    def write(self, msg: str):
        try:
            if not self.arduino.isOpen(): self.start()
            self.arduino.write(msg)
        except SerialException as exc:
            self.timer.stop()
            self.arduino.close()
            self.received.emit("SerialException: {}\n".format(str(exc)).encode('utf-8'))


class ArduinoDesign(QMainWindow):

    def __init__(self, context: AppContext) -> None:
        super().__init__()

        self.context = context
        self.serial_manager = SerialManager()
        self.serial_ports: list[QAction] = []

        self.serial_manager.received.connect(self.parse_message)

        self.setup_ui()
        self.list_serial()

        if len(self.serial_ports) > 0:
            self.serial_ports[0].setChecked(True)
            self.set_serial(self.serial_ports[0])

        self.timer = QTimer()
        self.timer.timeout.connect(self.list_serial)
        self.timer.start(10000)

    def setup_ui(self):
        loadUi(self.context.get_resource("gui/devino_utility.ui"), self)

        self.act_save_lib: QAction
        self.btn_send: QPushButton
        self.frm_arduino_svg: QFrame
        self.lbl_arduino: QLabel
        self.le_sender: QLineEdit
        self.te_serial_monitor: QTextEdit

        self.mnu_tools: QMenu
        self.mnu_port: QMenu
        self.act_none: QAction

        self.act_save_lib.triggered.connect(self.save_lib)
        self.mnu_port.triggered[QAction].connect(self.set_serial)

        # Add Arduino Uno Reference Image
        self.svg_arduino_uno = QSvgWidget(self.context.get_resource("images/ArduinoUno.svg"))
        self.svg_arduino_uno.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        self.svg_arduino_uno.setMinimumWidth(256)
        self.frm_arduino_svg.layout().addWidget(self.svg_arduino_uno)

        # Generate dictionary of controls displays
        self.analog_widgets: dict[str, QLineEdit] = {
            "A0": self.le_a0,
            "A1": self.le_a1,
            "A2": self.le_a2,
            "A3": self.le_a3,
            "A4": self.le_a4,
            "A5": self.le_a5
        }

        self.digital_widgets: dict[str, tuple[QPushButton, Optional[QStackedWidget]]] = {
            "D2": (self.btn_d2_mode, None),
            "D3": (self.btn_d3_mode, self.swgt_d3),
            "D4": (self.btn_d4_mode, None),
            "D5": (self.btn_d5_mode, self.swgt_d5),
            "D6": (self.btn_d6_mode, self.swgt_d6),
            "D7": (self.btn_d7_mode, None),
            "D8": (self.btn_d8_mode, None),
            "D9": (self.btn_d9_mode, self.swgt_d9),
            "D10": (self.btn_d10_mode, self.swgt_d10),
            "D11": (self.btn_d11_mode, self.swgt_d11),
            "D12": (self.btn_d12_mode, None),
            "D13": (self.btn_d13_mode, None)
        }

        self.pwm_widgets: dict[str, tuple[QSpinBox, QStackedWidget]] = {
            "A3": (self.sbx_d3_pwm, self.swgt_d3),
            "A5": (self.sbx_d5_pwm, self.swgt_d5),
            "A6": (self.sbx_d6_pwm, self.swgt_d6),
            "A9": (self.sbx_d9_pwm, self.swgt_d9),
            "A10": (self.sbx_d10_pwm, self.swgt_d10),
            "A11": (self.sbx_d11_pwm, self.swgt_d11)
        }

    def save_lib(self):
        root_path = os.path.join(os.path.expanduser('~'), "Documents", "Arduino")
        if not os.path.isdir(root_path): root_path = os.path.expanduser('~')

        folder = QFileDialog.getExistingDirectory(self, "Select Directory", root_path, QFileDialog.ShowDirsOnly)
        if len(folder) > 0 and os.path.isdir(folder):
            lib_dir = os.path.join(folder, "Devino")
            if not os.path.isdir(lib_dir): os.mkdir(lib_dir)
            shutil.copy(self.context.get_resource("library/Devino.cpp"), lib_dir)
            shutil.copy(self.context.get_resource("library/Devino.h"), lib_dir)

    def set_serial(self, port: QAction):
        if port.isChecked():
            self.serial_manager.port = port.text().split(" ")[0]
            self.mnu_port.setTitle(f"Port: {self.serial_manager.port}")

            for act_port in self.serial_ports:
                act_port.setChecked(False)
            
            port.setChecked(True)
        else:
            self.serial_manager.stop()
            self.list_serial()

    def setup_serial(self):
        self.btn_send.clicked.connect(lambda: self.send_message(bytes(self.le_sender.text(), 'utf-8')))
        self.le_sender.returnPressed.connect(lambda: self.send_message(bytes(self.le_sender.text(), 'utf-8')))

    def list_serial(self):
        for action in self.serial_ports: self.mnu_port.removeAction(action)
        self.mnu_port.setTitle(f"Port: None")
        self.serial_ports = []

        for port, desc, hwid in sorted(serial_ports.comports()):
            if "VID:PID=2A03:0043" in hwid or "VID:PID=2341:0043" in hwid:
                action = QAction(f"{port} (Arduino Uno)")
            else:
                action = QAction(f"{port}")

            action.setCheckable(True)
            self.mnu_port.addAction(action)
            self.serial_ports.append(action)

            if port == self.serial_manager.port:
                action.setChecked(True)
                self.mnu_port.setTitle(f"Port: {self.serial_manager.port}")

    def send_message(self, msg: bytes):
        self.le_sender.setText("")
        self.serial_manager.write(msg)

    def parse_message(self, msg: bytes):
        try:
            msg_str = msg.decode('utf-8')
        except UnicodeDecodeError:
            pass
        else:
            for data in list(itertools.chain.from_iterable(data.split(",") for data in re.findall(r"<(.*?)>", msg_str))):
                if data[:2] == "RA": self.update_analog_display(data)
                elif data[:2] == "WA": self.update_pwm_display(data)
                elif data[1] == "D": self.update_digital_display(data, data[0] == "W")

                msg_str = msg_str.replace(f"<{data}>", "")

            self.print_message(msg_str)

    def print_message(self, msg: str):
        self.te_serial_monitor.insertPlainText(msg)

    def update_analog_display(self, data: str):
        line_edit = self.analog_widgets.get(data.split(" ")[0][1:], None)
        if line_edit is not None and not line_edit.text() == data.split(" ")[1]: line_edit.setText(data.split(" ")[1])

    def update_pwm_display(self, data: str):
        pwm_widget = self.pwm_widgets.get(data.split(" ")[0][1:], (None, None))
        spinbox = pwm_widget[0]
        stacked_widget = pwm_widget[1]

        if spinbox is not None:
            spinbox.setValue(int(data.split(" ")[1]))
            if not stacked_widget.currentIndex() == 1:
                stacked_widget.setCurrentIndex(1)
                spinbox.setEnabled(True)
                spinbox.setKeyboardTracking(False)
                spinbox.valueChanged.connect(lambda: self.set_pwm(data[2], spinbox))

    def update_digital_display(self, data: str, writeable: bool):
        digital_widget = self.digital_widgets.get(data.split(" ")[0][1:], (None, None))
        button = digital_widget[0]
        stacked_widget = digital_widget[1]

        if button is not None:
            button.setText("HIGH" if int(data.split(" ")[1]) > 0 else "LOW")
            if writeable and not button.isEnabled():
                button.setEnabled(True)
                button.clicked.connect(lambda: self.set_digital(data[2], button))

    def set_digital(self, pin: int, button: QPushButton):
        button_text = button.text()
        button.setText("HIGH" if button_text == "LOW" else "LOW")
        self.send_message(bytes("<set d {} {}>".format(pin, 0 if button_text == "HIGH" else 1), 'utf-8'))

    def set_pwm(self, pin: int, spinbox: QSpinBox):
        if spinbox.hasFocus(): spinbox.clearFocus()
        self.send_message(bytes("<set a {} {}>".format(pin, spinbox.value()), 'utf-8'))

    def closeEvent(self, event: QCloseEvent) -> None:
        return super().closeEvent(event)

if __name__ == '__main__':
    app_context = AppContext()
    app_context.run()
