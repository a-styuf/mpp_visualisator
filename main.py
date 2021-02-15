import tkinter as tk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import mpp
import time
import warnings
# warnings.filterwarnings("ignore", category=UserWarning)

mpp_serial = None
legend = None
cycle_after_id = 0
spectr_acum = [0 for i in range(256)]


def state_check():
    if mpp.state == 1:
        connect_button["bg"] = "SeaGreen2"
    elif mpp.state == 0:
        connect_button["bg"] = "ivory3"
    elif mpp.state == -1:
        connect_button["bg"] = "coral2"
    pass


def single():
    global spectr_acum
    spectr_acum = [0 for i in range(256)]
    single_read()


def single_read():
    global legend
    mpp.id = int(mpp_adr_var.get())
    if mpp.id == 7:
        mpp.a, mpp.b = 1, 0
    elif mpp.id == 5:
        mpp.a, mpp.b = 1, 0
    elif mpp.id == 6:
        mpp.a, mpp.b = 1, 0
    else:
        mpp.a, mpp.b = 1, 0
    # установка уставки МПП
    mpp.offset = float(mpp_offset_var.get())
    mpp.pulse_read()
    pulse_draw()
    pass


def pulse_draw():
    global legend
    # отрисовка осциллограммы
    try:
        legend.remove()
    except (AttributeError, ValueError):
        pass

    ax0.cla()
    try:
        y0 = (mpp.pulse_power / (2 * mpp.pulse_width + 1.4)) + mpp.pulse_mean
    except:
        y0 = 0
    x = [0, 0, mpp.pulse_width, mpp.pulse_width]
    y = [mpp.pulse_mean, y0, y0, mpp.pulse_mean]
    ax0.fill(x, y, 'r', alpha=0.3)

    ax0.axhline(y=mpp.pulse_mean, color="black", linewidth=1)  # рисуем среднее значение

    ax0.axhline(y=mpp.pulse_mean + mpp.offset, color="red", linewidth=1)  # рисуем верхнюю отсечку
    ax0.axhline(y=mpp.pulse_mean - mpp.offset, color="red", linewidth=1)  # рисуем нижнюю отсечку

    ax0.axhline(y=mpp.pulse_mean + mpp.pulse_peak, color="green", linewidth=1)  # рисуем верхний максимум
    ax0.axhline(y=mpp.pulse_mean - mpp.pulse_peak, color="green", linewidth=1)  # рисуем нижний максимум

    ax0.axhline(y=mpp.pulse_mean + mpp.pulse_noise, color="blue", linewidth=1)  # рисуем верхний максимум
    ax0.axhline(y=mpp.pulse_mean - mpp.pulse_noise, color="blue", linewidth=1)  # рисуем нижний максимум

    ax0.axvline(x=0, color="orange", linewidth=2)  # начало импульса
    ax0.axvline(x=mpp.pulse_width, color="orange", linewidth=2)  # конец импульса

    custom_lines = [Line2D([0], [0], color="black", lw=2, label="mean"),
                    Line2D([0], [0], color="red", lw=2, label="offset"),
                    Line2D([0], [0], color="green", lw=2, label="peak"),
                    Line2D([0], [0], color="blue", lw=2, label="noise"),
                    Line2D([0], [0], color="orange", lw=2, label="width"),
                    Line2D([0], [0], color="red", alpha=0.3, lw=6, label="power"),
                    ]
    legend = f_1.legend(handles=custom_lines, loc=1, markerscale=0.5, fontsize="x-small",
                        bbox_to_anchor=(0.96, 0.99))

    text_str = "zero_count = %d" % mpp.pulse_zero_count
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax0.text(0.95, 0.95, text_str, transform=ax0.transAxes, fontsize=14, verticalalignment='top',
             horizontalalignment="right", bbox=props)

    ax0.plot(mpp.osc_time, mpp.osc_data)
    ax0.set_xlabel("time, us")
    ax0.set_ylabel("voltage, V")
    ax0.grid()
    f_1_canvas.draw()
    f_1.savefig("image/offset_%.2f-mpp_id_%d-%s.png" % (mpp.offset, mpp.id, get_time()), format="png")
    # отрисовка спектра
    ax1.cla()
    ax1.plot(mpp.osc_freq, mpp.osc_spectra)
    ax1.set_xlabel("freq, MHz")
    ax1.set_ylabel("voltage, V")
    ax1.grid()
    ax1.set_yscale("linear")
    ax1.set_xscale("log")
    f_2_canvas.draw()
    pass


def cycle_read():
    global cycle_after_id, spectr_acum
    if cycle_after_id == 0:
        cycle_after_id = root.after(1000, cycle_body)
    else:
        root.after_cancel(cycle_after_id)
        cycle_after_id = 0
        # отрисовка спектра
        ax1.cla()
        freq = [(1 / (512 * 0.025)) * i for i in range(256)]
        ax1.plot(freq, spectr_acum)
        ax1.set_xlabel("freq, MHz")
        ax1.set_ylabel("voltage, V")
        ax1.grid()
        ax1.set_yscale("linear")
        ax1.set_xscale("linear")
        f_2_canvas.draw()
        spectr_acum = [0 for i in range(256)]
    pass


def cycle_body():
    global cycle_after_id, spectr_acum
    single_read()
    cycle_after_id = root.after(1000, cycle_body)
    pass


def initialisation():
    mpp.initialisation()
    print(mpp.report)
    pass


def bytes_array_to_str(bytes_array):
    bytes_string = "0x"
    for i, ch in enumerate(bytes_array):
        byte_str = (" %02X" % bytes_array[i])
        bytes_string += byte_str
    return bytes_string


def reconnect():
    mpp.reconnect()
    state_check()


def get_time():
    return time.strftime("%Y_%m_%d__%H-%M-%S", time.localtime())


# саздание основного окна для tkinter
root = tk.Tk()
root.title("МПП БКАП ОСЦИЛЛОГРАММЫ")
root.geometry('1000x1200')
root.resizable(False, False)
root.config(bg="gray90")

# mpp объект
mpp = mpp.Device()

# поля для ввода
mpp_adr_label = tk.Label(root, text="MPP address")
mpp_adr_label.place(relx=1, x=-200, y=25, width=75, height=20)
mpp_adr_var = tk.StringVar()
mpp_adr_var.set("7")
mpp_adr_entry = tk.Entry(root, width=9, bd=2, textvariable=mpp_adr_var, justify="center")
mpp_adr_entry.place(relx=1, x=-120, y=25, width=75, height=20)

mpp_offset_label = tk.Label(root, text="Offset")
mpp_offset_label.place(relx=1, x=-200, y=50, width=75, height=20)
mpp_offset_var = tk.StringVar()
mpp_offset_var.set("100")
mpp_offset_entry = tk.Entry(root, width=9, bd=2, textvariable=mpp_offset_var, justify="center")
mpp_offset_entry.place(relx=1, x=-120, y=50, width=75, height=20)

single_read_button = tk.Button(root, text='Одиночно', command=single_read)
single_read_button.place(relx=1, x=-200, y=75, width=75, height=20)

cycle_read_button = tk.Button(root, text='Цикл', command=cycle_read)
cycle_read_button.place(relx=1, x=-200, y=100, width=75, height=20)


pulse_button = tk.Button(root, text='Инициализация МПП', command=initialisation)
pulse_button.place(relx=1, x=-200, y=150, width=150, height=20)

connect_button = tk.Button(root, text='Подключение', command=reconnect)
connect_button.place(relx=1, x=-200, y=200, width=150, height=20)

# graph
graph_block_x = 25
graph_block_y = 25

frame = tk.Frame(root, bg="gray10")
frame.place(x=graph_block_x, y=graph_block_y, width=750, height=550)
f_1 = Figure(figsize=(7.5, 5.5), dpi=100, facecolor="#A9A9A9", frameon=True)
ax0 = f_1.add_axes((0.1, 0.1, 0.75, 0.8), facecolor="#D3D3D3", frameon=True, yscale="linear")
label_font = {'family': 'Arial',
              'color':  'Black',
              'weight': 'normal',
              'size': 12}
ax0.set_yscale("linear")
ax0.set_xlabel("Time, us", fontdict=label_font)
#  ax0.plot(np.max(np.random.rand(100,10)*10, axis = 1),"r-")
f_1_canvas = FigureCanvasTkAgg(f_1, master=frame)
f_1_canvas.get_tk_widget().place(x=0, y=0)
f_1_canvas.draw()

toolbar = NavigationToolbar2Tk(f_1_canvas, root)
toolbar.place(x=25, y=570)
toolbar.update()

# graph
graph_block_x = 25
graph_block_y = 600

frame = tk.Frame(root, bg="gray10")
frame.place(x=graph_block_x, y=graph_block_y, width=750, height=550)
f_2 = Figure(figsize=(7.5, 5.5), dpi=100, facecolor="#A9A9A9", frameon=True)
ax1 = f_2.add_axes((0.1, 0.1, 0.75, 0.8), facecolor="#D3D3D3", frameon=True, yscale="linear")
label_font = {'family': 'Arial',
              'color':  'Black',
              'weight': 'normal',
              'size': 12}
ax1.set_yscale("linear")
ax1.set_xlabel("Freq, MHz", fontdict=label_font)
#  ax0.plot(np.max(np.random.rand(100,10)*10, axis = 1),"r-")
f_2_canvas = FigureCanvasTkAgg(f_2, master=frame)
f_2_canvas.get_tk_widget().place(x=0, y=0)
f_2_canvas.draw()

toolbar = NavigationToolbar2Tk(f_2_canvas, root)
toolbar.place(x=25, y=570)
toolbar.update()

# Main #
root.mainloop()
