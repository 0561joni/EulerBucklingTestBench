import xlsxwriter
from serial import Serial, SerialException
import serial.tools.list_ports as list_ports
import time
import logging
import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

BAUDRATE = 115200
DEVICENAME = b"EulerBucklingTestBench"
SUPPORTED_PROTOCOLS = [1]
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# All the stuff inside the window.
layout = [[sg.Text('Euler Buckling Test Bench v0.1', justification='center', size=(50, 1), relief=sg.RELIEF_SUNKEN)],
          [sg.Canvas(key="-CANVAS-")],
          [sg.Button('Connect', key='CONNECT'), sg.Text(
              'NOT CONNECTED', size=(30, 1), key='CONNECT_STATUS')],
          [sg.Button('Start', key='START'), sg.Button('Stop', key='STOP'), sg.Button('Return', key='RETURN'), sg.Button('Save', key='SAVE'), sg.Button('Clear', key='CLEAR'), sg.Button('Tare', key='TARE'), sg.Button('SwitchDir', key='SWITCHDIR')]]
window = sg.Window('EulerBucklingTestBench', layout,
                   finalize=True, font="Helvetica 12", icon="icon.ico")


def readline(connection):
    '''wraper Function to automatically remove linebreaks '''
    return connection.readline().replace(b'\n', b'').replace(b'\r', b'')


def draw_figure(canvas, figure, loc=(0, 0)):
    '''draw the figuere onto the canvas'''
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg


def connect_serial(window):
    '''searches automatically for a connected device. returns the connection (object or None) and a status string'''
    logging.info(f"searching for device with baudrate {BAUDRATE} ...")
    ports = list(list_ports.comports())
    for port in ports:
        window.refresh()
        try:
            connection = Serial(port.device, BAUDRATE, timeout=1)
        except SerialException:
            continue
        time.sleep(1)
        handshake = readline(connection)
        if handshake == DEVICENAME:
            logging.info(f"connected at {port}")
            protocol = int(connection.readline().replace(b'\n', b'').replace(
                b'\r', b'').replace(b"protocol version: ", b''))
            if protocol not in SUPPORTED_PROTOCOLS:
                logging.warning(f"unsupported protocol ({protocol})")
                return (None, f"UNSUPPORTED PROTOCOL ({protocol}) on {str(connection)}")
            else:
                line = 0
                while True:
                    window.refresh()
                    l = readline(connection)
                    logging.info(l)
                    if l == b"ready":
                        return (connection, f"{port}")
                    else:
                        line += 1
                        if line > 10:
                            return(None, "DEVICE NOT READY")

    logging.error("could not find device.")
    return (None, "NO DEVICE FOUND")


def setup_result_file(name):
    '''create and setup the report file '''
    # Create an new Excel file and add a worksheet.
    workbook = xlsxwriter.Workbook(f"result_{name}.xlsx")
    worksheet = workbook.add_worksheet()
    # Add a bold format to use to highlight cells.
    bold = workbook.add_format({'bold': True})
    # Add a number format for cells.
    # workbook.add_format({'num_format': '#.##0,00'})
    # Setup columns.
    worksheet.write('A1', 'Distance', bold)
    worksheet.write('B1', 'Load', bold)
    return workbook, worksheet


def read_data(connection):
    '''read data from the connected device. returns parsed distance and force'''
    line = readline(connection)
    print(line)
    token = line.split(b" ")
    if len(token) == 3:
        try:
            dist = float((token[1].split(b":")[1]))
            force = float((token[2].split(b":")[1]))
            return(dist, force)
        except Exception:
            logging.warning("could not parse serial communication")
    return None


def update_plot(ax, fig_agg, forces, distances):
    '''update the figure'''
    ax.cla()
    ax.grid()
    # ax.set_xlim(0,350)
    # ax.set_ylim(0,2000)
    ax.plot(forces, distances)
    fig_agg.draw()


def gui_main_loop():
    '''handles program logic and gui updates'''

    #state variables
    distances = []
    forces = []
    connection = None
    running = False
    has_moved = False

    #figure variables and setup
    canvas = window['-CANVAS-'].TKCanvas
    fig = Figure(figsize=(4.5, 3))
    ax = fig.add_subplot()
    fig_agg = draw_figure(canvas, fig)
    fig.tight_layout()

    #main loop
    while True:
        update_plot(ax, fig_agg, distances, forces)

        window.Element('CONNECT').Update(
            disabled=True if connection != None else False)
        window.Element('START').Update(
            disabled=True if connection == None or running else False)
        window.Element('STOP').Update(
            disabled=True if connection == None or not running else False)
        window.Element('RETURN').Update(
            disabled=True if connection == None or running or not has_moved else False)
        window.Element('SAVE').Update(disabled=True if connection ==
                                      None or running or len(forces) == 0 else False)
        window.Element('CLEAR').Update(disabled=True if connection ==
                                       None or running or len(forces) == 0 else False)
        window.Element('SWITCHDIR').Update(
            disabled=True if connection == None or running else False)
        window.Element('TARE').Update(
            disabled=True if connection == None or running else False)

        event, values = window.read(timeout=20)
        #print(event, values)
        if event == sg.WIN_CLOSED or event == 'Exit':
            window.close()
            connection.write(b"stop\n")
            exit()
        elif event == "CONNECT":
            window.Element('CONNECT_STATUS').Update("CONNECTING...")
            window.Refresh()
            connection, status = connect_serial(window)
            window.Element('CONNECT_STATUS').Update(status)
        elif event == "START":
            running = True
            has_moved = True
            connection.write(b"go\n")
        elif event == "STOP":
            running = False
            connection.write(b"stop\n")
        elif event == "RETURN":
            connection.write(b"reverse\n")
            has_moved = False
        elif event == "SWITCHDIR":
            connection.write(b"switchDir\n")
        elif event == "CLEAR":
            forces.clear()
            distances.clear()
        elif event == "TARE":
            connection.write(b"tare\n")
        elif event == "SAVE":
            fname = sg.popup_get_text('', 'Please input a filename')
            file, worksheet = setup_result_file(fname)
            if len(forces) != len(distances):
                sg.popup(
                    'saving failed due to an internal error (list lengths are not equal)')
            else:
                for i, (force, distance) in enumerate(zip(forces, distances)):
                    worksheet.write_number(i+1, 0, distance)
                    worksheet.write_number(i+1, 1, force)
            file.close()
        if running:
            data = read_data(connection)
            if data != None:
                dist, force = data
                distances.append(dist)
                forces.append(force)


if __name__ == "__main__":
    gui_main_loop()
