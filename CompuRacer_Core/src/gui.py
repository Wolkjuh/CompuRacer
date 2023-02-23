import json
import os
from typing import List, Any

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QPushButton, QMainWindow, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QMessageBox, QLineEdit, QHBoxLayout, QApplication


def load_json_batches(directory) -> List[Any]:
    file_names = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            with open(os.path.join(directory, filename), "r") as file:
                data = json.load(file)
                if "name" in data:
                    file_names.append(data["name"])

    return file_names


class MainGUI(QMainWindow):
    def __init__(self, racer, state, cmdprocessor) -> None:
        super().__init__()

        self.general_window = None
        self.batch_window = None
        self.current_batch = None
        self.data_requests = None
        self.table_widget = None

        self.command_processor = cmdprocessor
        self.racer = racer
        self.state = state

        self.batch_buttons = []

        self.load_json_requests()

        self.init_ui()

        return None

    def init_ui(self) -> None:
        self.showFullScreen()
        self.setWindowTitle("CompuRacer GUI")

        tabs = QTabWidget()
        general_tab = QWidget()
        logs_tab = QWidget()

        tabs.addTab(general_tab, "General")
        tabs.addTab(logs_tab, "Logs")

        vbox_general = QVBoxLayout()
        vbox_logs = QVBoxLayout()

        # --- Create and load in GUI --- #
        self.create_request_widget(vbox_general, general_tab)
        self.create_batch_widget(vbox_general, general_tab)
        self.create_logs_widget(vbox_logs, logs_tab)

        self.setCentralWidget(tabs)

        return None

    def create_request_widget(self, vbox, requests_tab) -> None:
        vbox.addWidget(QLabel("Requests Information"))

        # --- Creating Table --- #
        self.table_widget = QTableWidget(len(self.data_requests["requests"]), 6)
        self.table_widget.setColumnWidth(0, 30)
        self.table_widget.setColumnWidth(1, 400)
        self.table_widget.setColumnWidth(3, 200)
        self.table_widget.setColumnWidth(4, 100)
        self.table_widget.setHorizontalHeaderLabels(["ID", "URL", "Method", "Timestamp", "Host", "Add To Batch"])
        vbox.addWidget(self.table_widget)

        self.load_requests(vbox)

        requests_tab.setLayout(vbox)

        return None

    def create_batch_widget(self, vbox, batches_tab) -> None:
        vbox.addWidget(QLabel("Batches Information"))

        directory = "state/batches"
        file_names = load_json_batches(directory)

        # --- Creating table --- #
        self.table_widget = QTableWidget(len(file_names), 6)
        self.table_widget.setColumnWidth(0, 400)
        self.table_widget.setHorizontalHeaderLabels(["Name", "Allow Redirects", "Sync Last Byte", "Send Timeout", "Set Current Batch", "Open Batch"])
        vbox.addWidget(self.table_widget)

        # --- Clearing content before creating new --- #
        self.table_widget.clearContents()
        self.table_widget.setRowCount(0)

        # --- Add new batch --- #
        add_batch_field = QLineEdit()
        add_batch_field_button = QPushButton("Add Batch", self)
        add_batch_field_button.clicked.connect(lambda _, input_field=add_batch_field: self.create_new_batch(input_field))

        # --- Create add batch button and field --- #
        hbox = QHBoxLayout()
        hbox.addWidget(add_batch_field)
        hbox.addWidget(add_batch_field_button)
        vbox.addLayout(hbox)

        # --- Add other important buttons --- #
        quit_button = QPushButton("Quit", self)
        quit_button.clicked.connect(QApplication.quit)
        vbox.addWidget(quit_button)

        # --- Load in all batches --- #
        current_batch = self.data_requests["current_batch"]
        self.load_batches(file_names, directory, vbox, current_batch)

        # --- JSON Parsing Timer --- #
        self.update_json_timer = QTimer()
        self.update_json_timer.timeout.connect(self.reload_json)
        self.update_json_timer.start(5000)

        batches_tab.setLayout(vbox)

        return None

    def create_logs_widget(self, vbox, logs_tab) -> None:
        vbox.addWidget(QLabel("Logs"))

        # --- Create table --- #
        self.table_widget = QTableWidget(len(self.data_requests["cp_history"]), 1)
        self.table_widget.setColumnWidth(0, 400)
        self.table_widget.setHorizontalHeaderLabels(["Commands"])
        vbox.addWidget(self.table_widget)

        vbox.addWidget(QPushButton("Save", self, clicked=self.save_data))

        self.load_logs()

        logs_tab.setLayout(vbox)

        return None

    def load_requests(self, vbox) -> None:
        for idx, request in enumerate(self.data_requests["requests"]):
            # --- Insert row number {forloopnumber} --- #
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)

            # --- Create Button --- #
            add_request_button = QPushButton("Add", self)
            add_request_button.clicked.connect(lambda _, request_id=str(request): self.add_request_to_batch(request_id))

            # --- Insert data into row --- #
            self.table_widget.setItem(row, 0, QTableWidgetItem(str(request)))
            self.table_widget.setItem(row, 1, QTableWidgetItem(str(self.data_requests["requests"][request]["url"])))
            self.table_widget.setItem(row, 2, QTableWidgetItem(str(self.data_requests["requests"][request]["method"])))
            self.table_widget.setItem(row, 3, QTableWidgetItem(str(self.data_requests["requests"][request]["timestamp"])))
            headers = self.data_requests["requests"][request].get("headers", {})
            host = headers.get("Host", "")
            self.table_widget.setItem(row, 4, QTableWidgetItem(str(host)))
            self.table_widget.setCellWidget(row, 5, add_request_button)

        self.remove_empty_rows()

        return None

    def load_batches(self, file_names, directory, vbox, current_batch) -> callable([]):
        self.batch_buttons.clear()

        def load_table():
            for idx, name in enumerate(file_names):
                # --- Create commandbuttons --- #
                current_button = QPushButton("Set Current", self)
                window_button = QPushButton("Open", self)

                current_button.clicked.connect(lambda _, batch_name=name: self.set_current_batch(batch_name))
                window_button.clicked.connect(lambda _, batch_name=name: self.new_batch_window(batch_name))

                self.batch_buttons.append((current_button, window_button))

                # --- Insert row number {forloopnumber} --- #
                row = self.table_widget.rowCount()
                self.table_widget.insertRow(row)
                self.table_widget.setItem(row, 0, QTableWidgetItem(str(name)))
                self.table_widget.setCellWidget(row, 4, current_button)
                self.table_widget.setCellWidget(row, 5, window_button)

                self.check_current_batch(name, row, current_button, window_button, current_batch)

                data = self.get_json_data(directory, name)

                for col, col_name in enumerate(["Allow Redirects", "Sync Last Byte", "Send Timeout"]):
                    value = data.get(col_name.lower().replace(" ", "_"))
                    self.table_widget.setItem(row, col + 1, QTableWidgetItem(str(value)))

                    if name == current_batch:
                        item = self.table_widget.item(row, col + 1)
                        if item is not None:
                            item.setBackground(Qt.gray)

            self.remove_empty_rows()

        load_table()

        return load_table

    def load_logs(self) -> None:
        for command in enumerate(self.data_requests["cp_history"]):
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(str(command)))

        self.remove_empty_rows()
        return None

    def add_request_to_batch(self, request_id) -> None:
        self.showNotification("RequestID " + request_id + " has been added to active Batch!")
        self.racer.comm_curr_add(self.state, request_id)

        return None

    def get_json_data(self, directory, name) -> dict:
        with open(os.path.join(directory, name + ".json"), "r") as file:
            data = json.load(file)

        return data

    def check_current_batch(self, name, row, current_button, window_button, current_batch) -> None:
        if name == current_batch:
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                if item is not None:
                    item.setBackground(Qt.gray)
            current_button.setEnabled(False)
            window_button.setEnabled(True)
        else:
            window_button.setEnabled(False)

        if name == "Imm":
            current_button.setEnabled(False)
            window_button.setEnabled(False)

        return None

    def remove_empty_rows(self) -> None:
        for row in range(self.table_widget.rowCount() - 1, -1, -1):
            empty = True
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                if item is not None and not item.text().strip() == "":
                    empty = False
                    break
            if empty:
                self.table_widget.removeRow(row)

        return None

    def load_json_requests(self) -> None:
        with open('state/state.json', 'r') as f:
            self.data_requests = json.load(f)

        return None

    def save_data(self) -> None:
        self.racer.comm_general_save(True)

        return None

    def reload_json(self) -> None:
        if self.isActiveWindow():
            self.save_data()
            self.update_json_timer.stop()
            self.hide()
            self.general_window = MainGUI(self.racer, self.state, self.command_processor)
            self.general_window.show()
            self.deleteLater()

        return None

    def set_current_batch(self, batch_name) -> None:
        self.racer.set_curr_batch_by_name(batch_name)
        self.current_batch = batch_name
        self.showNotification("Set current batch to " + batch_name)

        return None

    def new_batch_window(self, batch_name) -> None:
        self.save_data()
        self.update_json_timer.stop()
        self.batch_window = BatchWindow(batch_name, self.racer, self.state, self.command_processor)
        self.batch_window.show()
        self.hide()

        return None

    def create_new_batch(self, batch_name) -> None:
        batch_name = batch_name.text()
        self.racer.gui_create_new_batch(batch_name)
        self.showNotification("Added New Batch " + batch_name + ". Add a request to your batch so you can open your batch")

        return None

    def showNotification(self, notiText) -> None:
        messageBox = QMessageBox()
        messageBox.setIcon(QMessageBox.Information)
        messageBox.setText(notiText)

        messageBox.setGeometry(0, 0, 500, 50)

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(messageBox.close)
        timer.start(5000)

        messageBox.exec()

        return None


def load_json(filepath) -> dict:
    with open(filepath, 'r') as file:
        data = json.load(file)

    return data


class BatchWindow(QMainWindow):
    def __init__(self, batch_name, racer, state, command_processor) -> None:
        super().__init__()

        self.showFullScreen()
        self.setWindowTitle("Batch: " + batch_name)

        self.update_json_timer = None
        self.general_window = None
        self.table_widget = None

        self.racer = racer
        self.batch_name = batch_name
        self.state = state
        self.command_processor = command_processor

        self.batch_requests = []

        self.init_ui()

    def init_ui(self) -> None:
        vbox = QVBoxLayout()
        batch_tab = QWidget()

        batch_tab.setLayout(vbox)
        batch_tab.layout().addWidget(self.table_widget)

        tabs = QTabWidget()
        tabs.addTab(batch_tab, "Batch")

        vbox.addStretch()

        self.add_button_widget(vbox)
        self.setCentralWidget(tabs)
        self.create_requests_widget(vbox)

        vbox.insertWidget(0, self.table_widget)

        self.update_json_timer = QTimer()
        self.update_json_timer.timeout.connect(lambda: self.reload_json())
        self.update_json_timer.start(10000)

        return None

    def create_requests_widget(self, vbox) -> None:
        vbox.addWidget(QLabel(""))

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["ID", "URL", "Method", "Host"])
        self.table_widget.setColumnWidth(0, 50)
        self.table_widget.setColumnWidth(1, 50)
        self.table_widget.setColumnWidth(2, 300)
        self.table_widget.setColumnWidth(3, 100)

        self.add_request_table()

        return None

    def add_button_widget(self, vbox) -> None:
        send_batch_button = QPushButton("Send Batch")
        go_back_button = QPushButton("Go Back")
        quit_button = QPushButton("Quit")

        send_batch_button.clicked.connect(self.send_batch)
        go_back_button.clicked.connect(self.go_back)
        quit_button.clicked.connect(QApplication.quit)

        vbox.addWidget(send_batch_button, alignment=Qt.AlignBottom)
        vbox.addWidget(go_back_button, alignment=Qt.AlignBottom)
        vbox.addWidget(quit_button, alignment=Qt.AlignBottom)

        return None

    def add_request_table(self) -> None:
        items = load_json("state/batches/" + self.batch_name + ".json")["items"]
        requests = load_json("state/state.json")["requests"]

        # --- Load in all data --- #
        for i, item in enumerate(items):
            request_id = item["key"][0]
            request = requests[request_id]

            method = request["method"]
            url = request["url"]
            host = request["headers"]["Host"]

            self.table_widget.setItem(i, 0, QTableWidgetItem(request_id))
            self.table_widget.setItem(i, 1, QTableWidgetItem(method))
            self.table_widget.setItem(i, 2, QTableWidgetItem(url))
            self.table_widget.setItem(i, 3, QTableWidgetItem(host))

        return None

    def send_batch(self) -> None:
        self.save_data()
        self.update_json_timer.stop()
        self.racer.gui_send_batches()

        return None

    def go_back(self) -> None:
        self.general_window = MainGUI(self.racer, self.state, self.command_processor)
        self.general_window.show()
        self.hide()

        return None

    def save_data(self) -> None:
        self.racer.comm_general_save(True)

        return None

    def reload_json(self) -> None:
        if self.isActiveWindow():
            self.save_data()
            self.update_json_timer.stop()
            self.hide()
            self.general_window = BatchWindow(self.batch_name, self.racer, self.state, self.command_processor)
            self.general_window.show()
            self.deleteLater()

        return None

    @staticmethod
    def showNotification(notifyText) -> None:
        messageBox = QMessageBox()
        messageBox.setIcon(QMessageBox.Information)
        messageBox.setText(notifyText)

        messageBox.setGeometry(0, 0, 500, 50)

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(messageBox.close)
        timer.start(5000)

        messageBox.exec()

        return None
